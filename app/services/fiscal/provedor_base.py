# PDV Ibix - Interface do provedor fiscal (NFS-e / NF-e / NFC-e)
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ResultadoEnvioFiscal:
    """Resultado do envio de documento ao provedor"""
    sucesso: bool
    status: str  # autorizado, rejeitado, etc.
    protocolo: Optional[str] = None
    chave: Optional[str] = None
    mensagem: Optional[str] = None
    payload_retorno: Optional[Dict[str, Any]] = None
    xml_retorno: Optional[str] = None
    pdf_path: Optional[str] = None
    xml_path: Optional[str] = None
    xml_retorno_path: Optional[str] = None


@dataclass
class ResultadoCancelamentoFiscal:
    """Resultado do cancelamento de documento"""
    sucesso: bool
    mensagem: Optional[str] = None
    payload_retorno: Optional[Dict[str, Any]] = None


class IProvedorFiscal(ABC):
    """Interface comum para provedores fiscais (NFS-e nacional, NF-e gateway, etc.)."""

    @abstractmethod
    def enviar_nfse(self, empresa_id: int, nota_servico_id: int, payload: Dict[str, Any]) -> ResultadoEnvioFiscal:
        """Envia NFS-e ao provedor. payload contém dados da nota e itens."""
        ...

    @abstractmethod
    def enviar_nfe(self, empresa_id: int, nota_fiscal_id: int, payload: Dict[str, Any]) -> ResultadoEnvioFiscal:
        """Envia NF-e ao provedor."""
        ...

    @abstractmethod
    def enviar_nfce(self, empresa_id: int, nota_fiscal_id: int, payload: Dict[str, Any]) -> ResultadoEnvioFiscal:
        """Envia NFC-e ao provedor."""
        ...

    @abstractmethod
    def cancelar_nfse(self, empresa_id: int, nota_servico_id: int, motivo: str) -> ResultadoCancelamentoFiscal:
        """Cancela NFS-e no provedor."""
        ...

    @abstractmethod
    def cancelar_nfe(self, empresa_id: int, nota_fiscal_id: int, motivo: str) -> ResultadoCancelamentoFiscal:
        """Cancela NF-e no provedor."""
        ...

    @abstractmethod
    def cancelar_nfce(self, empresa_id: int, nota_fiscal_id: int, motivo: str) -> ResultadoCancelamentoFiscal:
        """Cancela NFC-e no provedor."""
        ...

    def consultar_status_nfse(self, empresa_id: int, nota_servico_id: int) -> Optional[Dict[str, Any]]:
        """Consulta status da NFS-e no provedor (opcional)."""
        return None

    def consultar_status_nfe(self, empresa_id: int, nota_fiscal_id: int) -> Optional[Dict[str, Any]]:
        """Consulta status da NF-e no provedor (opcional)."""
        return None
