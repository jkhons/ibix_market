# PDV Ibix - Factory de provedor para marketplace
"""Retorna config ativa + instância do provedor por cliente (e opcionalmente loja)."""
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import PaymentProviderConfig

from .base import PaymentProviderBase
from .credentials import decrypt_text
from .providers_marketplace import get_marketplace_provider
from .stubs import AsaasMarketplaceProvider, StripeMarketplaceProvider

PROVIDER_MP = "mercadopago"
ALLOWED_MARKETPLACE_PROVIDERS = {PROVIDER_MP, "pagbank", "pagarme", "asaas", "stripe"}


def get_provider_for_cliente(
    db: Session,
    cliente_id: int,
) -> Tuple[Optional[PaymentProviderConfig], Optional[PaymentProviderBase]]:
    """
    Retorna a config ativa do provedor de pagamento do cliente (marketplace).
    Um ativo por cliente; prioridade is_default.
    """
    config = (
        db.query(PaymentProviderConfig)
        .filter(
            PaymentProviderConfig.cliente_id == cliente_id,
            PaymentProviderConfig.is_active.is_(True),
            PaymentProviderConfig.provider_code.in_(ALLOWED_MARKETPLACE_PROVIDERS),
        )
        .order_by(PaymentProviderConfig.is_default.desc(), PaymentProviderConfig.id.asc())
        .first()
    )
    if not config:
        return None, None
    provider = _provider_from_config(config)
    return config, provider


def get_provider_for_store(
    db: Session,
    cliente_id: int,
    loja_id: Optional[int] = None,
) -> Tuple[Optional[PaymentProviderConfig], Optional[PaymentProviderBase]]:
    """
    Retorna config + provedor para a loja. Por enquanto apenas por cliente_id
    (loja_id pode ser usado no futuro para multi-gateway por loja).
    """
    return get_provider_for_cliente(db, cliente_id)


def _provider_from_config(config: PaymentProviderConfig) -> PaymentProviderBase:
    """Monta instância do provedor com credenciais e webhook_secret da config."""
    code = (config.provider_code or "").lower()
    webhook_secret = None
    if config.webhook_secret_encrypted:
        webhook_secret = decrypt_text(config.webhook_secret_encrypted)
    if code == PROVIDER_MP:
        return get_marketplace_provider(code, webhook_secret=webhook_secret)
    if code == "pagbank":
        from .providers_marketplace import PagBankMarketplaceProvider
        return PagBankMarketplaceProvider(webhook_secret=webhook_secret)
    if code == "pagarme":
        from .providers_marketplace import PagarMeMarketplaceProvider
        return PagarMeMarketplaceProvider(webhook_secret=webhook_secret)
    if code == "asaas":
        return AsaasMarketplaceProvider()
    if code == "stripe":
        return StripeMarketplaceProvider()
    return get_marketplace_provider(code, webhook_secret=webhook_secret)
