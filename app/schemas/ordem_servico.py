from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


# Schemas para tipos de ordem de serviço (tabela ordem_servico_tipo por tenant)
class OrdemServicoTipoResponse(BaseModel):
    id: int
    tenant_id: int
    nome: str
    codigo: Optional[str] = None
    ativo: bool = True

    class Config:
        from_attributes = True


class OrdemServicoTipoCreate(BaseModel):
    nome: str = Field(..., max_length=100)
    codigo: Optional[str] = Field(None, max_length=50)
    ativo: bool = True
    tenant_id: Optional[int] = None  # opcional; se omitido, usa tenant efetivo do usuário


class OrdemServicoTipoUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=100)
    codigo: Optional[str] = Field(None, max_length=50)
    ativo: Optional[bool] = None


class OrdemServicoPrioridadeEnum(str, Enum):
    baixa = "baixa"
    media = "media"
    alta = "alta"
    critica = "critica"


class OrdemServicoStatusEnum(str, Enum):
    aberta = "aberta"
    em_andamento = "em_andamento"
    aguardando_material = "aguardando_material"
    aguardando_cliente = "aguardando_cliente"
    concluida = "concluida"
    cancelada = "cancelada"


class OrdemServicoItemBase(BaseModel):
    produto_cliente_id: Optional[int] = Field(None, description="ID do produto (produtos_cliente)")
    codigo: Optional[str] = Field(None, max_length=50, description="Código interno do item")
    nome: str = Field(..., max_length=255, description="Descrição do item")
    unidade: Optional[str] = Field(None, max_length=20, description="Unidade de medida")
    quantidade: Decimal = Field(..., gt=0, description="Quantidade utilizada")
    valor_unitario: Decimal = Field(..., ge=0, description="Valor unitário aplicado")
    desconto: Decimal = Field(Decimal("0.00"), ge=0, description="Desconto aplicado ao item")
    valor_total: Optional[Decimal] = Field(None, ge=0, description="Valor total do item")
    observacao: Optional[str] = Field(None, description="Observações específicas do item")
    lacre_lote_id: Optional[int] = Field(None, description="ID do lote de lacre aplicado")
    lacre_serial: Optional[int] = Field(None, description="Serial do lacre aplicado")
    historico_selo_id: Optional[int] = Field(None, description="ID do histórico de selo associado")

    @validator("valor_total", always=True)
    def calcular_valor_total(cls, v: Optional[Decimal], values) -> Decimal:
        quantidade = values.get("quantidade") or Decimal("0")
        valor_unitario = values.get("valor_unitario") or Decimal("0")
        desconto = values.get("desconto") or Decimal("0")
        calculado = quantidade * valor_unitario - desconto
        if calculado < Decimal("0"):
            calculado = Decimal("0")
        return v if v is not None else calculado.quantize(Decimal("0.01"))


class OrdemServicoItemCreate(OrdemServicoItemBase):
    pass


class OrdemServicoItemUpdate(OrdemServicoItemBase):
    id: Optional[int] = Field(None, description="ID do item para atualização")


class OrdemServicoItemResponse(OrdemServicoItemBase):
    id: int
    ordem_servico_id: int

    class Config:
        from_attributes = True


class OrdemServicoBase(BaseModel):
    cliente_id: int
    tipo_id: int
    prioridade: OrdemServicoPrioridadeEnum = OrdemServicoPrioridadeEnum.media
    status: OrdemServicoStatusEnum = OrdemServicoStatusEnum.aberta
    responsavel_id: Optional[int] = None
    lacre_utilizado_id: Optional[int] = None
    data_prevista: Optional[datetime] = None
    data_conclusao: Optional[datetime] = None
    observacoes: Optional[str] = None


class OrdemServicoCreate(OrdemServicoBase):
    codigo: Optional[str] = Field(None, description="Identificador único da OS (se vazio, será gerado)")
    itens: List[OrdemServicoItemCreate] = Field(
        default_factory=list,
        description="Itens/peças utilizados na OS",
    )


class OrdemServicoUpdate(BaseModel):
    tipo_id: Optional[int] = None
    prioridade: Optional[OrdemServicoPrioridadeEnum] = None
    status: Optional[OrdemServicoStatusEnum] = None
    responsavel_id: Optional[int] = None
    lacre_utilizado_id: Optional[int] = None
    data_prevista: Optional[datetime] = None
    data_conclusao: Optional[datetime] = None
    observacoes: Optional[str] = None
    itens: Optional[List[OrdemServicoItemUpdate]] = None


class OrdemServicoResumoResponse(BaseModel):
    id: int
    codigo: str
    cliente_id: int
    cliente_nome: Optional[str]
    status: OrdemServicoStatusEnum
    tipo_id: int
    tipo_nome: Optional[str] = None
    prioridade: OrdemServicoPrioridadeEnum
    data_abertura: datetime
    data_prevista: Optional[datetime]
    data_conclusao: Optional[datetime]
    venda_id: Optional[int] = None
    venda_numero: Optional[str] = None

    class Config:
        from_attributes = True


class OrdemServicoResponse(OrdemServicoResumoResponse):
    responsavel_id: Optional[int]
    responsavel_nome: Optional[str]
    lacre_utilizado_id: Optional[int]
    observacoes: Optional[str]
    itens: List[OrdemServicoItemResponse] = Field(default_factory=list)


class OrdemServicoListResponse(BaseModel):
    ordens: List[OrdemServicoResumoResponse]
    total: int


