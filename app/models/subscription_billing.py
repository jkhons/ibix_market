# PDV Ibix - Assinatura de cobrança (billing), distinta de assinatura de certificado
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class SubscriptionBilling(BaseModel):
    """Assinatura de pagamento por tenant (trial, ativa, inadimplente, bloqueada, cancelada)."""
    __tablename__ = "subscriptions"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plano_codigo = Column(String(50), nullable=False, default="pdv_solumatica_490")
    valor_mensal_centavos = Column(Integer, nullable=False, default=49000)  # R$ 490,00
    codigo_desconto_id = Column(Integer, ForeignKey("codigos_desconto.id", ondelete="SET NULL"), nullable=True, index=True, comment="Código usado no cadastro (vínculo Admin/divulgador e comissão)")

    qtd_pdvs_contratados = Column(Integer, nullable=False, default=1, comment="Qtd de PDVs contratados nesta subscription")

    status = Column(String(20), nullable=False, default="trial", index=True)
    grace_days = Column(Integer, nullable=False, default=15)

    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    next_charge_at = Column(Date, nullable=True)

    last_paid_at = Column(DateTime(timezone=True), nullable=True)
    blocked_at = Column(DateTime(timezone=True), nullable=True)

    mp_preference_id = Column(String(64), nullable=True)
    last_payer_user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("ix_subscriptions_tenant_status", "tenant_id", "status"),
        {"comment": "Assinatura de cobrança por tenant (billing)"},
    )

    tenant = relationship("Tenant", backref="subscription_billing")

    def __repr__(self):
        return f"<SubscriptionBilling(id={self.id}, tenant_id={self.tenant_id}, status='{self.status}')>"


# Comissão do Administrador por pagamento (idempotente: uma comissão por payment_id)
class ComissaoAdministrador(BaseModel):
    """Comissão do Administrador sobre mensalidade paga (CA vinculado via código promocional)."""
    __tablename__ = "comissoes_administrador"

    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    usuario_id_administrador = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    valor_mensalidade_centavos = Column(Integer, nullable=False)
    percentual_comissao = Column(Integer, nullable=False)
    valor_comissao_centavos = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pendente", index=True)  # pendente | pago
    pago_em = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_comissoes_administrador_usuario_status", "usuario_id_administrador", "status"),
        {"comment": "Comissão do Administrador por pagamento (uma por payment_id)"},
    )

    def __repr__(self):
        return f"<ComissaoAdministrador(id={self.id}, payment_id={self.payment_id}, status='{self.status}')>"
