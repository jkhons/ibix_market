# Stubs de provedores marketplace (C3): Asaas, Pagar.me, Stripe — não implementados em V1.
from .asaas import AsaasMarketplaceProvider
from .pagarme import PagarmeMarketplaceProvider
from .stripe import StripeMarketplaceProvider

__all__ = ["AsaasMarketplaceProvider", "PagarmeMarketplaceProvider", "StripeMarketplaceProvider"]
