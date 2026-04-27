# PDV Ibix - Stub Pagar.me (marketplace)
"""Provedor Pagar.me para marketplace: stub em V1 (não implementado)."""
from ..providers_marketplace import StubMarketplaceProvider


class PagarmeMarketplaceProvider(StubMarketplaceProvider):
    """Stub Pagar.me: checkout/refund não implementados em V1."""

    def __init__(self) -> None:
        super().__init__(code="pagarme")
