from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class EnsaioExcentricidadeBase(BaseModel):
    ponto: str
    carga: Decimal
    leitura_antes: Optional[Decimal] = None
    erro_antes: Optional[Decimal] = None
    leitura_depois: Optional[Decimal] = None
    erro_depois: Optional[Decimal] = None


class EnsaioExcentricidadeCreate(EnsaioExcentricidadeBase):
    pass


class EnsaioExcentricidade(EnsaioExcentricidadeBase):
    id: int
    certificado_id: int

    class Config:
        from_attributes = True


class ResultadoEnsaioBase(BaseModel):
    ponto: int
    carga: Optional[Decimal] = None
    leitura_antes: Optional[Decimal] = None
    erro_antes: Optional[Decimal] = None
    leitura_depois: Optional[Decimal] = None
    erro_depois: Optional[Decimal] = None
    incerteza: Optional[Decimal] = None


class ResultadoEnsaioCreate(ResultadoEnsaioBase):
    pass


class ResultadoEnsaio(ResultadoEnsaioBase):
    id: int
    certificado_id: int

    class Config:
        from_attributes = True


class EnsaioMobilidadeBase(BaseModel):
    carga: Optional[Decimal] = None
    sobrecarga: Optional[Decimal] = None
    leitura_antes: Optional[Decimal] = None
    leitura_depois: Optional[Decimal] = None
    padrao_utilizado: Optional[str] = None


class EnsaioMobilidadeCreate(EnsaioMobilidadeBase):
    pass


class EnsaioMobilidade(EnsaioMobilidadeBase):
    id: int
    certificado_id: int

    class Config:
        from_attributes = True


# Schemas para operações em lote
class EnsaiosExcentricidadeLote(BaseModel):
    ensaios: List[EnsaioExcentricidadeCreate]


class ResultadosEnsaiosLote(BaseModel):
    resultados: List[ResultadoEnsaioCreate]


class EnsaiosMobilidadeLote(BaseModel):
    ensaios: List[EnsaioMobilidadeCreate] 