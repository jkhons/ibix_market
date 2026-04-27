# Providers NFS-e (NACIONAL, SP_CAPITAL, etc.)
from .base import CancelResult, IssueResult, NfseProviderBase, PollResult
from .nacional import ProviderNacional


def get_provider(name: str) -> NfseProviderBase:
    if name == "NACIONAL":
        return ProviderNacional()
    raise ValueError(f"Provider NFS-e desconhecido: {name}")

__all__ = ["NfseProviderBase", "IssueResult", "PollResult", "CancelResult", "ProviderNacional", "get_provider"]
