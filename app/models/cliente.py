# PDV Ibix - Cliente Model
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, Float, Index, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class Cliente(BaseModel):
    """Modelo para tabela de clientes. Registros podem ser Cliente (Empresa Fiscal, emissor) ou Subcliente (destinatário das notas). PJ = CNPJ; PF = CPF."""
    __tablename__ = "clientes"

    # Campos
    nome = Column(String(255), nullable=False)
    cnpj = Column(String(18), nullable=True, index=True)  # único por escopo do CA (subcliente), não global
    cpf = Column(String(14), nullable=True, index=True)
    cep = Column(String(20), nullable=True)  # CEP opcional (formato 00000-000 ou variações)
    endereco = Column(String(500), nullable=False)
    cidade = Column(String(100), nullable=False)
    uf = Column(String(2), nullable=False)
    municipio_ibge = Column(Integer, nullable=True, comment="Código IBGE do município (tomador NFS-e)")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geocoding_precision = Column(
        String(20),
        nullable=True,
        comment="Precisao da geocodificacao da loja: rooftop|range_interpolated|locality|manual.",
    )
    contato = Column(String(100), nullable=False)
    telefone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)

    # Dados bancários + PIX (obrigatórios apenas no cadastro do CA; para subclientes pode ficar vazio)
    banco_nome = Column(String(100), nullable=True)
    banco_codigo = Column(String(10), nullable=True)
    agencia = Column(String(20), nullable=True)
    conta = Column(String(30), nullable=True)
    tipo_conta = Column(String(20), nullable=True)
    pix_chave = Column(String(120), nullable=True)
    
    # Relacionamentos
    alertas_email = relationship("AlertaEmail", back_populates="cliente", cascade="all, delete-orphan")
    areas_cliente = relationship("AreaCliente", back_populates="cliente", cascade="all, delete-orphan")
    ordens_servico = relationship("OrdemServico", back_populates="cliente", cascade="all, delete-orphan")
    loja_marketplace = relationship("LojaMarketplace", back_populates="cliente", uselist=False, cascade="all, delete-orphan")
    categorias_vitrine = relationship(
        "ClienteMaterialCategoria",
        back_populates="cliente",
        cascade="all, delete-orphan",
    )
    
    # Índices e restrições: pelo menos um de cnpj/cpf; cada um único quando preenchido
    __table_args__ = (
        Index('idx_clientes_cnpj', 'cnpj'),
        Index('idx_clientes_cpf', 'cpf'),
        Index('idx_clientes_cidade', 'cidade'),
        Index('idx_clientes_uf', 'uf'),
        Index('idx_clientes_geocoding_precision', 'geocoding_precision'),
        CheckConstraint('cnpj IS NOT NULL OR cpf IS NOT NULL', name='ck_clientes_cnpj_ou_cpf'),
    )

    def __repr__(self):
        doc = self.cnpj or self.cpf or ''
        return f"<Cliente(id={self.id}, nome='{self.nome}', doc='{doc}')>" 