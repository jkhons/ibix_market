# PDV Ibix - Modelos de Cupons Fiscais (CF-e - SAT/MFe)
import enum
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class TipoEquipamentoEnum(str, enum.Enum):
    """Enum para tipo de equipamento SAT/MFe"""
    SAT = "SAT"
    MFE = "MFe"

class StatusCupomEnum(str, enum.Enum):
    """Enum para status do cupom fiscal"""
    PENDENTE = "pendente"
    AUTORIZADO = "autorizado"
    CANCELADO = "cancelado"
    REJEITADO = "rejeitado"

class CupomFiscal(BaseModel):
    """Modelo para tabela cupons_fiscais (capa do CF-e)"""
    __tablename__ = "cupons_fiscais"
    
    # Identificação do Cupom
    numero_cfe = Column(String(20), nullable=False, comment="Número do CF-e")
    serie = Column(String(10), nullable=True, comment="Série do CF-e")
    chave_cfe = Column(String(50), nullable=True, comment="Chave de acesso do CF-e")
    
    # Data
    data_emissao = Column(DateTime, nullable=False, comment="Data e hora de emissão do CF-e")
    
    # Relacionamentos
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, comment="ID do cliente (FK para clientes.id) - pode ser NULL para consumidor final")
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="RESTRICT"), nullable=False, comment="ID da empresa emissora (FK para empresa.id)")
    venda_id = Column(Integer, ForeignKey("vendas.id", ondelete="SET NULL"), nullable=True, comment="ID da venda relacionada (FK para vendas.id) - opcional")
    emitido_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, comment="ID do usuário que emitiu o cupom (FK para usuarios.id)")
    
    # Valores do Cupom
    valor_total = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="Valor total do CF-e")
    valor_produtos = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor total dos produtos")
    valor_desconto = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor de desconto")
    valor_acrescimo = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor de acréscimo")
    valor_troco = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do troco")
    
    # Equipamento SAT/MFe
    tipo_equipamento = Column(Enum(TipoEquipamentoEnum), nullable=False, comment="Tipo de equipamento (SAT ou MFe)")
    numero_serie_sat = Column(String(100), nullable=True, comment="Número de série do equipamento SAT/MFe")
    codigo_ativacao = Column(String(100), nullable=True, comment="Código de ativação do equipamento")
    numero_caixa = Column(Integer, nullable=True, comment="Número do ECF (caixa)")
    
    # Status
    status = Column(Enum(StatusCupomEnum), default=StatusCupomEnum.PENDENTE, nullable=True, comment="Status do CF-e")
    protocolo_autorizacao = Column(String(50), nullable=True, comment="Protocolo de autorização retornado pelo equipamento")
    data_autorizacao = Column(DateTime, nullable=True, comment="Data e hora da autorização")
    mensagem_retorno = Column(Text, nullable=True, comment="Mensagem retornada pelo equipamento")
    
    # Arquivos
    xml_sat_path = Column(String(255), nullable=True, comment="Caminho do arquivo XML do SAT/MFe")
    extrato_path = Column(String(255), nullable=True, comment="Caminho do arquivo extrato do CF-e")
    qr_code_url = Column(String(500), nullable=True, comment="URL do QR Code do CF-e")
    qr_code_image_path = Column(String(255), nullable=True, comment="Caminho da imagem do QR Code")
    
    # Forma de Pagamento
    forma_pagamento = Column(String(50), nullable=True, comment="Forma de pagamento")
    tipo_pagamento = Column(String(50), nullable=True, comment="Tipo de pagamento")
    
    # Relacionamentos
    empresa = relationship("Empresa", back_populates="cupons_fiscais")
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    venda = relationship("Venda", foreign_keys=[venda_id])
    emitido_por = relationship("Usuario", foreign_keys=[emitido_por_id])
    itens = relationship("CupomFiscalItem", back_populates="cupom_fiscal", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_cupons_fiscais_numero_cfe', 'numero_cfe'),
        Index('idx_cupons_fiscais_chave_cfe', 'chave_cfe'),
        Index('idx_cupons_fiscais_cliente', 'cliente_id'),
        Index('idx_cupons_fiscais_empresa', 'empresa_id'),
        Index('idx_cupons_fiscais_venda', 'venda_id'),
        Index('idx_cupons_fiscais_status', 'status'),
        Index('idx_cupons_fiscais_data_emissao', 'data_emissao'),
        Index('idx_cupons_fiscais_tipo_equipamento', 'tipo_equipamento'),
        Index('idx_cupons_fiscais_numero_serie_sat', 'numero_serie_sat'),
        {"comment": "Tabela para armazenar cupons fiscais eletrônicos (CF-e) emitidos por SAT ou MFe"}
    )
    
    def __repr__(self):
        return f"<CupomFiscal(id={self.id}, numero_cfe='{self.numero_cfe}', tipo_equipamento='{self.tipo_equipamento}', status='{self.status}')>"

class CupomFiscalItem(BaseModel):
    """Modelo para tabela cupons_fiscais_itens (itens do CF-e)"""
    __tablename__ = "cupons_fiscais_itens"
    
    # Relacionamentos
    cupom_fiscal_id = Column(Integer, ForeignKey("cupons_fiscais.id", ondelete="CASCADE"), nullable=False, comment="ID do cupom fiscal (FK para cupons_fiscais.id)")
    produto_cliente_id = Column(Integer, ForeignKey("produtos_cliente.id", ondelete="SET NULL"), nullable=True, comment="ID do produto (produtos_cliente)")

    # Identificação do Item
    item_numero = Column(Integer, nullable=False, comment="Número sequencial do item no CF-e")
    codigo_produto = Column(String(50), nullable=True, comment="Código interno do produto")
    descricao = Column(String(255), nullable=False, comment="Descrição do produto")
    ncm = Column(String(10), nullable=True, comment="Nomenclatura Comum do Mercosul")
    cfop = Column(String(10), nullable=True, comment="CFOP da operação")
    unidade = Column(String(10), nullable=True, comment="Unidade de medida")
    
    # Quantidades e Valores
    quantidade = Column(DECIMAL(10, 3), nullable=False, comment="Quantidade do item")
    valor_unitario = Column(DECIMAL(10, 4), nullable=False, comment="Valor unitário do item")
    valor_total = Column(DECIMAL(10, 2), nullable=False, comment="Valor total do item")
    valor_desconto = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor de desconto do item")
    
    # Tributação ICMS
    cst_icms = Column(String(5), nullable=True, comment="CST ICMS")
    aliquota_icms = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota do ICMS (%)")
    valor_icms = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do ICMS")
    
    # Relacionamentos
    cupom_fiscal = relationship("CupomFiscal", back_populates="itens")
    produto_cliente = relationship("ProdutoCliente", foreign_keys=[produto_cliente_id])

    # Índices
    __table_args__ = (
        Index('idx_cupons_fiscais_itens_cupom_fiscal', 'cupom_fiscal_id'),
        Index('idx_cupons_fiscais_itens_produto_cliente', 'produto_cliente_id'),
        Index('idx_cupons_fiscais_itens_item_numero', 'cupom_fiscal_id', 'item_numero'),
        {"comment": "Tabela para armazenar itens dos cupons fiscais eletrônicos"}
    )
    
    def __repr__(self):
        return f"<CupomFiscalItem(id={self.id}, cupom_fiscal_id={self.cupom_fiscal_id}, item_numero={self.item_numero}, descricao='{self.descricao}')>"

