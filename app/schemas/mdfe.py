# PDV Ibix - Schemas de MDF-e (Manifesto Eletrônico de Documentos Fiscais)
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StatusMDFeEnum(str, Enum):
    """Enum para status do MDF-e"""
    PENDENTE = "pendente"
    AUTORIZADO = "autorizado"
    CANCELADO = "cancelado"
    ENCERRADO = "encerrado"
    REJEITADO = "rejeitado"

class TipoDocumentoEnum(str, Enum):
    """Enum para tipo de documento vinculado"""
    NFE = "NFe"
    CTE = "CTe"

# Schemas para Documentos
class MDFeDocumentoBase(BaseModel):
    """Schema base para documento do MDF-e"""
    tipo_documento: TipoDocumentoEnum = Field(..., description="Tipo de documento vinculado (NFe ou CTe)")
    chave_acesso: str = Field(..., min_length=44, max_length=44, description="Chave de acesso do documento (NF-e ou CT-e)")
    valor: Optional[Decimal] = Field(None, ge=0, description="Valor do documento")
    peso: Optional[Decimal] = Field(None, ge=0, description="Peso do documento (em kg)")

class MDFeDocumentoCreate(MDFeDocumentoBase):
    """Schema para criação de documento do MDF-e"""
    pass

class MDFeDocumentoResponse(MDFeDocumentoBase):
    """Schema para resposta de documento do MDF-e"""
    id: int
    mdfe_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schemas para Veículos
class MDFeVeiculoBase(BaseModel):
    """Schema base para veículo do MDF-e"""
    placa: str = Field(..., min_length=7, max_length=7, description="Placa do veículo")
    renavam: Optional[str] = Field(None, max_length=20, description="RENAVAM do veículo")
    tara: Optional[Decimal] = Field(None, ge=0, description="Tara do veículo (em kg)")
    capacidade_kg: Optional[Decimal] = Field(None, ge=0, description="Capacidade de carga em kg")
    capacidade_m3: Optional[Decimal] = Field(None, ge=0, description="Capacidade de carga em m³")
    tipo_rodado: Optional[str] = Field(None, max_length=50, description="Tipo de rodado")
    tipo_carroceria: Optional[str] = Field(None, max_length=50, description="Tipo de carroceria")
    uf: Optional[str] = Field(None, max_length=2, description="UF de licenciamento do veículo")

class MDFeVeiculoCreate(MDFeVeiculoBase):
    """Schema para criação de veículo do MDF-e"""
    pass

class MDFeVeiculoResponse(MDFeVeiculoBase):
    """Schema para resposta de veículo do MDF-e"""
    id: int
    mdfe_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schemas para Condutores
class MDFeCondutorBase(BaseModel):
    """Schema base para condutor do MDF-e"""
    nome: str = Field(..., min_length=1, max_length=255, description="Nome do condutor")
    cpf: Optional[str] = Field(None, max_length=11, description="CPF do condutor")

class MDFeCondutorCreate(MDFeCondutorBase):
    """Schema para criação de condutor do MDF-e"""
    pass

class MDFeCondutorResponse(MDFeCondutorBase):
    """Schema para resposta de condutor do MDF-e"""
    id: int
    mdfe_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schemas para Percursos
class MDFePercursoBase(BaseModel):
    """Schema base para percurso do MDF-e"""
    uf: str = Field(..., min_length=2, max_length=2, description="UF do percurso")

class MDFePercursoCreate(MDFePercursoBase):
    """Schema para criação de percurso do MDF-e"""
    pass

class MDFePercursoResponse(MDFePercursoBase):
    """Schema para resposta de percurso do MDF-e"""
    id: int
    mdfe_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schemas para MDF-e
class MDFeBase(BaseModel):
    """Schema base para MDF-e"""
    numero: str = Field(..., min_length=1, max_length=20, description="Número do MDF-e")
    serie: str = Field("1", max_length=10, description="Série do MDF-e")
    codigo_mdfe: Optional[str] = Field(None, max_length=50, description="Código numérico do MDF-e")
    chave_acesso: Optional[str] = Field(None, max_length=44, description="Chave de acesso do MDF-e (44 dígitos)")
    
    data_emissao: datetime = Field(..., description="Data e hora de emissão do MDF-e")
    
    empresa_id: int = Field(..., description="ID da empresa emitente")
    
    tipo_emitente: Optional[int] = Field(None, description="Tipo de emitente (1=Transportador, 2=Carga própria)")
    uf_inicio: str = Field(..., min_length=2, max_length=2, description="UF de início do transporte")
    uf_fim: str = Field(..., min_length=2, max_length=2, description="UF de fim do transporte")
    
    qtd_cte: int = Field(0, ge=0, description="Quantidade de CT-e vinculados")
    valor_total_carga: Optional[Decimal] = Field(None, ge=0, description="Valor total da carga")
    peso_bruto_total: Optional[Decimal] = Field(None, ge=0, description="Peso bruto total (em kg)")
    
    status: StatusMDFeEnum = Field(StatusMDFeEnum.PENDENTE, description="Status do MDF-e")
    protocolo_autorizacao: Optional[str] = Field(None, max_length=50, description="Protocolo de autorização retornado pela SEFAZ")
    data_autorizacao: Optional[datetime] = Field(None, description="Data e hora da autorização")
    mensagem_retorno: Optional[str] = Field(None, description="Mensagem retornada pela SEFAZ")
    
    xml_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo XML assinado")
    xml_retorno_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo XML de retorno da SEFAZ")

class MDFeCreate(MDFeBase):
    """Schema para criação de MDF-e"""
    documentos: List[MDFeDocumentoCreate] = Field(default_factory=list, description="Documentos vinculados (NF-es/CT-es)")
    veiculos: List[MDFeVeiculoCreate] = Field(..., min_items=1, description="Veículos do transporte")
    condutores: List[MDFeCondutorCreate] = Field(default_factory=list, description="Condutores")
    percursos: List[MDFePercursoCreate] = Field(default_factory=list, description="Percursos (UFs)")

class MDFeUpdate(BaseModel):
    """Schema para atualização de MDF-e"""
    status: Optional[StatusMDFeEnum] = None
    protocolo_autorizacao: Optional[str] = Field(None, max_length=50)
    data_autorizacao: Optional[datetime] = None
    mensagem_retorno: Optional[str] = None
    xml_path: Optional[str] = Field(None, max_length=255)
    xml_retorno_path: Optional[str] = Field(None, max_length=255)

class MDFeResponse(MDFeBase):
    """Schema para resposta de MDF-e"""
    id: int
    documentos: List[MDFeDocumentoResponse] = []
    veiculos: List[MDFeVeiculoResponse] = []
    condutores: List[MDFeCondutorResponse] = []
    percursos: List[MDFePercursoResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

