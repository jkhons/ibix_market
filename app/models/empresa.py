# PDV Ibix - Modelo Empresa (Dados Fiscais)
import enum
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Boolean, Column, Date, Enum, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class AmbienteEnum(str, enum.Enum):
    """Enum para ambiente de emissão"""
    HOMOLOGACAO = "homologacao"
    PRODUCAO = "producao"

class TipoEquipamentoEnum(str, enum.Enum):
    """Enum para tipo de equipamento SAT/MFe"""
    SAT = "SAT"
    MFE = "MFe"

class CRTEnum(int, enum.Enum):
    """Enum para Código de Regime Tributário"""
    SIMPLES_NACIONAL = 1
    SIMPLES_NACIONAL_EXCESSO = 2
    REGIME_NORMAL = 3

class Empresa(BaseModel):
    """Modelo para tabela empresa (dados fiscais do emissor). Pertence ao Cliente (Empresa Fiscal). Usado como emissor em notas."""
    __tablename__ = "empresa"
    
    # Dados Básicos da Empresa
    razao_social = Column(String(255), nullable=False, comment="Razão social da empresa")
    nome_fantasia = Column(String(255), nullable=True, comment="Nome fantasia da empresa")
    cnpj = Column(String(18), unique=True, nullable=False, comment="CNPJ da empresa (formato: 00.000.000/0000-00)")
    ie = Column(String(20), nullable=True, comment="Inscrição Estadual")
    im = Column(String(20), nullable=True, comment="Inscrição Municipal")
    cnae = Column(String(20), nullable=True, comment="CNAE Principal da empresa")
    crt = Column(Integer, nullable=True, comment="Código de Regime Tributário (1=Simples Nacional, 2=Simples Nacional - Excesso de sublimite de receita bruta, 3=Regime Normal)")
    
    # Endereço
    cep = Column(String(20), nullable=True, comment="CEP (formato 00000-000 ou variações)")
    endereco = Column(String(255), nullable=True, comment="Logradouro")
    numero = Column(String(20), nullable=True, comment="Número do endereço")
    complemento = Column(String(100), nullable=True, comment="Complemento do endereço")
    bairro = Column(String(100), nullable=True, comment="Bairro")
    cidade = Column(String(100), nullable=True, comment="Cidade")
    uf = Column(String(2), nullable=True, comment="UF (sigla de 2 letras)")
    telefone = Column(String(20), nullable=True, comment="Telefone de contato")
    email = Column(String(100), nullable=True, comment="E-mail de contato")
    
    # Certificado Digital A1
    certificado_a1_path = Column(String(255), nullable=True, comment="Caminho do arquivo certificado .pfx/.p12")
    senha_certificado = Column(String(100), nullable=True, comment="Senha do certificado digital (criptografada)")
    certificado_a1_blob = Column(LargeBinary, nullable=True, comment="Certificado armazenado no banco (opcional)")
    certificado_validade = Column(Date, nullable=True, comment="Data de validade do certificado")
    
    # Configurações SEFAZ
    ambiente = Column(Enum(AmbienteEnum, values_callable=lambda x: [e.value for e in x]), default=AmbienteEnum.HOMOLOGACAO, nullable=True, comment="Ambiente de emissão (homologação ou produção)")
    uf_emissao = Column(String(2), nullable=True, comment="UF de emissão das notas fiscais")
    
    # Código IBGE do município (NFS-e / módulo faturamento)
    municipio_ibge = Column(Integer, nullable=True, comment="Código IBGE do município do prestador (emissor)")

    # Campos para NFS-e (Nota Fiscal de Serviço)
    cnae_servicos = Column(String(20), nullable=True, comment="CNAE para prestação de serviços")
    codigo_servico_municipal = Column(String(20), nullable=True, comment="Código de serviço municipal (LC 116)")
    aliquota_iss = Column(DECIMAL(5, 2), nullable=True, comment="Alíquota padrão do ISS (%)")
    
    # Campos para SAT/MFe
    codigo_ativacao_sat = Column(String(100), nullable=True, comment="Código de ativação do equipamento SAT")
    numero_serie_sat = Column(String(100), nullable=True, comment="Número de série do equipamento SAT/MFe")
    tipo_equipamento_sat = Column(Enum(TipoEquipamentoEnum, values_callable=lambda x: [e.value for e in x]), nullable=True, comment="Tipo de equipamento (SAT ou MFe)")
    
    # Logo do emissor (certificados de calibração)
    logo_url = Column(String(512), nullable=True, comment="URL ou caminho do logo do emissor (ex: /static/img/logo_emissor.png)")

    # Provedor/Gateway fiscal (módulo faturamento)
    provedor_fiscal = Column(String(50), nullable=True, comment="Provedor fiscal (ex: nfs-e_nacional, focus_nfe, outro)")
    provedor_api_key_encrypted = Column(Text, nullable=True, comment="API key do provedor (criptografada)")
    provedor_api_secret_encrypted = Column(Text, nullable=True, comment="API secret do provedor (criptografada)")
    serie_padrao_nfe = Column(String(10), default="1", nullable=True, comment="Série padrão NF-e")
    serie_padrao_nfce = Column(String(10), default="1", nullable=True, comment="Série padrão NFC-e")

    # Configuração NFC-e (modelo 65)
    nfce_habilitado = Column(Boolean, default=False, nullable=True, comment="Habilitar emissão NFC-e")
    nfce_csc_id = Column(String(10), nullable=True, comment="ID do CSC - SEFAZ")
    nfce_csc_token = Column(String(255), nullable=True, comment="Token CSC (criptografado)")

    regime_tributario = Column(String(50), nullable=True, comment="Regime tributário (texto, ex: Simples Nacional)")
    aliquotas_uf = Column(Text, nullable=True, comment="JSON: alíquotas por UF")

    # Controle
    ativo = Column(Boolean, default=True, nullable=True, comment="Se a empresa está ativa no sistema")

    # Modo de recebimento (definido pelo SuperAdmin)
    modo_recebimento = Column(
        String(20), nullable=False, server_default="plataforma",
        comment="'direto' = CA recebe na própria conta; 'plataforma' = plataforma recebe e repassa"
    )
    gateway_plataforma = Column(
        String(30),
        nullable=False,
        server_default="mercadopago",
        comment="Gateway no modo plataforma: mercadopago, pagbank ou pagarme (definido pelo SuperAdmin)",
    )
    taxa_plataforma_percentual = Column(
        DECIMAL(5, 2), nullable=True,
        comment="Taxa percentual da plataforma sobre vendas (ex: 5.00 = 5%)"
    )
    taxa_plataforma_valor_fixo = Column(
        DECIMAL(10, 2), nullable=True,
        comment="Taxa fixa da plataforma por transação (ex: 2.50 = R$2,50)"
    )

    # Vínculo com Cliente (Empresa Fiscal)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True, comment="Cliente (Empresa Fiscal) a que a empresa pertence; emissor das notas")
    
    # Relacionamentos
    cliente = relationship("Cliente", backref="empresas_fiscais", foreign_keys=[cliente_id])
    notas_fiscais = relationship("NotaFiscal", back_populates="empresa", cascade="all, delete-orphan")
    notas_servico = relationship("NotaServico", back_populates="empresa", cascade="all, delete-orphan")
    cupons_fiscais = relationship("CupomFiscal", back_populates="empresa", cascade="all, delete-orphan")
    mdfes = relationship("MDFe", back_populates="empresa", cascade="all, delete-orphan")
    fiscal_eventos = relationship("FiscalEvento", back_populates="empresa", cascade="all, delete-orphan")

    # Índices
    __table_args__ = (
        Index('idx_empresa_cnpj', 'cnpj'),
        Index('idx_empresa_uf_emissao', 'uf_emissao'),
        Index('idx_empresa_ambiente', 'ambiente'),
        Index('idx_empresa_ativo', 'ativo'),
        {"comment": "Tabela para armazenar dados fiscais da empresa emissora de notas fiscais"}
    )
    
    def __repr__(self):
        return f"<Empresa(id={self.id}, razao_social='{self.razao_social}', cnpj='{self.cnpj}')>"

