# PDV Ibix - Modelo Venda
import enum

from sqlalchemy import DECIMAL, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class StatusVenda(str, enum.Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    FINALIZADA = "FINALIZADA"
    FINALIZADA_LEGADO = "finalizada"

class TipoPagamento(str, enum.Enum):
    DINHEIRO = "dinheiro"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"
    PIX = "pix"
    BOLETO = "boleto"
    TRANSFERENCIA = "transferencia"

class Venda(BaseModel):
    """Modelo para tabela de vendas"""
    __tablename__ = "vendas"

    # Dados da Venda
    numero_venda = Column(String(50), unique=True, nullable=False, comment="# Número único da venda")
    data_venda = Column(DateTime, nullable=False, comment="# Data da venda")
    status = Column(
        String(20),
        default=StatusVenda.PENDENTE.value if hasattr(StatusVenda.PENDENTE, 'value') else 'PENDENTE',
        nullable=False,
        comment="# Status da venda"
    )
    
    # Cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, comment="# ID do cliente")
    
    # Vendedor/Usuário
    vendedor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, comment="# ID do vendedor")
    
    # Valores
    subtotal = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="# Subtotal da venda")
    desconto = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="# Valor do desconto")
    acrescimo = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="# Valor do acréscimo")
    total = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="# Total da venda")
    
    # Pagamento
    tipo_pagamento = Column(
        String(20),
        nullable=True,
        comment="# Tipo de pagamento"
    )
    valor_pago = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="# Valor pago")
    troco = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="# Valor do troco")
    
    # Observações
    observacoes = Column(Text, nullable=True, comment="# Observações da venda")
    
    # Relacionamentos Fiscais (opcionais)
    nota_fiscal_id = Column(Integer, ForeignKey("notas_fiscais.id", ondelete="SET NULL"), nullable=True, comment="# ID da nota fiscal relacionada (FK para notas_fiscais.id)")
    nota_servico_id = Column(Integer, ForeignKey("notas_servico.id", ondelete="SET NULL"), nullable=True, comment="# ID da nota de serviço relacionada (FK para notas_servico.id)")
    cupom_fiscal_id = Column(Integer, ForeignKey("cupons_fiscais.id", ondelete="SET NULL"), nullable=True, comment="# ID do cupom fiscal relacionado (FK para cupons_fiscais.id)")
    ordem_servico_id = Column(Integer, ForeignKey("ordem_servico.id", ondelete="SET NULL"), nullable=True, comment="# ID da ordem de serviço que originou a venda (1:1)")
    orcamento_id = Column(Integer, ForeignKey("orcamentos.id", ondelete="SET NULL"), nullable=True, index=True, comment="# Orçamento que originou a venda (conversão)")
    abertura_caixa_id = Column(Integer, ForeignKey("aberturas_caixa.id", ondelete="SET NULL"), nullable=True, index=True, comment="# Abertura de caixa (turno) vinculada à venda")
    
    # Relacionamentos
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    abertura_caixa = relationship("AberturaCaixa", foreign_keys=[abertura_caixa_id])
    ordem_servico = relationship("OrdemServico", back_populates="vendas", foreign_keys=[ordem_servico_id])
    orcamento = relationship("Orcamento", foreign_keys=[orcamento_id])
    vendedor = relationship("Usuario", foreign_keys=[vendedor_id])
    itens = relationship("VendaItem", back_populates="venda", cascade="all, delete-orphan")
    pagamentos = relationship("VendaPagamento", back_populates="venda", cascade="all, delete-orphan")
    
    # Relacionamentos Fiscais
    nota_fiscal = relationship("NotaFiscal", foreign_keys=[nota_fiscal_id])
    nota_servico = relationship("NotaServico", foreign_keys=[nota_servico_id])
    cupom_fiscal = relationship("CupomFiscal", foreign_keys=[cupom_fiscal_id])
    
    def __repr__(self):
        return f"<Venda(id={self.id}, numero='{self.numero_venda}', total={self.total})>"

class VendaItem(BaseModel):
    """Modelo para itens de venda"""
    __tablename__ = "venda_itens"

    # Relacionamentos
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=False, comment="# ID da venda")
    produto_cliente_id = Column(Integer, ForeignKey("produtos_cliente.id", ondelete="SET NULL"), nullable=True, index=True, comment="# Produto do estabelecimento")

    # Quantidade e Valores
    quantidade = Column(DECIMAL(10, 2), nullable=False, comment="# Quantidade vendida")
    valor_unitario = Column(DECIMAL(10, 2), nullable=False, comment="# Valor unitário na venda")
    valor_total = Column(DECIMAL(10, 2), nullable=False, comment="# Valor total do item")
    desconto_item = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="# Desconto no item")
    
    # Observações do item
    observacoes = Column(Text, nullable=True, comment="# Observações do item")
    
    # Relacionamentos
    venda = relationship("Venda", back_populates="itens")
    produto_cliente = relationship("ProdutoCliente", foreign_keys=[produto_cliente_id])
    
    def __repr__(self):
        return f"<VendaItem(id={self.id}, quantidade={self.quantidade}, valor_total={self.valor_total})>"
