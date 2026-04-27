# PDV Ibix - Schemas Entrega Marketplace (logística local)
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel


# --- Endereço JSON (contrato interno) ---
# Contrato padronizado para endereco_retirada_json e endereco_entrega_json (JSONB).
# Usar estes campos ao montar/validar endereços no service e nas APIs.
class EnderecoEntregaJson(BaseModel):
    """Contrato interno para endereço em entregas: cep, logradouro, numero, complemento, bairro, cidade, uf, referencia."""
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    referencia: Optional[str] = None


# --- Criação (tenant) ---
class EntregaCreateIn(BaseModel):
    pedido_id: int
    valor_frete: Decimal
    tipo_veiculo_aceito: Optional[str] = None  # moto, carro, utilitario, qualquer
    observacoes: Optional[str] = None
    aceita_ate_em: Optional[datetime] = None


# --- Atualização de status (entregador) ---
class EntregaStatusUpdateIn(BaseModel):
    novo_status: str  # em_retirada, retirada, em_rota, entregue, falha_entrega


# --- Respostas ---
class EntregaEventoOut(BaseModel):
    id: int
    tipo_evento: str
    actor_type: str
    actor_id: Optional[int] = None
    payload_json: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EntregaDisponivelOut(BaseModel):
    id: int
    pedido_id: int
    loja_nome: Optional[str] = None
    bairro_retirada: Optional[str] = None
    bairro_entrega: Optional[str] = None
    valor_frete: Decimal
    tipo_veiculo_aceito: Optional[str] = None
    observacoes: Optional[str] = None

    model_config = {"from_attributes": True}


class EntregaOut(BaseModel):
    id: int
    pedido_id: int
    tenant_id: int
    entregador_id: Optional[int] = None
    status: str
    valor_frete: Decimal
    tipo_veiculo_aceito: Optional[str] = None
    nome_retirada: Optional[str] = None
    telefone_retirada: Optional[str] = None
    endereco_retirada_json: Optional[Any] = None
    nome_destinatario: Optional[str] = None
    telefone_destinatario: Optional[str] = None
    endereco_entrega_json: Optional[Any] = None
    observacoes: Optional[str] = None
    aceita_ate_em: Optional[datetime] = None
    publicada_em: Optional[datetime] = None
    aceita_em: Optional[datetime] = None
    retirada_em: Optional[datetime] = None
    saiu_para_entrega_em: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    cancelada_em: Optional[datetime] = None
    created_at: Optional[datetime] = None
    eventos: List[EntregaEventoOut] = []

    model_config = {"from_attributes": True}
