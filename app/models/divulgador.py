# PDV Ibix - Divulgador/parceiro (Fase 2 + Modulo Influencers)
"""Pessoa divulgadora: representante ou influenciador digital."""
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class Divulgador(BaseModel):
    """Pessoa divulgadora/parceiro — unifica representantes e influencers."""
    __tablename__ = "divulgadores"

    nome = Column(String(255), nullable=False)
    cpf_cnpj = Column(String(20), nullable=True, comment="CPF ou CNPJ (opcional)")
    email = Column(String(255), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, comment="Vínculo opcional com usuário para login")

    tipo = Column(String(30), nullable=True, default="representante", comment="representante, influencer, parceiro")
    status = Column(String(30), nullable=True, default="aprovado", comment="pendente, teste, aprovado, parceiro, bloqueado")
    nicho = Column(String(100), nullable=True, comment="Area de atuacao: automotivo, moda, tecnologia, etc.")
    cidade = Column(String(150), nullable=True)
    estado = Column(String(2), nullable=True)
    redes_sociais = Column(Text, nullable=True, comment="JSON: {facebook, instagram, tiktok, youtube}")
    engajamento = Column(Integer, nullable=True, comment="Seguidores/alcance estimado")
    score_performance = Column(Integer, nullable=True, default=0, comment="Score calculado automaticamente")
    tipo_atuacao = Column(String(50), nullable=True, comment="propaganda, cupom, live, todos")
    bio = Column(Text, nullable=True, comment="Descricao curta do influencer")
    telefone = Column(String(20), nullable=True)
    foto_url = Column(String(500), nullable=True)

    usuario = relationship("Usuario", backref="divulgador_perfil")

    __table_args__ = (
        Index("ix_divulgadores_ativo", "ativo"),
        Index("ix_divulgadores_tipo", "tipo"),
        Index("ix_divulgadores_status", "status"),
        Index("ix_divulgadores_nicho", "nicho"),
        Index("ix_divulgadores_cidade", "cidade"),
        {"comment": "Divulgadores/parceiros comerciais e influencers"},
    )

    def __repr__(self):
        return f"<Divulgador(id={self.id}, nome='{self.nome}', tipo='{self.tipo}')>"
