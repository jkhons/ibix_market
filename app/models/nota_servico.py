# PDV Ibix - Modelos de Notas de Serviço (NFS-e)
import enum
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Column, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class StatusNotaServicoEnum(str, enum.Enum):
    """Enum para status da nota de serviço"""
    RASCUNHO = "rascunho"
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    AUTORIZADO = "autorizado"
    CANCELADO = "cancelado"
    REJEITADO = "rejeitado"


class OrigemDocumentoFiscalEnum(str, enum.Enum):
    """Origem do documento fiscal"""
    MANUAL = "manual"
    ORCAMENTO = "orcamento"
    VENDA_BALCAO = "venda_balcao"
    ORDEM_SERVICO = "ordem_servico"

class NotaServico(BaseModel):
    """Modelo para tabela notas_servico (capa da NFS-e)"""
    __tablename__ = "notas_servico"
    
    # Identificação da Nota
    numero = Column(String(20), nullable=False, comment="Número da NFS-e")
    codigo_verificacao = Column(String(20), nullable=True, comment="Código de verificação da NFS-e")
    
    # Datas
    data_emissao = Column(DateTime, nullable=False, comment="Data e hora de emissão da NFS-e")
    data_competencia = Column(Date, nullable=True, comment="Data de competência do serviço")
    
    # Relacionamentos
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, comment="Destinatário da nota = Subcliente (cliente da Empresa Fiscal)")
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="RESTRICT"), nullable=False, comment="Emissor = Empresa Fiscal (Cliente Administrador)")
    venda_id = Column(Integer, ForeignKey("vendas.id", ondelete="SET NULL"), nullable=True, comment="ID da venda relacionada (FK para vendas.id) - opcional")
    ordem_servico_id = Column(Integer, ForeignKey("ordem_servico.id", ondelete="SET NULL"), nullable=True, comment="ID da ordem de serviço (FK para ordem_servico.id) - NFS-e gerada ao concluir OS")
    emitido_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, comment="ID do usuário que emitiu a nota (FK para usuarios.id)")
    origem_documento = Column(Enum(OrigemDocumentoFiscalEnum), default=OrigemDocumentoFiscalEnum.MANUAL, nullable=True, comment="Origem do documento (manual, orcamento, venda_balcao, ordem_servico)")
    
    # Valores da Nota
    valor_total = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="Valor total da NFS-e")
    valor_servicos = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor dos serviços")
    valor_deducoes = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor das deduções")
    valor_desconto = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor de desconto")
    
    # Valores de Impostos
    valor_iss = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do ISS")
    aliquota_iss = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota do ISS (%)")
    base_calculo_iss = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Base de cálculo do ISS")
    valor_pis = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do PIS")
    valor_cofins = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do COFINS")
    valor_inss = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do INSS")
    valor_ir = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do IR (Imposto de Renda)")
    valor_csll = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do CSLL (Contribuição Social sobre Lucro Líquido)")
    
    # Dados Municipais
    codigo_servico_municipal = Column(String(20), nullable=True, comment="Código de serviço municipal (LC 116)")
    codigo_tributacao_municipio = Column(String(20), nullable=True, comment="Código de tributação no município")
    discriminacao_servicos = Column(Text, nullable=False, comment="Discriminação detalhada dos serviços prestados")
    local_prestacao = Column(String(255), nullable=True, comment="Local de prestação do serviço")
    municipio_prestacao = Column(String(100), nullable=True, comment="Município de prestação do serviço")
    uf_prestacao = Column(String(2), nullable=True, comment="UF de prestação do serviço")
    
    # Status
    status = Column(Enum(StatusNotaServicoEnum), default=StatusNotaServicoEnum.RASCUNHO, nullable=True, comment="Status da NFS-e")
    protocolo_autorizacao = Column(String(50), nullable=True, comment="Protocolo de autorização retornado pela API municipal")
    data_autorizacao = Column(DateTime, nullable=True, comment="Data e hora da autorização")
    mensagem_retorno = Column(Text, nullable=True, comment="Mensagem retornada pela API municipal")
    
    # Arquivos
    xml_path = Column(String(255), nullable=True, comment="Caminho do arquivo XML da NFS-e")
    pdf_path = Column(String(255), nullable=True, comment="Caminho do arquivo PDF da NFS-e")
    
    # Relacionamentos
    empresa = relationship("Empresa", back_populates="notas_servico")
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    venda = relationship("Venda", foreign_keys=[venda_id])
    ordem_servico = relationship("OrdemServico", back_populates="notas_servico", foreign_keys=[ordem_servico_id])
    emitido_por = relationship("Usuario", foreign_keys=[emitido_por_id])
    itens = relationship("NotaServicoItem", back_populates="nota_servico", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_notas_servico_numero', 'numero'),
        Index('idx_notas_servico_codigo_verificacao', 'codigo_verificacao'),
        Index('idx_notas_servico_cliente', 'cliente_id'),
        Index('idx_notas_servico_empresa', 'empresa_id'),
        Index('idx_notas_servico_venda', 'venda_id'),
        Index('idx_notas_servico_status', 'status'),
        Index('idx_notas_servico_data_emissao', 'data_emissao'),
        Index('idx_notas_servico_data_competencia', 'data_competencia'),
        Index('idx_notas_servico_ordem_servico', 'ordem_servico_id'),
        Index('idx_notas_servico_origem_documento', 'origem_documento'),
        {"comment": "Tabela para armazenar notas fiscais de serviço eletrônicas (NFS-e)"}
    )
    
    def __repr__(self):
        return f"<NotaServico(id={self.id}, numero='{self.numero}', status='{self.status}')>"

class NotaServicoItem(BaseModel):
    """Modelo para tabela notas_servico_itens (itens da NFS-e)"""
    __tablename__ = "notas_servico_itens"
    
    # Relacionamentos
    nota_servico_id = Column(Integer, ForeignKey("notas_servico.id", ondelete="CASCADE"), nullable=False, comment="ID da nota de serviço (FK para notas_servico.id)")
    
    # Identificação do Item
    item_numero = Column(Integer, nullable=False, comment="Número sequencial do item na NFS-e")
    discriminacao = Column(Text, nullable=False, comment="Discriminação do serviço")
    codigo_servico_municipal = Column(String(20), nullable=True, comment="Código de serviço municipal (LC 116)")
    codigo_cnae = Column(String(20), nullable=True, comment="Código CNAE do serviço")
    
    # Quantidades e Valores
    quantidade = Column(DECIMAL(10, 3), nullable=True, comment="Quantidade do serviço")
    valor_unitario = Column(DECIMAL(10, 4), nullable=True, comment="Valor unitário do serviço")
    valor_total = Column(DECIMAL(10, 2), nullable=False, comment="Valor total do item")
    
    # Tributação ISS
    aliquota_iss = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota do ISS (%)")
    valor_iss = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do ISS")
    base_calculo_iss = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Base de cálculo do ISS")
    
    # Relacionamentos
    nota_servico = relationship("NotaServico", back_populates="itens")
    
    # Índices
    __table_args__ = (
        Index('idx_notas_servico_itens_nota_servico', 'nota_servico_id'),
        Index('idx_notas_servico_itens_item_numero', 'nota_servico_id', 'item_numero'),
        Index('idx_notas_servico_itens_codigo_servico', 'codigo_servico_municipal'),
        {"comment": "Tabela para armazenar itens das notas fiscais de serviço eletrônicas"}
    )
    
    def __repr__(self):
        return f"<NotaServicoItem(id={self.id}, nota_servico_id={self.nota_servico_id}, item_numero={self.item_numero})>"

