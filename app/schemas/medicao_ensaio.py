# PDV Ibix - Schemas para Medições de Ensaio com Peso Padrão
from datetime import date
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class PesoResumoItem(BaseModel):
    """Schema para item de resumo de peso usado no ensaio"""
    id: int = Field(..., description="ID da peça de peso")
    valor_nominal: Decimal = Field(..., description="Valor nominal do peso")
    unidade: str = Field(..., description="Unidade (kg, g, etc.)")
    classe: Optional[str] = Field(None, description="Classe do peso")
    identificador: str = Field(..., description="Identificador da peça")
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class MedicaoEnsaioBase(BaseModel):
    """Schema base para uma medição de ensaio"""
    ponto: int = Field(..., description="Número do ponto de medição")
    carga: Decimal = Field(..., description="Carga aplicada no ensaio")
    valor_nominal: Optional[Decimal] = Field(None, description="Valor nominal (legado, pode ser igual a carga)")
    leitura_1: Optional[Decimal] = Field(None, description="Primeira leitura")
    leitura_2: Optional[Decimal] = Field(None, description="Segunda leitura")
    leitura_3: Optional[Decimal] = Field(None, description="Terceira leitura")
    leitura_4: Optional[Decimal] = Field(None, description="Quarta leitura (ex.: excentricidade)")
    media: Optional[Decimal] = Field(None, description="Média das leituras")
    erro: Optional[Decimal] = Field(None, description="Erro calculado")
    erro_percentual: Optional[Decimal] = Field(None, description="Erro percentual")
    dentro_tolerancia: Optional[bool] = Field(None, description="Se está dentro da tolerância")
    
    # Ordem cronológica (ISO 17025 Fase 3.3)
    ordem_execucao: Optional[int] = Field(None, description="Ordem de execução do ponto (1, 2, 3...)")
    timestamp: Optional[int] = Field(None, description="Timestamp da medição (ex.: Date.now()) para rastreabilidade")
    
    # Campos de incerteza (Plano V2 / ISO 17025)
    incerteza: Optional[Decimal] = Field(None, description="Incerteza de medição (obrigatório para certificado)")
    origem_incerteza: Optional[str] = Field(None, description="Origem da incerteza: 'calculada' ou 'informada'")
    fator_abrangencia: Optional[Decimal] = Field(Decimal("2"), description="Fator de abrangência k (default 2 para 95%)")

    @field_validator("fator_abrangencia", mode="before")
    @classmethod
    def coerce_fator_abrangencia(cls, v: Any) -> Optional[Decimal]:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))
    
    # Campos de peso padrão (obrigatórios quando usar peso padrão)
    pesos_ids: Optional[List[int]] = Field(None, description="IDs das peças de peso usadas (obrigatório se usar peso padrão)")
    pesos_resumo: Optional[List[PesoResumoItem]] = Field(None, description="Resumo dos pesos usados (opcional mas recomendado)")
    certificado_numero: Optional[str] = Field(None, description="Número do certificado do conjunto (obrigatório se usar peso padrão)")
    validade_min: Optional[date] = Field(None, description="Validade mínima entre os pesos usados (obrigatório se usar peso padrão)")
    
    # Campos para ensaio Mobilidade (PESOPADRAO: carga_kg + sobrecarga_kg do cadastro)
    sobrecarga: Optional[Decimal] = Field(None, description="Sobrecarga em kg (mobilidade)")
    leitura_antes: Optional[Decimal] = Field(None, description="Leitura antes (mobilidade)")
    leitura_depois: Optional[Decimal] = Field(None, description="Leitura depois (mobilidade)")
    padrao_utilizado: Optional[str] = Field(None, description="Certificado/nome do padrão utilizado (mobilidade)")
    padrao_utilizado_id: Optional[int] = Field(None, description="aux_cadastro_id do PESOPADRAO (mobilidade)")
    
    class Config:
        json_encoders = {
            Decimal: str,
            date: lambda v: v.isoformat() if v else None
        }


class MedicaoEnsaioCreate(MedicaoEnsaioBase):
    """Schema para criação de medição de ensaio"""
    pass


class MedicaoEnsaioResponse(MedicaoEnsaioBase):
    """Schema para resposta de medição de ensaio"""
    pass


class MedicoesEnsaioLote(BaseModel):
    """Schema para lote de medições de ensaio"""
    medicoes: List[MedicaoEnsaioCreate] = Field(..., description="Lista de medições do ensaio")
    tipo_ensaio: Optional[str] = Field(None, alias="tipoEnsaio", description="Tipo: indicacao, excentricidade, mobilidade (para gravar em balanca.ensaios_*_json)")
    
    class Config:
        populate_by_name = True
    
    @field_validator('medicoes')
    @classmethod
    def validar_medicoes_nao_vazias(cls, v: List) -> List:
        if not v or len(v) == 0:
            raise ValueError("Lista de medições não pode estar vazia")
        return v
