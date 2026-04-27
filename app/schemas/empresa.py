# PDV Ibix - Schemas de Empresa (Dados Fiscais)
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


class AmbienteEnum(str, Enum):
    """Enum para ambiente de emissão"""
    HOMOLOGACAO = "homologacao"
    PRODUCAO = "producao"

class TipoEquipamentoEnum(str, Enum):
    """Enum para tipo de equipamento SAT/MFe"""
    SAT = "SAT"
    MFE = "MFe"

class CRTEnum(int, Enum):
    """Enum para Código de Regime Tributário"""
    SIMPLES_NACIONAL = 1
    SIMPLES_NACIONAL_EXCESSO = 2
    REGIME_NORMAL = 3

class EmpresaBase(BaseModel):
    """Schema base para empresa"""
    razao_social: str = Field(..., min_length=1, max_length=255, description="Razão social da empresa")
    nome_fantasia: Optional[str] = Field(None, max_length=255, description="Nome fantasia da empresa")
    cnpj: str = Field(..., min_length=14, max_length=18, description="CNPJ da empresa (formato: 00.000.000/0000-00)")
    ie: Optional[str] = Field(None, max_length=20, description="Inscrição Estadual")
    im: Optional[str] = Field(None, max_length=20, description="Inscrição Municipal")
    cnae: Optional[str] = Field(None, max_length=20, description="CNAE Principal da empresa")
    crt: Optional[CRTEnum] = Field(None, description="Código de Regime Tributário")
    
    # Endereço
    cep: Optional[str] = Field(None, max_length=9, description="CEP (formato: 00000-000)")
    endereco: Optional[str] = Field(None, max_length=255, description="Logradouro")
    numero: Optional[str] = Field(None, max_length=20, description="Número do endereço")
    complemento: Optional[str] = Field(None, max_length=100, description="Complemento do endereço")
    bairro: Optional[str] = Field(None, max_length=100, description="Bairro")
    cidade: Optional[str] = Field(None, max_length=100, description="Cidade")
    uf: Optional[str] = Field(None, max_length=2, description="UF (sigla de 2 letras)")
    telefone: Optional[str] = Field(None, max_length=20, description="Telefone de contato")
    email: Optional[str] = Field(None, max_length=100, description="E-mail de contato")
    
    # Certificado Digital A1
    certificado_a1_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo certificado .pfx/.p12")
    certificado_a1_blob: Optional[str] = Field(None, description="Certificado em base64 (opcional, enviado via upload)")
    senha_certificado: Optional[str] = Field(None, max_length=100, description="Senha do certificado digital (criptografada)")
    certificado_validade: Optional[date] = Field(None, description="Data de validade do certificado")
    
    # Provedor fiscal (NF-e: local = SEFAZ direto, vazio = stub/gateway)
    provedor_fiscal: Optional[str] = Field(None, max_length=50, description="Provedor fiscal: 'local' ou vazio para stub/gateway")

    # Configurações SEFAZ
    ambiente: Optional[AmbienteEnum] = Field(default=AmbienteEnum.HOMOLOGACAO, description="Ambiente de emissão (homologação ou produção)")
    uf_emissao: Optional[str] = Field(None, max_length=2, description="UF de emissão das notas fiscais")
    municipio_ibge: Optional[int] = Field(None, description="Código IBGE do município (obrigatório para emissão NF-e)")
    
    # Campos para NFS-e
    cnae_servicos: Optional[str] = Field(None, max_length=20, description="CNAE para prestação de serviços")
    codigo_servico_municipal: Optional[str] = Field(None, max_length=20, description="Código de serviço municipal (LC 116)")
    aliquota_iss: Optional[Decimal] = Field(None, description="Alíquota padrão do ISS (%)")
    
    # Campos para SAT/MFe
    codigo_ativacao_sat: Optional[str] = Field(None, max_length=100, description="Código de ativação do equipamento SAT")
    numero_serie_sat: Optional[str] = Field(None, max_length=100, description="Número de série do equipamento SAT/MFe")
    tipo_equipamento_sat: Optional[TipoEquipamentoEnum] = Field(None, description="Tipo de equipamento (SAT ou MFe)")
    
    # Logo do emissor (certificados)
    logo_url: Optional[str] = Field(None, max_length=512, description="URL ou caminho do logo do emissor (certificados de calibração)")

    # Configuração NFC-e (modelo 65)
    nfce_habilitado: Optional[bool] = Field(False, description="Habilitar emissão NFC-e")
    nfce_csc_id: Optional[str] = Field(None, max_length=10, description="ID do CSC - SEFAZ")
    nfce_csc_token: Optional[str] = Field(None, max_length=255, description="Token CSC (obrigatório se nfce_habilitado)")

    # Controle
    ativo: Optional[bool] = Field(True, description="Se a empresa está ativa no sistema")
    regime_tributario: Optional[str] = Field(None, max_length=50, description="Regime tributário (texto, ex: Simples Nacional)")
    aliquotas_uf: Optional[Any] = Field(None, description="JSON: alíquotas por UF")

    # Modo de recebimento (SuperAdmin define)
    modo_recebimento: Optional[str] = Field("plataforma", max_length=20, description="'direto' = CA recebe na própria conta; 'plataforma' = plataforma recebe e repassa")
    taxa_plataforma_percentual: Optional[Decimal] = Field(None, description="Taxa percentual da plataforma sobre vendas (ex: 5.00 = 5%)")
    taxa_plataforma_valor_fixo: Optional[Decimal] = Field(None, description="Taxa fixa da plataforma por transação (ex: 2.50 = R$2,50)")
    gateway_plataforma: Optional[str] = Field(
        "mercadopago",
        max_length=30,
        description="Gateway quando modo_recebimento=plataforma: mercadopago, pagbank ou pagarme (SuperAdmin)",
    )

    # Vínculo com cliente direto do sistema (obrigatório: empresa fiscal pertence ao Cliente Administrador)
    cliente_id: Optional[int] = Field(None, description="ID do cliente (cliente direto) a que a empresa fiscal pertence")
    
    @validator('cnpj')
    def validate_cnpj(cls, v):
        """Validar formato básico do CNPJ"""
        if v:
            # Remove caracteres não numéricos
            cnpj_clean = ''.join(filter(str.isdigit, v))
            if len(cnpj_clean) != 14:
                raise ValueError("CNPJ deve ter 14 dígitos")
        return v
    
    @validator('cep')
    def validate_cep(cls, v):
        """Validar formato do CEP"""
        if v:
            cep_clean = ''.join(filter(str.isdigit, v))
            if len(cep_clean) != 8:
                raise ValueError("CEP deve ter 8 dígitos")
        return v
    
    @validator('uf')
    def validate_uf(cls, v):
        """Validar UF"""
        if v:
            v = v.upper()
            if len(v) != 2:
                raise ValueError("UF deve ter 2 caracteres")
        return v

    @validator("gateway_plataforma")
    def validate_gateway_plataforma(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return "mercadopago"
        s = str(v).strip().lower()
        if s not in ("mercadopago", "pagbank", "pagarme"):
            raise ValueError("gateway_plataforma deve ser mercadopago, pagbank ou pagarme")
        return s

class EmpresaCreate(EmpresaBase):
    """Schema para criação de empresa. cliente_id é obrigatório (empresa fiscal pertence ao cliente direto)."""
    cliente_id: int = Field(..., description="ID do cliente (cliente direto) - obrigatório")
    logo_emissor_blob: Optional[str] = Field(None, description="Imagem do logo em base64 (opcional; ao enviar, o arquivo é salvo e logo_url é preenchido automaticamente)")

class EmpresaUpdate(BaseModel):
    """Schema para atualização de empresa"""
    razao_social: Optional[str] = Field(None, min_length=1, max_length=255)
    nome_fantasia: Optional[str] = Field(None, max_length=255)
    cnpj: Optional[str] = Field(None, min_length=14, max_length=18)
    ie: Optional[str] = Field(None, max_length=20)
    im: Optional[str] = Field(None, max_length=20)
    cnae: Optional[str] = Field(None, max_length=20)
    crt: Optional[CRTEnum] = None
    
    cep: Optional[str] = Field(None, max_length=9)
    endereco: Optional[str] = Field(None, max_length=255)
    numero: Optional[str] = Field(None, max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: Optional[str] = Field(None, max_length=100)
    cidade: Optional[str] = Field(None, max_length=100)
    uf: Optional[str] = Field(None, max_length=2)
    telefone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    
    certificado_a1_path: Optional[str] = Field(None, max_length=255)
    certificado_a1_blob: Optional[str] = Field(None, description="Certificado em base64 (opcional, enviado via upload)")
    senha_certificado: Optional[str] = Field(None, max_length=100)
    certificado_validade: Optional[date] = None

    provedor_fiscal: Optional[str] = Field(None, max_length=50)
    
    ambiente: Optional[AmbienteEnum] = None
    uf_emissao: Optional[str] = Field(None, max_length=2)
    municipio_ibge: Optional[int] = None
    
    cnae_servicos: Optional[str] = Field(None, max_length=20)
    codigo_servico_municipal: Optional[str] = Field(None, max_length=20)
    aliquota_iss: Optional[Decimal] = None
    
    codigo_ativacao_sat: Optional[str] = Field(None, max_length=100)
    numero_serie_sat: Optional[str] = Field(None, max_length=100)
    tipo_equipamento_sat: Optional[TipoEquipamentoEnum] = None
    
    logo_url: Optional[str] = Field(None, max_length=512)
    logo_emissor_blob: Optional[str] = Field(None, description="Imagem do logo em base64 (opcional)")
    nfce_habilitado: Optional[bool] = None
    nfce_csc_id: Optional[str] = Field(None, max_length=10)
    nfce_csc_token: Optional[str] = Field(None, max_length=255)
    ativo: Optional[bool] = None
    cliente_id: Optional[int] = None
    regime_tributario: Optional[str] = Field(None, max_length=50)
    aliquotas_uf: Optional[Any] = None
    modo_recebimento: Optional[str] = Field(None, max_length=20, description="'direto' ou 'plataforma' (somente SuperAdmin)")
    taxa_plataforma_percentual: Optional[Decimal] = None
    taxa_plataforma_valor_fixo: Optional[Decimal] = None
    gateway_plataforma: Optional[str] = Field(None, max_length=30, description="mercadopago|pagbank|pagarme (somente SuperAdmin)")


class EmpresaResponse(EmpresaBase):
    """Schema para resposta de empresa"""
    id: int
    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = Field(None, description="Nome do cliente - preenchido pela API")
    modo_recebimento: Optional[str] = Field(None, description="'direto' ou 'plataforma'")
    taxa_plataforma_percentual: Optional[Decimal] = None
    taxa_plataforma_valor_fixo: Optional[Decimal] = None
    nfce_csc_token_configurado: Optional[bool] = Field(None, description="True se token CSC está configurado (nunca expõe o valor)")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @validator('ambiente', pre=True, always=True)
    def validar_ambiente(cls, v):
        """Converter string ou enum do SQLAlchemy para enum do Pydantic"""
        if v is None:
            return None
        # Se já for enum do Pydantic, retornar como está
        if isinstance(v, AmbienteEnum):
            return v
        # Se for objeto enum (do SQLAlchemy), pegar o valor
        if hasattr(v, 'value'):
            v = v.value
        # Se for string, normalizar e converter
        if isinstance(v, str):
            v = v.lower().strip()
            if v == 'homologacao':
                return AmbienteEnum.HOMOLOGACAO
            elif v == 'producao':
                return AmbienteEnum.PRODUCAO
        # Tentar converter para string e processar
        try:
            v_str = str(v).lower().strip()
            if v_str == 'homologacao':
                return AmbienteEnum.HOMOLOGACAO
            elif v_str == 'producao':
                return AmbienteEnum.PRODUCAO
        except:
            pass
        # Se não conseguir converter, retornar None (campo opcional)
        return None
    
    @validator('tipo_equipamento_sat', pre=True, always=True)
    def validar_tipo_equipamento(cls, v):
        """Converter string ou enum do SQLAlchemy para enum do Pydantic"""
        if v is None:
            return None
        # Se já for enum do Pydantic, retornar como está
        if isinstance(v, TipoEquipamentoEnum):
            return v
        # Se for objeto enum (do SQLAlchemy), pegar o valor
        if hasattr(v, 'value'):
            v = v.value
        # Se for string, normalizar e converter
        if isinstance(v, str):
            v = v.upper().strip()
            if v == 'SAT':
                return TipoEquipamentoEnum.SAT
            elif v in ['MFE', 'MFe']:
                return TipoEquipamentoEnum.MFE
        # Tentar converter para string e processar
        try:
            v_str = str(v).upper().strip()
            if v_str == 'SAT':
                return TipoEquipamentoEnum.SAT
            elif v_str in ['MFE', 'MFe']:
                return TipoEquipamentoEnum.MFE
        except:
            pass
        # Se não conseguir converter, retornar None (campo opcional)
        return None
    
    class Config:
        from_attributes = True

