# PDV Ibix - PaymentOrchestrator (Fase 3.3)
"""Orquestrador: carrega configs, seleciona provedor, chama charge, aplica split, persiste transação e splits."""
import json
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ...models import PaymentLog, PaymentProviderConfig, PaymentTransaction
from ...models.empresa import Empresa
from .credentials import decrypt_credentials
from .providers import ChargeRequest, ChargeResult, get_provider
from .split_engine import SplitEngine


class PaymentOrchestrator:
    """
    (1) Carrega configs ativas do estabelecimento
    (2) Filtra provedores que suportam o método
    (3) Seleciona provedor (is_default ou primeiro ativo)
    (4) Descriptografa credenciais
    (5) Chama provedor.charge()
    (6) Persiste transação e splits (SplitEngine)
    (7) Em falha, pode fallback para próximo provedor (simplificado: um provedor por chamada)
    """

    _ALLOWED_PROVIDERS = {"mercadopago", "pagbank", "pagarme"}

    def __init__(self, db: Session):
        self.db = db

    def _get_platform_credentials(self):
        """Retorna (provider_code, credentials_dict) usando a conta billing MP da plataforma."""
        from ...core.billing_config import get_mp_access_token
        access_token = get_mp_access_token(self.db)
        if not access_token:
            raise ValueError(
                "Conta de recebimento da plataforma não configurada. "
                "Configure o Mercado Pago em Admin Billing."
            )
        return "mercadopago", {"access_token": access_token}

    def _configs_for_establishment(self, cliente_id: int, method: str) -> List[PaymentProviderConfig]:
        """Configs ativas do estabelecimento cujo provedor suporta o método."""
        configs = (
            self.db.query(PaymentProviderConfig)
            .filter(
                PaymentProviderConfig.cliente_id == cliente_id,
                PaymentProviderConfig.is_active.is_(True),
            )
            .order_by(PaymentProviderConfig.is_default.desc(), PaymentProviderConfig.id.asc())
            .all()
        )
        out = []
        for c in configs:
            if (c.provider_code or "").lower() not in self._ALLOWED_PROVIDERS:
                continue
            provider = get_provider(c.provider_code)
            if provider.supports_method(method):
                out.append(c)
        return out

    def _find_idempotent_transaction(
        self,
        cliente_id: int,
        venda_id: Optional[int],
        amount: Decimal,
        method: str,
        idempotency_key: Optional[str],
    ) -> Optional[PaymentTransaction]:
        if not idempotency_key:
            return None
        query = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.cliente_id == cliente_id,
            PaymentTransaction.payment_method == method,
            PaymentTransaction.amount == amount,
        )
        if venda_id is not None:
            query = query.filter(PaymentTransaction.venda_id == venda_id)
        rows = query.order_by(PaymentTransaction.id.desc()).limit(30).all()
        for tx in rows:
            if not tx.provider_response:
                continue
            try:
                provider_meta = json.loads(tx.provider_response)
            except Exception:
                continue
            if provider_meta.get("idempotency_key") == idempotency_key:
                return tx
        return None

    def process(
        self,
        cliente_id: int,
        venda_id: Optional[int],
        caixa_id: Optional[int],
        amount: Decimal,
        method: str,
        payment_submethod: Optional[str] = None,
        installments: int = 1,
        idempotency_key: Optional[str] = None,
        method_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Processa pagamento: seleciona provedor, charge, persiste transação e splits.
        Retorna dict com transaction_uuid, status, provider_transaction_id, payment_details, message.
        """
        existing = self._find_idempotent_transaction(
            cliente_id=cliente_id,
            venda_id=venda_id,
            amount=amount,
            method=method,
            idempotency_key=idempotency_key,
        )
        if existing:
            details = {}
            if existing.provider_response:
                try:
                    details = json.loads(existing.provider_response).get("payment_details") or {}
                except Exception:
                    details = {}
            return {
                "transaction_uuid": existing.uuid,
                "status": existing.status,
                "provider_transaction_id": existing.provider_transaction_id,
                "payment_details": details,
                "message": "Transação reaproveitada por idempotência.",
                "retry_allowed": existing.status in {"failed", "pending"},
            }

        empresa = (
            self.db.query(Empresa)
            .filter(Empresa.cliente_id == cliente_id, Empresa.ativo.is_(True))
            .first()
        )
        modo = (empresa.modo_recebimento or "plataforma").lower() if empresa else "plataforma"

        if modo == "plataforma":
            provider_code, credentials = self._get_platform_credentials()
        else:
            configs = self._configs_for_establishment(cliente_id, method)
            if not configs:
                raise ValueError(
                    "Nenhuma configuração ativa de gateway encontrada para este estabelecimento. "
                    "Configure em Negócios → Recebíveis."
                )
            config = configs[0]
            provider_code = (config.provider_code or "").lower()
            if provider_code not in self._ALLOWED_PROVIDERS:
                raise ValueError(f"Gateway '{provider_code}' não permitido. Use Mercado Pago, PagBank ou Pagar.me.")
            credentials = decrypt_credentials(config.credentials_encrypted)

        provider = get_provider(provider_code)

        transaction_uuid = str(uuid.uuid4())
        md = method_details if isinstance(method_details, dict) else {}
        charge_meta: Dict[str, Any] = {}
        payer_email = (md.get("payer_email") or md.get("customer_email") or "").strip()
        if payer_email:
            charge_meta["payer_email"] = payer_email
        if provider_code == "mercadopago":
            from ...core.billing_config import get_app_url

            base = (get_app_url(self.db) or "").strip().rstrip("/")
            if base:
                charge_meta["notification_url"] = f"{base}/api/webhooks/mercadopago?source_news=webhooks"
        charge_request = ChargeRequest(
            amount=amount,
            payment_method=method,
            payment_submethod=payment_submethod,
            installments=installments,
            idempotency_key=idempotency_key,
            metadata=charge_meta if charge_meta else None,
        )

        t0 = time.perf_counter()
        result: ChargeResult = provider.charge(charge_request, credentials)
        duration_ms = int((time.perf_counter() - t0) * 1000)

        t = PaymentTransaction(
            uuid=transaction_uuid,
            cliente_id=cliente_id,
            venda_id=venda_id,
            caixa_id=caixa_id,
            provider_code=provider_code,
            provider_transaction_id=result.provider_transaction_id,
            payment_method=method,
            payment_submethod=payment_submethod,
            amount=amount,
            installments=installments,
            status=result.status,
            modo_recebimento=modo,
            repasse_status_id=1 if modo == "plataforma" else None,
            provider_response=json.dumps(
                {
                    "idempotency_key": idempotency_key,
                    "payment_details": result.payment_details,
                    **({"payer_email": payer_email} if payer_email else {}),
                }
            ),
            reconciliation_status="pending",
        )
        self.db.add(t)
        self.db.flush()  # para ter t.id

        # Log de auditoria
        log = PaymentLog(
            transaction_id=t.id,
            provider_code=provider_code,
            request_body=str(charge_request),
            response_body=str(result.payment_details) if result.payment_details else None,
            duration_ms=duration_ms,
        )
        self.db.add(log)

        # Split
        split_engine = SplitEngine(self.db)
        split_engine.compute_and_persist_splits(t, amount, fee_total=Decimal("0"))

        self.db.commit()
        self.db.refresh(t)

        return {
            "transaction_uuid": transaction_uuid,
            "status": result.status,
            "provider_transaction_id": result.provider_transaction_id,
            "payment_details": result.payment_details,
            "message": result.message,
            "retry_allowed": result.status in {"failed", "pending"},
        }
