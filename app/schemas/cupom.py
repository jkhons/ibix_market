# PDV Ibix - Schemas para configuração e conteúdo de cupom de venda
from typing import List, Optional

from pydantic import BaseModel, Field


class TenantCupomConfigResponse(BaseModel):
    """Resposta da config de cupom do tenant (CA)."""
    cupom_impressao_modo: Optional[str] = Field(None, description="automatico | manual")
    cupom_tipo: Optional[str] = Field(None, description="nao_fiscal | fiscal")
    cupom_fiscal_emissor: Optional[str] = Field(None, description="interno | externo (futuro)")


class TenantCupomConfigUpdate(BaseModel):
    """Payload para atualizar config de cupom do tenant."""
    cupom_impressao_modo: Optional[str] = Field(None, description="automatico | manual")
    cupom_tipo: Optional[str] = Field(None, description="nao_fiscal | fiscal")
    cupom_fiscal_emissor: Optional[str] = Field(None, description="interno | externo (futuro)")


class CupomConteudoResponse(BaseModel):
    """Conteúdo do cupom para impressão (térmica e/ou browser)."""
    tipo: str = Field(..., description="nao_fiscal | fiscal")
    linhas: List[str] = Field(default_factory=list, description="Linhas de texto para impressora térmica")
    html: Optional[str] = Field(None, description="Fragmento HTML para window.print() no browser")
