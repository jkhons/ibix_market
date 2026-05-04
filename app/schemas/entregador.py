# PDV Ibix - Schemas Entregador
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class EntregadorLoginIn(BaseModel):
    email: EmailStr
    senha: str


class EntregadorResponse(BaseModel):
    id: int
    nome: str
    email: str
    tipo_veiculo: Optional[str] = None

    model_config = {"from_attributes": True}


class EntregadorLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    entregador: EntregadorResponse


# --- Veículos do entregador ---
class EntregadorVeiculoCreate(BaseModel):
    tipo_veiculo: str = Field(..., max_length=20)
    capacidade_kg: Optional[Decimal] = None
    descricao: Optional[str] = Field(None, max_length=100)
    placa: Optional[str] = Field(None, max_length=10)


class EntregadorVeiculoUpdate(BaseModel):
    tipo_veiculo: Optional[str] = Field(None, max_length=20)
    capacidade_kg: Optional[Decimal] = None
    descricao: Optional[str] = Field(None, max_length=100)
    placa: Optional[str] = Field(None, max_length=10)
    ativo: Optional[bool] = None


class EntregadorVeiculoResponse(BaseModel):
    id: int
    entregador_id: int
    tipo_veiculo: Optional[str] = None
    capacidade_kg: Optional[Decimal] = None
    descricao: Optional[str] = None
    placa: Optional[str] = None
    ativo: bool = True
    documento_aprovado: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EntregadorMeOut(BaseModel):
    id: int
    nome: str
    email: str
    status: str
    ativo: bool
    tem_veiculo_aprovado: bool
    pode_operar: bool


class CadastroPublicoEntregadorOk(BaseModel):
    mensagem: str


class PainelResumoOut(BaseModel):
    quantidade_disponiveis: int
    soma_valor_frete_disponiveis: Decimal
    quantidade_minhas_andamento: int
    quantidade_minhas_encerradas: int
    soma_repasse_pedidos_com_custo: Decimal
    pedidos_sem_custo_frete: int
    totais_pagamento: Dict[str, float]


class PainelCorridaMinhaOut(BaseModel):
    entrega_id: int
    pedido_id: int
    valor_frete: Decimal
    valor_repasse_entregador: Optional[Decimal]
    status_entrega: str
    status_pagamento_entregador: str
