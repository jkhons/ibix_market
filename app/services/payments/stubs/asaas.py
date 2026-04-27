# PDV Ibix - Stub Asaas (marketplace)
"""Provedor Asaas para marketplace: stub em V1 (não implementado)."""
from ..providers_marketplace import StubMarketplaceProvider


class AsaasMarketplaceProvider(StubMarketplaceProvider):
    """Stub Asaas: checkout/refund não implementados em V1."""

    def __init__(self) -> None:
        super().__init__(code="asaas")
