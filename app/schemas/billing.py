# PDV Ibix - Schemas de billing (assinatura, pagamento, admin)
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MySubscriptionResponse(BaseModel):
    """Resposta GET /billing/my-subscription."""
    server_today: date
    status: str
    period_end: Optional[date] = None
    next_charge_at: Optional[date] = None
    grace_days: int = 15
    trial_days_left: Optional[int] = None
    grace_days_left: Optional[int] = None
    is_in_trial: bool = False
    is_past_due: bool = False
    is_blocked: bool = False
    valor_mensal_centavos: Optional[int] = None
    valor_exibicao: Optional[str] = None
    # Detalhe para exibir valor base, desconto e total
    valor_base_centavos: Optional[int] = None
    valor_base_exibicao: Optional[str] = None
    desconto_percent: Optional[int] = None
    valor_com_desconto_centavos: Optional[int] = None
    valor_com_desconto_exibicao: Optional[str] = None


class PayNowResponse(BaseModel):
    """Resposta POST /billing/pay-now."""

    init_point: str = ""
    preference_id: str = ""
    isento: bool = False
    message: Optional[str] = None


class PaymentListItem(BaseModel):
    """Item da lista GET /billing/my-payments."""
    id: int
    mp_payment_id: int
    status: str
    amount_centavos: int
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookAckResponse(BaseModel):
    """Resposta POST /api/webhooks/mercadopago."""
    status: str = "ok"


# Admin
class AdminTenantBillingListItem(BaseModel):
    """Item da lista GET /admin/billing/tenants."""
    tenant_id: int
    tenant_nome: str
    subscription_status: str
    period_end: Optional[date] = None
    next_charge_at: Optional[date] = None
    days_overdue: Optional[int] = None
    ativo: bool


class AdminBillingConfigResponse(BaseModel):
    """GET /admin/billing/config."""
    mp_configured: bool = False
    app_url: Optional[str] = None
    mp_access_token_masked: Optional[str] = None
    mp_webhook_secret_masked: Optional[str] = None
    mp_access_token: Optional[str] = None
    mp_webhook_secret: Optional[str] = None
    pagbank_configured: bool = False
    pagbank_client_id_masked: Optional[str] = None
    pagbank_client_id: Optional[str] = None
    pagbank_client_secret_masked: Optional[str] = None
    pagbank_sandbox: bool = True
    plataforma_pagbank_configured: bool = False
    plataforma_pagbank_access_token_masked: Optional[str] = None
    plataforma_pagbank_access_token: Optional[str] = None
    plataforma_pagarme_configured: bool = False
    plataforma_pagarme_secret_key_masked: Optional[str] = None
    plataforma_pagarme_secret_key: Optional[str] = None
    payment_lojas_gateway_self_service: bool = True


class AdminBillingConfigValidateResponse(BaseModel):
    """GET /admin/billing/config/validate — validação real do token com a API do MP."""
    mp_valid: bool = False
    mp_message: Optional[str] = None


class AdminBillingConfigRequest(BaseModel):
    """POST /admin/billing/config (opcional)."""
    mp_access_token: Optional[str] = None
    mp_webhook_secret: Optional[str] = None
    app_url: Optional[str] = None
    pagbank_client_id: Optional[str] = None
    pagbank_client_secret: Optional[str] = None
    pagbank_sandbox: Optional[bool] = None
    plataforma_pagbank_access_token: Optional[str] = None
    plataforma_pagarme_secret_key: Optional[str] = None
    payment_lojas_gateway_self_service: Optional[bool] = None


class PrecoVigenteBillingResponse(BaseModel):
    """GET /billing/preco-vigente — preço de referência (mesma origem que /admin/billing/preco)."""
    valor_base_centavos: int = Field(description="Valor mensal base em centavos (billing_config).")
    valor_pdv_adicional_centavos: int = Field(default=0, description="PDV adicional em centavos (0 quando origem é billing_config).")


class AdminBillingPrecoResponse(BaseModel):
    """GET /admin/billing/preco — valor mensal e descontos."""
    valor_mensal_centavos: int = 49000
    valor_aplicar_a: str = "novos"  # todos | novos
    desconto_percent: int = 0
    desconto_escopo: str = "todos"  # todos | ca | admin_cliente | especifico
    desconto_tenant_ids: List[int] = Field(default_factory=list)


class AdminBillingPrecoRequest(BaseModel):
    """POST /admin/billing/preco."""
    valor_mensal_centavos: Optional[int] = None
    valor_aplicar_a: Optional[str] = None  # todos | novos
    desconto_percent: Optional[int] = None
    desconto_escopo: Optional[str] = None  # todos | ca | admin_cliente | especifico
    desconto_tenant_ids: Optional[List[int]] = None
