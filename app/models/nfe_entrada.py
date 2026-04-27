# PDV Ibix - Modelos Entrada de Notas NFe (importação XML compras)
"""nfe_documentos = cabeçalho da NF-e importada; nfe_itens = itens do XML + conciliação.
Não confundir com notas_fiscais/notas_fiscais_itens (emissão)."""
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class NfeDocumento(BaseModel):
    """Cabeçalho da NF-e importada (entrada de compras). Escopo por cliente_id."""
    __tablename__ = "nfe_documentos"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Estabelecimento que importa/recebe a nota",
    )
    chave_acesso_44 = Column(String(44), nullable=False, unique=True)
    modelo = Column(String(5), nullable=True)
    serie = Column(String(10), nullable=True)
    numero = Column(String(20), nullable=True)
    emissao_em = Column(DateTime(timezone=True), nullable=True)
    entrada_saida = Column(String(20), nullable=False)  # ENTRADA, SAIDA
    ambiente = Column(String(20), nullable=True)
    emitente_fornecedor_id = Column(
        Integer,
        ForeignKey("fornecedores_cliente.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    emitente_razao_social = Column(String(255), nullable=True, comment="Razão social do emitente (XML xNome), para exibir na listagem")
    total_produtos = Column(Numeric(18, 2), nullable=True)
    total_nota = Column(Numeric(18, 2), nullable=True)
    xml_original = Column(Text(), nullable=True)
    xml_sha256 = Column(String(64), nullable=True)
    status = Column(String(30), nullable=False, default="IMPORTADO")

    cliente = relationship("Cliente", backref="nfe_documentos_entrada")
    emitente_fornecedor = relationship("FornecedorCliente", foreign_keys=[emitente_fornecedor_id])
    itens = relationship("NfeItem", back_populates="nfe_documento", cascade="all, delete-orphan")


class NfeItem(BaseModel):
    """Item do XML da NF-e importada + conciliação (produto_cliente_id, conciliar_status)."""
    __tablename__ = "nfe_itens"

    nfe_id = Column(
        Integer,
        ForeignKey("nfe_documentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    numero_item = Column(Integer, nullable=True)
    cprod_xml = Column(String(60), nullable=True)
    xprod_xml = Column(Text(), nullable=True)
    ean_xml = Column(String(14), nullable=True)
    ncm_xml = Column(String(10), nullable=True)
    cfop_xml = Column(String(10), nullable=True)
    ucom_xml = Column(String(10), nullable=True)
    qcom_xml = Column(Numeric(18, 6), nullable=True)
    vuncom_xml = Column(Numeric(18, 6), nullable=True)
    vprod_xml = Column(Numeric(18, 2), nullable=True)
    vdesc_xml = Column(Numeric(18, 2), nullable=True)
    vfrete_xml = Column(Numeric(18, 2), nullable=True)
    vseg_xml = Column(Numeric(18, 2), nullable=True)
    voutro_xml = Column(Numeric(18, 2), nullable=True)
    vipi_xml = Column(Numeric(18, 2), nullable=True)
    vicmsst_xml = Column(Numeric(18, 2), nullable=True)
    cest_xml = Column(String(10), nullable=True, comment="CEST do item (XML)")
    extipi_xml = Column(String(5), nullable=True, comment="EX TIPI do item (XML)")
    infadprod_xml = Column(Text(), nullable=True, comment="Informações adicionais do produto (XML infAdProd)")
    orig_xml = Column(Integer, nullable=True, comment="Origem da mercadoria 0-8 (XML det/imposto/ICMS/orig)")
    produto_cliente_id = Column(
        Integer,
        ForeignKey("produtos_cliente.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fornecedor_id = Column(
        Integer,
        ForeignKey("fornecedores_cliente.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conciliar_status = Column(String(20), nullable=False, default="PENDENTE")  # PENDENTE, VINCULADO, IGNORADO

    nfe_documento = relationship("NfeDocumento", back_populates="itens")
    produto_cliente = relationship("ProdutoCliente", foreign_keys=[produto_cliente_id])
    fornecedor = relationship("FornecedorCliente", foreign_keys=[fornecedor_id])
