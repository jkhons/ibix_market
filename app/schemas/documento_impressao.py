from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


TipoDocumentoImpressao = Literal["orcamento", "ordem_servico"]


class DocumentoImpressaoTemplateCreate(BaseModel):
    tipo_documento: TipoDocumentoImpressao
    nome: str = Field(..., min_length=1, max_length=120)
    conteudo_html: str = Field(..., min_length=1)
    css_extra: Optional[str] = None
    is_padrao: bool = False
    ativo: bool = True


class DocumentoImpressaoTemplateUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=120)
    conteudo_html: Optional[str] = Field(None, min_length=1)
    css_extra: Optional[str] = None
    is_padrao: Optional[bool] = None
    ativo: Optional[bool] = None


class DocumentoImpressaoTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    tipo_documento: str
    nome: str
    conteudo_html: str
    css_extra: Optional[str] = None
    is_padrao: bool
    ativo: bool
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentoImpressaoTemplateList(BaseModel):
    templates: List[DocumentoImpressaoTemplateResponse]
    total: int


class DocumentoImpressaoPreviewRequest(BaseModel):
    tipo_documento: TipoDocumentoImpressao
    conteudo_html: str = Field(..., min_length=1)
    css_extra: Optional[str] = None
