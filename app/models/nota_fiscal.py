# PDV Ibix - Modelos de Notas Fiscais (NF-e / NFC-e)
import enum
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class TipoNotaEnum(str, enum.Enum):
    """Enum para tipo de nota fiscal"""
    NFE = "NFe"
    NFCE = "NFCe"

class StatusNotaEnum(str, enum.Enum):
    """Enum para status da nota fiscal"""
    RASCUNHO = "rascunho"
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    AUTORIZADO = "autorizado"
    CANCELADO = "cancelado"
    REJEITADO = "rejeitado"
    DENEGADO = "denegado"


class OrigemDocumentoFiscalEnum(str, enum.Enum):
    """Origem do documento fiscal"""
    MANUAL = "manual"
    ORCAMENTO = "orcamento"
    VENDA_BALCAO = "venda_balcao"
    ORDEM_SERVICO = "ordem_servico"
    VENDA_MARKETPLACE = "venda_marketplace"

class AmbienteEnum(str, enum.Enum):
    """Enum para ambiente de emissão"""
    HOMOLOGACAO = "homologacao"
    PRODUCAO = "producao"

class NotaFiscal(BaseModel):
    """Modelo para tabela notas_fiscais (capa da NF-e/NFC-e)"""
    __tablename__ = "notas_fiscais"
    
    # Identificação da Nota
    numero = Column(String(20), nullable=False, comment="Número sequencial da nota fiscal")
    serie = Column(String(10), default='1', nullable=True, comment="Série da nota fiscal")
    tipo = Column(Enum(TipoNotaEnum), nullable=False, comment="Tipo de nota (NFe=Nota Fiscal Eletrônica, NFCe=Cupom Fiscal Eletrônico)")
    modelo = Column(String(5), nullable=False, comment="Modelo da nota (55=NF-e, 65=NFC-e)")
    
    # Datas
    data_emissao = Column(DateTime, nullable=False, comment="Data e hora de emissão da nota fiscal")
    data_saida = Column(DateTime, nullable=True, comment="Data e hora de saída/entrada da mercadoria")
    
    # Relacionamentos
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, comment="Destinatário da nota = Subcliente (cliente da Empresa Fiscal)")
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="RESTRICT"), nullable=False, comment="Emissor = Empresa Fiscal (Cliente Administrador)")
    venda_id = Column(Integer, ForeignKey("vendas.id", ondelete="SET NULL"), nullable=True, comment="ID da venda relacionada (FK para vendas.id) - opcional")
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="SET NULL"), nullable=True, index=True, comment="ID do pedido quando NF originada de faturamento de pedido")
    pedido_marketplace_id = Column(Integer, ForeignKey("pedidos_marketplace.id", ondelete="SET NULL"), nullable=True, index=True, comment="ID do pedido da loja (marketplace) quando NF originada de venda na vitrine")
    emitido_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True, comment="ID do usuário que emitiu a nota (null quando criada por task Celery)")
    origem_documento = Column(Enum(OrigemDocumentoFiscalEnum), default=OrigemDocumentoFiscalEnum.MANUAL, nullable=True, comment="Origem do documento (manual, orcamento, venda_balcao, ordem_servico)")
    
    # Valores da Nota
    valor_total = Column(DECIMAL(10, 2), nullable=False, default=0.00, comment="Valor total da nota fiscal")
    valor_produtos = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor total dos produtos")
    valor_frete = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do frete")
    valor_seguro = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do seguro")
    valor_desconto = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor total de desconto")
    valor_outros = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor de outras despesas")
    
    # Valores de Impostos
    valor_icms = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor total do ICMS")
    valor_icms_desonerado = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do ICMS desonerado")
    valor_icms_st = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do ICMS Substituição Tributária")
    valor_ipi = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor total do IPI")
    valor_pis = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor total do PIS")
    valor_cofins = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor total do COFINS")
    
    # Dados SEFAZ
    chave_acesso = Column(String(44), unique=True, nullable=True, comment="Chave de acesso da NF-e (44 dígitos)")
    protocolo_autorizacao = Column(String(50), nullable=True, comment="Protocolo de autorização retornado pela SEFAZ")
    data_autorizacao = Column(DateTime, nullable=True, comment="Data e hora da autorização pela SEFAZ")
    ambiente = Column(Enum(AmbienteEnum, values_callable=lambda x: [e.value for e in x]), default=AmbienteEnum.HOMOLOGACAO, nullable=True, comment="Ambiente de emissão")
    status = Column(Enum(StatusNotaEnum, values_callable=lambda x: [e.value for e in x]), default=StatusNotaEnum.RASCUNHO, nullable=True, comment="Status da nota fiscal")
    codigo_status = Column(String(10), nullable=True, comment="Código do status retornado pela SEFAZ")
    mensagem_retorno = Column(Text, nullable=True, comment="Mensagem retornada pela SEFAZ")
    
    # Arquivos
    xml_path = Column(String(255), nullable=True, comment="Caminho do arquivo XML assinado")
    xml_retorno_path = Column(String(255), nullable=True, comment="Caminho do arquivo XML de retorno da SEFAZ")
    danfe_path = Column(String(255), nullable=True, comment="Caminho do arquivo DANFE em PDF")
    qr_code_url = Column(String(500), nullable=True, comment="URL do QR Code (para NFC-e)")
    qr_code_image_path = Column(String(255), nullable=True, comment="Caminho da imagem do QR Code")
    
    # Dados Adicionais
    natureza_operacao = Column(String(100), nullable=True, comment="Natureza da operação")
    forma_pagamento = Column(String(50), nullable=True, comment="Forma de pagamento (para NFC-e)")
    tipo_pagamento = Column(String(50), nullable=True, comment="Tipo de pagamento")
    observacoes = Column(Text, nullable=True, comment="Observações gerais")
    informacoes_complementares = Column(Text, nullable=True, comment="Informações complementares da nota fiscal")
    
    # Relacionamentos
    empresa = relationship("Empresa", back_populates="notas_fiscais")
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    venda = relationship("Venda", foreign_keys=[venda_id])
    pedido = relationship("Pedido", foreign_keys=[pedido_id])
    pedido_marketplace = relationship("PedidoMarketplace", foreign_keys=[pedido_marketplace_id])
    emitido_por = relationship("Usuario", foreign_keys=[emitido_por_id])
    itens = relationship("NotaFiscalItem", back_populates="nota", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_notas_fiscais_numero_serie', 'numero', 'serie'),
        Index('idx_notas_fiscais_chave_acesso', 'chave_acesso'),
        Index('idx_notas_fiscais_cliente', 'cliente_id'),
        Index('idx_notas_fiscais_empresa', 'empresa_id'),
        Index('idx_notas_fiscais_venda', 'venda_id'),
        Index('idx_notas_fiscais_status', 'status'),
        Index('idx_notas_fiscais_data_emissao', 'data_emissao'),
        Index('idx_notas_fiscais_ambiente', 'ambiente'),
        Index('idx_notas_fiscais_tipo', 'tipo'),
        Index('idx_notas_fiscais_origem_documento', 'origem_documento'),
        Index('idx_notas_fiscais_pedido_marketplace', 'pedido_marketplace_id'),
        {"comment": "Tabela para armazenar notas fiscais eletrônicas (NF-e e NFC-e)"}
    )
    
    def __repr__(self):
        return f"<NotaFiscal(id={self.id}, numero='{self.numero}', tipo='{self.tipo}', status='{self.status}')>"

