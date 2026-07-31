# Templates configuráveis de impressão/PDF (Orçamento · OS) — escopo tenant
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database.base import BaseModel


class DocumentoImpressaoTemplate(BaseModel):
    __tablename__ = "documento_impressao_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "tipo_documento", "nome", name="uq_doc_imp_tenant_tipo_nome"),
    )

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_documento = Column(String(30), nullable=False, comment="orcamento | ordem_servico")
    nome = Column(String(120), nullable=False)
    conteudo_html = Column(Text, nullable=False)
    css_extra = Column(Text, nullable=True)
    is_padrao = Column(Boolean, nullable=False, default=False, server_default="false")
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    created_by = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
