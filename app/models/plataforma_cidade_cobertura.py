# PDV Ibix - Cidades/regiões atendidas pela plataforma (marketplace)
from sqlalchemy import Boolean, Column, Integer, String

from ..database.base import BaseModel


class PlataformaCidadeCobertura(BaseModel):
    """Lista canônica de cidades onde a plataforma permite entrega marketplace.

    Quando existir ao menos uma linha ativa, o checkout valida cidade/UF e o Superadmin só
    cadastra área por loja (`loja_areas_entrega`) dentro desta lista.
    """

    __tablename__ = "plataforma_cidades_cobertura"

    cidade = Column(String(120), nullable=False)
    uf = Column(String(2), nullable=False)
    codigo_ibge = Column(Integer, nullable=True)
    ativo = Column(Boolean, nullable=False, server_default="true")

    def __repr__(self):
        return f"<PlataformaCidadeCobertura({self.id}, {self.cidade}-{self.uf}, ativo={self.ativo})>"
