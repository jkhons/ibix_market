# PDV Ibix - Schemas para ProcessoBalancaCalibracao
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EtapaBalancaEnum(str, Enum):
    """Etapas possíveis para uma balança no processo"""
    pre_checagem = "pre_checagem"
    ensaio_inicial = "ensaio_inicial"
    ajuste = "ajuste"
    ensaio_final = "ensaio_final"
    concluido = "concluido"
    reprovado = "reprovado"

class ResultadoBalancaEnum(str, Enum):
    """Resultados possíveis para uma balança"""
    aprovado = "aprovado"
    reprovado = "reprovado"
    pendente = "pendente"

class ProcessoBalancaCalibracaoBase(BaseModel):
    """Schema base para ProcessoBalancaCalibracao"""
    equipamento_id: int = Field(..., description="ID do equipamento")
    tecnico_responsavel_id: Optional[int] = Field(None, description="ID do técnico responsável")
    etapa_atual: EtapaBalancaEnum = Field(default=EtapaBalancaEnum.pre_checagem, description="Etapa atual da balança")
    resultado_final: Optional[ResultadoBalancaEnum] = Field(None, description="Resultado final da balança")
    
    # Dados de calibração
    afer_tara: Optional[float] = Field(None, description="Leitura sem peso (tara) em kg")
    afer_peso: Optional[float] = Field(None, description="Peso aplicado em kg")
    afer_diferenc: Optional[float] = Field(None, description="Diferença calculada em kg")
    
    # Dados técnicos
    local_calibracao: Optional[str] = Field(None, description="Local da calibração")
    lacre_retirado: Optional[str] = Field(None, description="Número do lacre retirado")
    lacre_lote_id: Optional[int] = Field(None, description="ID do lote de lacre aplicado")
    lacre_serial: Optional[int] = Field(None, description="Serial do lacre aplicado")
    historico_selo_id: Optional[int] = Field(None, description="ID do histórico de selo associado")
    portaria: Optional[str] = Field(None, description="Número da portaria")
    observacoes: Optional[str] = Field(None, description="Observações específicas")

class ProcessoBalancaCalibracaoCreate(ProcessoBalancaCalibracaoBase):
    """Schema para criação de ProcessoBalancaCalibracao"""
    pass

class ProcessoBalancaCalibracaoUpdate(BaseModel):
    """Schema para atualização de ProcessoBalancaCalibracao"""
    etapa_atual: Optional[EtapaBalancaEnum] = None
    resultado_final: Optional[ResultadoBalancaEnum] = None
    afer_tara: Optional[float] = None
    afer_peso: Optional[float] = None
    afer_diferenc: Optional[float] = None
    local_calibracao: Optional[str] = None
    lacre_retirado: Optional[str] = None
    lacre_lote_id: Optional[int] = None
    lacre_serial: Optional[int] = None
    historico_selo_id: Optional[int] = None
    portaria: Optional[str] = None
    observacoes: Optional[str] = None
    procedimento_metodo_id: Optional[int] = None
    # Condições ambientais (Etapa 3)
    temperatura_inicial: Optional[float] = Field(None, ge=-9999.99, le=9999.99, description="Temperatura inicial em °C")
    temperatura_final: Optional[float] = Field(None, ge=-9999.99, le=9999.99, description="Temperatura final em °C")
    umidade_inicial: Optional[float] = Field(None, ge=0, le=100, description="Umidade inicial em %")
    umidade_final: Optional[float] = Field(None, ge=0, le=100, description="Umidade final em %")
    pressao_inicial: Optional[float] = Field(None, ge=0, le=999999.99, description="Pressão inicial")
    pressao_final: Optional[float] = Field(None, ge=0, le=999999.99, description="Pressão final")
    massa_ar_inicial: Optional[float] = Field(None, ge=0, le=9999.99, description="Massa específica do ar inicial em Kg/m³")
    massa_ar_final: Optional[float] = Field(None, ge=0, le=9999.99, description="Massa específica do ar final em Kg/m³")

class ProcessoBalancaCalibracaoResponse(ProcessoBalancaCalibracaoBase):
    """Schema de resposta para ProcessoBalancaCalibracao"""
    id: int
    processo_id: int
    data_inicio: Optional[datetime] = None
    data_conclusao: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Dados relacionados
    equipamento: Optional[dict] = None
    tecnico_responsavel: Optional[dict] = None
    lacre_lote: Optional[dict] = None
    historico_selo: Optional[dict] = None
    
    class Config:
        from_attributes = True

class ProcessoBalancaCalibracaoListResponse(BaseModel):
    """Schema para lista de ProcessoBalancaCalibracao"""
    balancas: List[ProcessoBalancaCalibracaoResponse]
    total: int
    processo_id: int
    numero_processo: str
    
    class Config:
        from_attributes = True
