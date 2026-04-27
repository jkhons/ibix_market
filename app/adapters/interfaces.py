# PDV Ibix - Interfaces de adapters (ICertificadoExporter, INotifierEmail, IERPIntegration)
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ICertificadoExporter(ABC):
    """Interface para exportar certificado em JSON/XML. Troca de endpoint sem refatorar o core."""

    @abstractmethod
    def export(self, certificado_id: int, formato: str = "json") -> Any:
        """Exporta certificado. formato: 'json' | 'xml'. Retorna bytes ou dict."""
        ...


class INotifierEmail(ABC):
    """Interface para envio de e-mail (SMTP/API futura). Troca de endpoint sem refatorar o core."""

    @abstractmethod
    def enviar(
        self,
        destinatario: str,
        assunto: str,
        corpo: str,
        *,
        anexos: Optional[List[tuple]] = None,
    ) -> bool:
        """Envia e-mail. anexos: [(filename, bytes), ...]. Retorna True se enviou."""
        ...


class IERPIntegration(ABC):
    """Interface para integração ERP/faturamento (stub com fila). Troca de endpoint sem refatorar o core."""

    @abstractmethod
    def enfileirar(self, certificado_id: int, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Enfileira certificado para envio ao ERP. Retorna True se enfileirou."""
        ...
