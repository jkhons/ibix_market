# PDV Ibix - Modelos de MDF-e (Manifesto Eletrônico de Documentos Fiscais)
import enum
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class StatusMDFeEnum(str, enum.Enum):
    """Enum para status do MDF-e"""
    PENDENTE = "pendente"
    AUTORIZADO = "autorizado"
    CANCELADO = "cancelado"
    ENCERRADO = "encerrado"
    REJEITADO = "rejeitado"

class TipoDocumentoEnum(str, enum.Enum):
    """Enum para tipo de documento vinculado"""
    NFE = "NFe"
    CTE = "CTe"

class MDFe(BaseModel):
    """Modelo para tabela mdfe (capa do MDF-e)"""
    __tablename__ = "mdfe"
    
    # Identificação do MDF-e
    numero = Column(String(20), nullable=False, comment="Número do MDF-e")
    serie = Column(String(10), default='1', nullable=True, comment="Série do MDF-e")
    codigo_mdfe = Column(String(50), nullable=True, comment="Código numérico do MDF-e")
    chave_acesso = Column(String(44), unique=True, nullable=True, comment="Chave de acesso do MDF-e (44 dígitos)")
    
    # Data
    data_emissao = Column(DateTime, nullable=False, comment="Data e hora de emissão do MDF-e")
    
    # Relacionamentos
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="RESTRICT"), nullable=False, comment="ID da empresa emitente (FK para empresa.id)")
    
    # Dados do Transporte
    tipo_emitente = Column(Integer, nullable=True, comment="Tipo de emitente (1=Transportador, 2=Carga própria)")
    uf_inicio = Column(String(2), nullable=False, comment="UF de início do transporte")
    uf_fim = Column(String(2), nullable=False, comment="UF de fim do transporte")
    
    # Informações Gerais
    qtd_cte = Column(Integer, default=0, nullable=True, comment="Quantidade de CT-e vinculados")
    valor_total_carga = Column(DECIMAL(10, 2), nullable=True, comment="Valor total da carga")
    peso_bruto_total = Column(DECIMAL(10, 3), nullable=True, comment="Peso bruto total (em kg)")
    
    # Status
    status = Column(Enum(StatusMDFeEnum), default=StatusMDFeEnum.PENDENTE, nullable=True, comment="Status do MDF-e")
    protocolo_autorizacao = Column(String(50), nullable=True, comment="Protocolo de autorização retornado pela SEFAZ")
    data_autorizacao = Column(DateTime, nullable=True, comment="Data e hora da autorização")
    mensagem_retorno = Column(Text, nullable=True, comment="Mensagem retornada pela SEFAZ")
    
    # Arquivos
    xml_path = Column(String(255), nullable=True, comment="Caminho do arquivo XML assinado")
    xml_retorno_path = Column(String(255), nullable=True, comment="Caminho do arquivo XML de retorno da SEFAZ")
    
    # Relacionamentos
    empresa = relationship("Empresa", back_populates="mdfes")
    documentos = relationship("MDFeDocumento", back_populates="mdfe", cascade="all, delete-orphan")
    veiculos = relationship("MDFeVeiculo", back_populates="mdfe", cascade="all, delete-orphan")
    condutores = relationship("MDFeCondutor", back_populates="mdfe", cascade="all, delete-orphan")
    percursos = relationship("MDFePercurso", back_populates="mdfe", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_mdfe_numero_serie', 'numero', 'serie'),
        Index('idx_mdfe_chave_acesso', 'chave_acesso'),
        Index('idx_mdfe_empresa', 'empresa_id'),
        Index('idx_mdfe_status', 'status'),
        Index('idx_mdfe_data_emissao', 'data_emissao'),
        Index('idx_mdfe_uf_inicio_fim', 'uf_inicio', 'uf_fim'),
        {"comment": "Tabela para armazenar Manifestos Eletrônicos de Documentos Fiscais (MDF-e)"}
    )
    
    def __repr__(self):
        return f"<MDFe(id={self.id}, numero='{self.numero}', status='{self.status}')>"