class NotaFiscalItem(BaseModel):
    """Modelo para tabela notas_fiscais_itens (itens da NF-e/NFC-e)"""
    __tablename__ = "notas_fiscais_itens"
    
    # Relacionamentos
    nota_id = Column(Integer, ForeignKey("notas_fiscais.id", ondelete="CASCADE"), nullable=False, comment="ID da nota fiscal (FK para notas_fiscais.id)")
    produto_cliente_id = Column(Integer, ForeignKey("produtos_cliente.id", ondelete="SET NULL"), nullable=True, comment="ID do produto (produtos_cliente)")

    # Identificação do Item
    item_numero = Column(Integer, nullable=False, comment="Número sequencial do item na nota fiscal")
    descricao = Column(String(255), nullable=False, comment="Descrição do produto/serviço")
    codigo_produto = Column(String(50), nullable=True, comment="Código interno do produto")
    ncm = Column(String(10), nullable=True, comment="Nomenclatura Comum do Mercosul")
    cest = Column(String(10), nullable=True, comment="Código Especificador de Substituição Tributária")
    cfop = Column(String(10), nullable=True, comment="CFOP da operação")
    unidade = Column(String(10), nullable=False, comment="Unidade de medida (UN, KG, etc.)")
    extipi = Column(String(5), nullable=True, comment="EX TIPI (código específico da TIPI)")
    
    # Quantidades e Valores
    quantidade = Column(DECIMAL(10, 3), nullable=False, comment="Quantidade do item")
    valor_unitario = Column(DECIMAL(10, 4), nullable=False, comment="Valor unitário do item")
    valor_total = Column(DECIMAL(10, 2), nullable=False, comment="Valor total do item")
    valor_desconto = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor de desconto do item")
    
    # Origem e Tributação ICMS
    origem = Column(Integer, nullable=True, comment="Origem da mercadoria (0-8)")
    cst_icms = Column(String(5), nullable=True, comment="CST ICMS (regime normal)")
    csosn = Column(String(5), nullable=True, comment="CSOSN (Simples Nacional)")
    aliquota_icms = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota do ICMS (%)")
    valor_icms = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do ICMS")
    valor_base_icms = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Base de cálculo do ICMS")
    
    # ICMS ST (Substituição Tributária)
    modalidade_bc_icms_st = Column(Integer, nullable=True, comment="Modalidade de cálculo da BC do ICMS ST")
    aliquota_icms_st = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota do ICMS ST (%)")
    valor_base_icms_st = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Base de cálculo do ICMS ST")
    valor_icms_st = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do ICMS ST")
    
    # IPI
    ipi_cst = Column(String(5), nullable=True, comment="CST IPI")
    ipi_codigo_enquadramento = Column(String(10), nullable=True, comment="Código de enquadramento IPI")
    ipi_aliquota = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota do IPI (%)")
    valor_ipi = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do IPI")
    valor_base_ipi = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Base de cálculo do IPI")
    
    # PIS
    pis_cst = Column(String(5), nullable=True, comment="CST PIS")
    pis_aliquota = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota do PIS (%)")
    pis_valor = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do PIS")
    pis_base_calculo = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Base de cálculo do PIS")
    
    # COFINS
    cofins_cst = Column(String(5), nullable=True, comment="CST COFINS")
    cofins_aliquota = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota do COFINS (%)")
    cofins_valor = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Valor do COFINS")
    cofins_base_calculo = Column(DECIMAL(10, 2), default=0.00, nullable=True, comment="Base de cálculo do COFINS")
    
    # Dados Adicionais
    informacoes_adicionais = Column(Text, nullable=True, comment="Informações complementares do item")

    # Auditoria motor tributário
    regra_fiscal_icms_id = Column(
        Integer,
        ForeignKey("regras_fiscais_icms.id", ondelete="SET NULL"),
        nullable=True,
        comment="Regra fiscal aplicada pelo motor tributário",
    )
    motor_contexto_json = Column(JSONB, nullable=True, comment="Contexto usado pelo motor tributário")
    motor_resultado_json = Column(JSONB, nullable=True, comment="Resultado retornado pelo motor tributário")
    motor_versao = Column(String(20), nullable=True, comment="Versão do motor tributário aplicada")

    # Relacionamentos
    nota = relationship("NotaFiscal", back_populates="itens")
    produto_cliente = relationship("ProdutoCliente", foreign_keys=[produto_cliente_id])
    regra_fiscal_icms = relationship("RegraFiscalIcms", foreign_keys=[regra_fiscal_icms_id])

    # Índices
    __table_args__ = (
        Index('idx_notas_fiscais_itens_nota', 'nota_id'),
        Index('idx_notas_fiscais_itens_produto_cliente', 'produto_cliente_id'),
        Index('idx_notas_fiscais_itens_item_numero', 'nota_id', 'item_numero'),
        Index('idx_notas_fiscais_itens_ncm', 'ncm'),
        Index('idx_notas_fiscais_itens_cfop', 'cfop'),
        {"comment": "Tabela para armazenar itens das notas fiscais eletrônicas"}
    )
    
    def __repr__(self):
        return f"<NotaFiscalItem(id={self.id}, nota_id={self.nota_id}, item_numero={self.item_numero}, descricao='{self.descricao}')>"

