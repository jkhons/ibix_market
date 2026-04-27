# PDV Ibix - Stub Stripe (marketplace)
"""Provedor Stripe para marketplace: stub em V1 (não implementado)."""
from ..providers_marketplace import StubMarketplaceProvider


class StripeMarketplaceProvider(StubMarketplaceProvider):
    """Stub Stripe: checkout/refund não implementados em V1."""

    def __init__(self) -> None:
        super().__init__(code="stripe")
