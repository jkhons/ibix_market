# PDV Ibix - Modelo Produto por Estabelecimento (Fase 2)
"""Catálogo de produtos por estabelecimento (cliente_id = loja). Isolamento Loja A vs Loja B."""
from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class ProdutoCliente(BaseModel):
    """Produto do catálogo de um estabelecimento. Código único por cliente_id."""
    __tablename__ = "produtos_cliente"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Estabelecimento (clientes.id)",
    )
    codigo = Column(String(50), nullable=False, comment="Código/SKU único por estabelecimento")
    nome = Column(String(255), nullable=False)
    descricao = Column(Text(), nullable=True)
    ncm = Column(String(10), nullable=True)
    cfop_padrao = Column(String(10), nullable=True, comment="CFOP padrão para o produto (ex: 5102)")
    cest = Column(String(10), nullable=True, comment="Código Especificador da Substituição Tributária (emissão NF)")
    extipi = Column(String(5), nullable=True, comment="EX TIPI (emissão NF)")
    origem_mercadoria = Column(Integer, nullable=True, comment="Origem da mercadoria 0-8 (ICMS, emissão NF)")
    csosn = Column(String(5), nullable=True, comment="CSOSN (Simples Nacional) para emissão NF-e")
    cst_icms = Column(String(5), nullable=True, comment="CST ICMS (Regime Normal) para emissão NF-e")
    referencia = Column(String(100), nullable=True, comment="Código de referência / referência do produto")
    unidade_medida = Column(String(20), nullable=False, default="UN")
    valor_custo = Column(Numeric(10, 2), nullable=True)
    valor_venda = Column(Numeric(10, 2), nullable=True)
    quantidade_atual = Column(Numeric(10, 2), nullable=False, default=0)
    quantidade_minima = Column(Numeric(10, 2), nullable=True)
    quantidade_maxima = Column(Numeric(10, 2), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    controla_estoque = Column(Boolean, nullable=False, default=True)

    # Campos migrados do Estoque (uso em dashboard, filtros, relatórios)
    categoria = Column(String(100), nullable=True)
    tipo_material = Column(String(50), nullable=True)
    tipo_material_id = Column(Integer, ForeignKey("tipo_material.id", ondelete="SET NULL"), nullable=True)
    categoria_id = Column(Integer, ForeignKey("material_categoria.id", ondelete="SET NULL"), nullable=True)
    fabricante = Column(String(255), nullable=True)
    fornecedor = Column(String(255), nullable=True)
    data_validade = Column(Date, nullable=True)
    data_fabricacao = Column(Date, nullable=True)

    # Imagem principal (compatível PDV/vitrine) e múltiplas mídias (imagens/vídeos)
    foto_peca = Column(String(512), nullable=True, comment="Caminho da imagem principal do produto")
    midias = Column(Text(), nullable=True, comment="JSON: lista de { tipo, url } para imagens e vídeos")

    cliente = relationship("Cliente", backref="produtos_cliente")
    categoria_rel = relationship("MaterialCategoria", back_populates="produtos_cliente", foreign_keys=[categoria_id])
    tipo_material_rel = relationship("TipoMaterial", back_populates="produtos_cliente", foreign_keys=[tipo_material_id])
    codigos_barras = relationship("CodigoBarrasCliente", back_populates="produto_cliente", cascade="all, delete-orphan")
    movimentacoes = relationship("MovimentacaoEstoque", back_populates="produto_cliente", cascade="all, delete-orphan")
    produtos_fornecedor = relationship("ProdutoFornecedor", back_populates="produto_cliente", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("cliente_id", "codigo", name="uq_produtos_cliente_cliente_codigo"),
    )

    def __repr__(self):
        return f"<ProdutoCliente(id={self.id}, codigo='{self.codigo}', cliente_id={self.cliente_id})>"