class MDFeDocumento(BaseModel):
    """Modelo para tabela mdfe_documentos (NF-es/CT-es vinculados)"""
    __tablename__ = "mdfe_documentos"
    
    # Relacionamentos
    mdfe_id = Column(Integer, ForeignKey("mdfe.id", ondelete="CASCADE"), nullable=False, comment="ID do MDF-e (FK para mdfe.id)")
    
    # Dados do Documento
    tipo_documento = Column(Enum(TipoDocumentoEnum), nullable=False, comment="Tipo de documento vinculado (NFe ou CTe)")
    chave_acesso = Column(String(44), nullable=False, comment="Chave de acesso do documento (NF-e ou CT-e)")
    valor = Column(DECIMAL(10, 2), nullable=True, comment="Valor do documento")
    peso = Column(DECIMAL(10, 3), nullable=True, comment="Peso do documento (em kg)")
    
    # Relacionamentos
    mdfe = relationship("MDFe", back_populates="documentos")
    
    # Índices
    __table_args__ = (
        Index('idx_mdfe_documentos_mdfe', 'mdfe_id'),
        Index('idx_mdfe_documentos_chave_acesso', 'chave_acesso'),
        Index('idx_mdfe_documentos_tipo_documento', 'tipo_documento'),
        {"comment": "Tabela para armazenar documentos (NF-es e CT-es) vinculados ao MDF-e"}
    )
    
    def __repr__(self):
        return f"<MDFeDocumento(id={self.id}, mdfe_id={self.mdfe_id}, tipo_documento='{self.tipo_documento}', chave_acesso='{self.chave_acesso}')>"

class MDFeVeiculo(BaseModel):
    """Modelo para tabela mdfe_veiculos (veículos do MDF-e)"""
    __tablename__ = "mdfe_veiculos"
    
    # Relacionamentos
    mdfe_id = Column(Integer, ForeignKey("mdfe.id", ondelete="CASCADE"), nullable=False, comment="ID do MDF-e (FK para mdfe.id)")
    
    # Dados do Veículo
    placa = Column(String(7), nullable=False, comment="Placa do veículo")
    renavam = Column(String(20), nullable=True, comment="RENAVAM do veículo")
    tara = Column(DECIMAL(10, 3), nullable=True, comment="Tara do veículo (em kg)")
    capacidade_kg = Column(DECIMAL(10, 3), nullable=True, comment="Capacidade de carga em kg")
    capacidade_m3 = Column(DECIMAL(10, 3), nullable=True, comment="Capacidade de carga em m³")
    tipo_rodado = Column(String(50), nullable=True, comment="Tipo de rodado")
    tipo_carroceria = Column(String(50), nullable=True, comment="Tipo de carroceria")
    uf = Column(String(2), nullable=True, comment="UF de licenciamento do veículo")
    
    # Relacionamentos
    mdfe = relationship("MDFe", back_populates="veiculos")
    
    # Índices
    __table_args__ = (
        Index('idx_mdfe_veiculos_mdfe', 'mdfe_id'),
        Index('idx_mdfe_veiculos_placa', 'placa'),
        {"comment": "Tabela para armazenar veículos do MDF-e"}
    )
    
    def __repr__(self):
        return f"<MDFeVeiculo(id={self.id}, mdfe_id={self.mdfe_id}, placa='{self.placa}')>"

class MDFeCondutor(BaseModel):
    """Modelo para tabela mdfe_condutores (condutores do MDF-e)"""
    __tablename__ = "mdfe_condutores"
    
    # Relacionamentos
    mdfe_id = Column(Integer, ForeignKey("mdfe.id", ondelete="CASCADE"), nullable=False, comment="ID do MDF-e (FK para mdfe.id)")
    
    # Dados do Condutor
    nome = Column(String(255), nullable=False, comment="Nome do condutor")
    cpf = Column(String(11), nullable=True, comment="CPF do condutor")
    
    # Relacionamentos
    mdfe = relationship("MDFe", back_populates="condutores")
    
    # Índices
    __table_args__ = (
        Index('idx_mdfe_condutores_mdfe', 'mdfe_id'),
        Index('idx_mdfe_condutores_cpf', 'cpf'),
        {"comment": "Tabela para armazenar condutores do MDF-e"}
    )
    
    def __repr__(self):
        return f"<MDFeCondutor(id={self.id}, mdfe_id={self.mdfe_id}, nome='{self.nome}')>"

class MDFePercurso(BaseModel):
    """Modelo para tabela mdfe_percursos (percursos do MDF-e)"""
    __tablename__ = "mdfe_percursos"
    
    # Relacionamentos
    mdfe_id = Column(Integer, ForeignKey("mdfe.id", ondelete="CASCADE"), nullable=False, comment="ID do MDF-e (FK para mdfe.id)")
    
    # Dados do Percurso
    uf = Column(String(2), nullable=False, comment="UF do percurso")
    
    # Relacionamentos
    mdfe = relationship("MDFe", back_populates="percursos")
    
    # Índices
    __table_args__ = (
        Index('idx_mdfe_percursos_mdfe', 'mdfe_id'),
        Index('idx_mdfe_percursos_uf', 'uf'),
        {"comment": "Tabela para armazenar percursos (UFs) do MDF-e"}
    )
    
    def __repr__(self):
        return f"<MDFePercurso(id={self.id}, mdfe_id={self.mdfe_id}, uf='{self.uf}')>"

