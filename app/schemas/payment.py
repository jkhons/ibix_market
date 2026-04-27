# PDV Ibix - Schemas Módulo de Pagamentos (Fase 3.3)
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_serializer


class PaymentProviderConfigBase(BaseModel):
    cliente_id: int
    provider_code: str
    credentials_encrypted: Optional[str] = None
    fee_configs: Optional[Any] = None
    routing_rules: Optional[Any] = None
    is_active: bool = True
    is_default: bool = False
    test_mode: bool = False


class PaymentProviderConfigCreate(PaymentProviderConfigBase):
    """credentials (dict) em plain: será criptografado antes de salvar. credentials_encrypted: já cifrado (opcional)."""
    credentials: Optional[Any] = None  # plain JSON para criptografar no backend


class PaymentProviderConfigUpdate(BaseModel):
    """Atualização parcial (PATCH). Não altera cliente_id nem provider_code."""
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    test_mode: Optional[bool] = None
    credentials: Optional[Any] = None  # plain dict: Mercado Pago / Pagar.me; omitir para manter


class PaymentProviderConfigResponse(PaymentProviderConfigBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    connection_status: Optional[str] = None
    account_external_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("credentials_encrypted")
    def mask_credentials(self, v: Optional[str]) -> Optional[str]:
        return "***" if v else None


class PaymentProcessRequest(BaseModel):
    """Request para processar pagamento (orquestrador)."""
    estabelecimento_id: int  # cliente_id
    venda_id: Optional[int] = None
    caixa_id: Optional[int] = None
    amount: Decimal
    method: str  # credit, debit, pix, boleto, cash, transfer
    method_details: Optional[dict] = None  # installments; payer_email (obrigatório PIX Mercado Pago); payment_submethod
    idempotency_key: Optional[str] = None


class PaymentProcessResponse(BaseModel):
    """Resposta padronizada do processamento."""
    transaction_uuid: str
    status: str
    provider_transaction_id: Optional[str] = None
    payment_details: Optional[dict] = None  # pix_qr_code, boleto_url, nsu, authorization_code, etc.
    message: Optional[str] = None
    retry_allowed: Optional[bool] = None


class PaymentStatusResponse(BaseModel):
    """Status da transação."""
    model_config = ConfigDict(from_attributes=True)
    uuid: str
    status: str
    payment_method: str
    amount: Decimal
    venda_id: Optional[int] = None
    provider_transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    reconciliation_status: Optional[str] = None
    reconciliation_date: Optional[datetime] = None


class PaymentTransactionListItem(BaseModel):
    """Item de listagem operacional de transações."""
    model_config = ConfigDict(from_attributes=True)
    uuid: str
    status: str
    payment_method: str
    amount: Decimal
    venda_id: Optional[int] = None
    pedido_id: Optional[int] = None
    numero_pedido: Optional[str] = None
    paid_at: Optional[datetime] = None
    provider_code: Optional[str] = None
    provider_transaction_id: Optional[str] = None
    reconciliation_status: Optional[str] = None
    created_at: datetime
