# PDV Ibix - Modelo Material Categoria
from sqlalchemy import DECIMAL, Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class MaterialCategoria(BaseModel):
    """Modelo para tabela de categorias de materiais"""
    __tablename__ = "material_categoria"
    
    # Dados da Categoria
    nome = Column(String(100), nullable=False, unique=True, comment="# Nome da categoria")
    descricao = Column(Text, nullable=True, comment="# Descrição da categoria")
    codigo = Column(String(20), nullable=False, unique=True, comment="# Código único da categoria")
    icone = Column(String(80), nullable=True, comment="# Ícone da categoria para vitrine")
    
    # Configurações
    ativo = Column(Boolean, default=True, nullable=False, comment="# Se a categoria está ativa")
    controla_estoque = Column(Boolean, default=True, nullable=False, comment="# Se deve controlar estoque para esta categoria")
    permite_negativo = Column(Boolean, default=False, nullable=False, comment="# Se permite estoque negativo")
    
    # Configurações de Validade
    tem_validade = Column(Boolean, default=False, nullable=False, comment="# Se produtos desta categoria têm validade")
    dias_alerta_vencimento = Column(Integer, default=30, nullable=False, comment="# Dias de antecedência para alerta de vencimento")
    
    # Configurações de Movimentação
    requer_aprovacao = Column(Boolean, default=False, nullable=False, comment="# Se movimentações requerem aprovação")
    limite_movimentacao = Column(DECIMAL(10, 2), nullable=True, comment="# Limite máximo de movimentação por vez")
    
    # Configurações de Relatório
    incluir_relatorios = Column(Boolean, default=True, nullable=False, comment="# Se incluir em relatórios")
    cor_relatorio = Column(String(7), default='#007bff', nullable=False, comment="# Cor para relatórios (hex)")
    
    # Relacionamentos (apenas ProdutoCliente; Estoque removido na migração)
    produtos_cliente = relationship("ProdutoCliente", back_populates="categoria_rel")
    
    def __repr__(self):
        return f"<MaterialCategoria(id={self.id}, codigo='{self.codigo}', nome='{self.nome}')>"
