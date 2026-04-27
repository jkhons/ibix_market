# Interface do provider NFS-e (MODULO_FATURAMENT_V2.MD — issue, poll, cancel)
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class IssueResult:
    success: bool
    status: str  # AUTHORIZED | REJECTED | SENT (aguardando poll)
    numero_nfse: Optional[str] = None
    codigo_verificacao: Optional[str] = None
    url_consulta: Optional[str] = None
    data_emissao: Optional[datetime] = None
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    payload_out_redacted: Optional[str] = None
    response_in_redacted: Optional[str] = None
    http_status: Optional[int] = None


@dataclass
class PollResult:
    success: bool
    status: str  # AUTHORIZED | REJECTED | SENT | PENDING
    numero_nfse: Optional[str] = None
    codigo_verificacao: Optional[str] = None
    url_consulta: Optional[str] = None
    data_emissao: Optional[datetime] = None
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    response_redacted: Optional[str] = None
    http_status: Optional[int] = None


@dataclass
class CancelResult:
    success: bool
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    payload_out_redacted: Optional[str] = None
    response_in_redacted: Optional[str] = None
    http_status: Optional[int] = None


class NfseProviderBase(ABC):
    """Adapter único: issue, poll, cancel. Implementações: NACIONAL, SP_CAPITAL (futuro)."""

    @abstractmethod
    def issue(
        self,
        invoice: Any,
        empresa: Any,
        credential: Any,
        rps_numero: int,
        rps_serie: str = "1",
    ) -> IssueResult:
        """Envia RPS ao provedor. credential pode ser None (usa empresa.certificado_*)."""
        pass

    @abstractmethod
    def poll(self, invoice: Any, empresa: Any, credential: Any) -> PollResult:
        """Consulta status até AUTHORIZED ou REJECTED."""
        pass

    @abstractmethod
    def cancel(
        self,
        invoice: Any,
        empresa: Any,
        credential: Any,
        reason: str,
        codigo_cancelamento: Optional[str] = None,
    ) -> CancelResult:
        """Solicita cancelamento no provedor."""
        pass
