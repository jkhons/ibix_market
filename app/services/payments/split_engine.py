# PDV Ibix - SplitEngine (Fase 3.3)
"""Calcula repasses a partir de split_rules e hierarquia (estabelecimento → cliente_admin → admin → super_admin)."""
from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

from ...models import SplitRule, TransactionSplit
from ...models.payment_transaction import PaymentTransaction


class SplitEngine:
    """Aplica regras de split por prioridade; restante líquido fica com o estabelecimento."""

    def __init__(self, db: Session):
        self.db = db

    def compute_and_persist_splits(
        self,
        transaction: PaymentTransaction,
        total_amount: Decimal,
        fee_total: Decimal = Decimal("0"),
    ) -> List[TransactionSplit]:
        """
        Carrega split_rules ativas do estabelecimento (cliente_id), aplica por prioridade,
        cria registros em transaction_splits. O valor restante após as regras vai para
        o estabelecimento (recipient_type=estabelecimento, recipient_id=cliente_id).
        """
        cliente_id = transaction.cliente_id
        rules = (
            self.db.query(SplitRule)
            .filter(
                SplitRule.cliente_id == cliente_id,
                SplitRule.is_active.is_(True),
            )
            .order_by(SplitRule.priority.asc(), SplitRule.id.asc())
            .all()
        )

        remaining = total_amount - fee_total
        splits_created: List[TransactionSplit] = []

        for rule in rules:
            if remaining <= 0:
                break
            original_amount = Decimal("0")
            if rule.rule_type == "fixed_percentage" and rule.percentage is not None:
                original_amount = (total_amount * rule.percentage / 100).quantize(Decimal("0.01"))
            elif rule.rule_type == "fixed_value" and rule.fixed_amount is not None:
                original_amount = min(rule.fixed_amount, remaining)
            # tiered pode ser implementado depois (faixas de valor)
            if original_amount <= 0:
                continue
            fee_amount = Decimal("0")  # taxa por split pode vir de fee_configs depois
            net_amount = original_amount - fee_amount
            if net_amount > remaining:
                net_amount = remaining
            remaining -= net_amount
            sp = TransactionSplit(
                transaction_id=transaction.id,
                recipient_type=rule.recipient_type,
                recipient_id=rule.recipient_id,
                original_amount=original_amount,
                fee_amount=fee_amount,
                net_amount=net_amount,
                status="pending",
            )
            self.db.add(sp)
            splits_created.append(sp)

        # Restante líquido fica com o estabelecimento
        if remaining > 0:
            sp = TransactionSplit(
                transaction_id=transaction.id,
                recipient_type="estabelecimento",
                recipient_id=cliente_id,
                original_amount=remaining,
                fee_amount=Decimal("0"),
                net_amount=remaining,
                status="pending",
            )
            self.db.add(sp)
            splits_created.append(sp)

        return splits_created
