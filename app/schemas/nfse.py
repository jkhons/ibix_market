# PDV Ibix - Schemas Pydantic NFS-e (conforme MODULO_FATURAMENT_V2.MD Parte V e VII)
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class NfseInvoiceCreate(BaseModel):
    """Criação genérica de NFS-e (campos mínimos)."""
    tenant_id: int
    empresa_id: int
    cliente_id: Optional[int] = None
    origin_type: str  # SUBSCRIPTION | OS | MANUAL
    origin_id: Optional[int] = None
    municipio_prestacao_ibge: int
    data_competencia: date
    descricao_servico: Optional[str] = None
    item_lista_servico: Optional[str] = None
    cnae: Optional[str] = None
    valor_servicos: float = 0
    valor_deducoes: float = 0
    aliquota_iss: float = 0
    iss_retido: bool = False
    valor_iss_retido: float = 0


class NfseInvoiceCreateFromSubscription(BaseModel):
    """Criação a partir de subscription (recorrente)."""
    subscription_id: int
    empresa_id: int
    cliente_id: Optional[int] = None
    municipio_ibge: int
    competencia: date
    descricao_servico: str
    valor_servicos: float
    aliquota_iss: float
    iss_retido: bool = False
    valor_iss_retido: float = 0


class NfseInvoiceCreateFromOS(BaseModel):
    """Criação a partir de ordem de serviço."""
    ordem_servico_id: int
    empresa_id: int
    cliente_id: Optional[int] = None
    municipio_ibge: int
    competencia: date
    descricao_servico: str
    valor_servicos: float
    aliquota_iss: float
    iss_retido: bool = False
    valor_iss_retido: float = 0


class NfseIssueRequest(BaseModel):
    """Solicitação de emissão (enfileirar)."""
    invoice_id: int


class NfseCancelRequest(BaseModel):
    """Solicitação de cancelamento."""
    invoice_id: int
    reason: str
    codigo_cancelamento: Optional[str] = None


class TenantNfseConfigUpdate(BaseModel):
    """Atualização da config NFS-e do tenant (CA): emissor e tomador padrão."""
    default_empresa_id: Optional[int] = None
    ca_cliente_id: Optional[int] = None


class TenantNfseConfigResponse(BaseModel):
    """Config atual do tenant + listas para selects (empresas e clientes do escopo)."""
    default_empresa_id: Optional[int] = None
    ca_cliente_id: Optional[int] = None
    empresas: List[dict]  # [{"id": 1, "razao_social": "..."}]
    clientes: List[dict]  # [{"id": 1, "nome": "..."}]


class NfseInvoiceResponse(BaseModel):
    """Resposta com dados da NFS-e (para API)."""
    id: int
    tenant_id: int
    empresa_id: int
    cliente_id: Optional[int] = None
    origin_type: str
    origin_id: Optional[int] = None
    status: str
    numero_nfse: Optional[str] = None
    codigo_verificacao: Optional[str] = None
    url_consulta: Optional[str] = None
    data_emissao: Optional[datetime] = None
    valor_servicos: Decimal
    valor_iss: Decimal
    last_error_code: Optional[str] = None
    last_error_msg: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
