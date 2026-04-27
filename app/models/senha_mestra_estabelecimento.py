# PDV Ibix - Senha mestra por estabelecimento (Fase 5.2)
"""Uma senha mestra por estabelecimento (cliente_id). Validade temporária (expira_em). Nunca hardcoded."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class SenhaMestraEstabelecimento(BaseModel):
    """Senha mestra do estabelecimento: sangria/suprimento, descontos acima do limite, cancelamento. Por estabelecimento, não global."""
    __tablename__ = "senha_mestra_estabelecimento"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Estabelecimento (clientes.id); uma senha por estabelecimento",
    )
    senha_hash = Column(
        String(255),
        nullable=False,
        comment="Hash da senha mestra (bcrypt)",
    )
    expira_em = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Validade temporária; null = até próxima alteração",
    )

    cliente = relationship("Cliente", backref="senha_mestra_estabelecimento")

    def __repr__(self):
        return f"<SenhaMestraEstabelecimento(cliente_id={self.cliente_id})>"
