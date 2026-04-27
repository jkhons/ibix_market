# PDV Ibix - Schemas Module
from .auth import (
    LoginResponse,
    LogoutResponse,
    PasswordChange,
    Token,
    TokenData,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from .cupom_fiscal import (
    CupomFiscalBase,
    CupomFiscalCreate,
    CupomFiscalItemBase,
    CupomFiscalItemCreate,
    CupomFiscalItemResponse,
    CupomFiscalResponse,
    CupomFiscalUpdate,
    StatusCupomEnum,
)
from .cupom_fiscal import TipoEquipamentoEnum as TipoEquipamentoCupomEnum

# Schemas Fiscais
from .empresa import (
    AmbienteEnum,
    CRTEnum,
    EmpresaBase,
    EmpresaCreate,
    EmpresaResponse,
    EmpresaUpdate,
    TipoEquipamentoEnum,
)
from .mdfe import (
    MDFeBase,
    MDFeCondutorBase,
    MDFeCondutorCreate,
    MDFeCondutorResponse,
    MDFeCreate,
    MDFeDocumentoBase,
    MDFeDocumentoCreate,
    MDFeDocumentoResponse,
    MDFePercursoBase,
    MDFePercursoCreate,
    MDFePercursoResponse,
    MDFeResponse,
    MDFeUpdate,
    MDFeVeiculoBase,
    MDFeVeiculoCreate,
    MDFeVeiculoResponse,
    StatusMDFeEnum,
    TipoDocumentoEnum,
)
from .nfse import (
    NfseCancelRequest,
    NfseInvoiceCreate,
    NfseInvoiceCreateFromOS,
    NfseInvoiceCreateFromSubscription,
    NfseInvoiceResponse,
    NfseIssueRequest,
    TenantNfseConfigResponse,
    TenantNfseConfigUpdate,
)
from .nota_fiscal import AmbienteEnum as AmbienteNotaEnum
from .nota_fiscal import (
    NotaFiscalBase,
    NotaFiscalCreate,
    NotaFiscalItemBase,
    NotaFiscalItemCreate,
    NotaFiscalItemResponse,
    NotaFiscalResponse,
    NotaFiscalUpdate,
    StatusNotaEnum,
    TipoNotaEnum,
)
from .nota_servico import (
    NotaServicoBase,
    NotaServicoCreate,
    NotaServicoItemBase,
    NotaServicoItemCreate,
    NotaServicoItemResponse,
    NotaServicoResponse,
    NotaServicoUpdate,
    StatusNotaServicoEnum,
)

__all__ = [
    "UserLogin",
    "UserRegister", 
    "Token",
    "TokenData",
    "UserResponse",
    "UserUpdate",
    "PasswordChange",
    "LoginResponse",
    "LogoutResponse",
    # Schemas Fiscais - Empresa
    "EmpresaBase",
    "EmpresaCreate",
    "EmpresaUpdate",
    "EmpresaResponse",
    "AmbienteEnum",
    "TipoEquipamentoEnum",
    "CRTEnum",
    
    # Schemas Fiscais - Nota Fiscal
    "NotaFiscalBase",
    "NotaFiscalCreate",
    "NotaFiscalUpdate",
    "NotaFiscalResponse",
    "NotaFiscalItemBase",
    "NotaFiscalItemCreate",
    "NotaFiscalItemResponse",
    "TipoNotaEnum",
    "StatusNotaEnum",
    "AmbienteNotaEnum",
    
    # Schemas Fiscais - Nota Serviço
    "NotaServicoBase",
    "NotaServicoCreate",
    "NotaServicoUpdate",
    "NotaServicoResponse",
    "NotaServicoItemBase",
    "NotaServicoItemCreate",
    "NotaServicoItemResponse",
    "StatusNotaServicoEnum",
    
    # Schemas Fiscais - Cupom Fiscal
    "CupomFiscalBase",
    "CupomFiscalCreate",
    "CupomFiscalUpdate",
    "CupomFiscalResponse",
    "CupomFiscalItemBase",
    "CupomFiscalItemCreate",
    "CupomFiscalItemResponse",
    "TipoEquipamentoCupomEnum",
    "StatusCupomEnum",
    
    # Schemas Fiscais - MDF-e
    "MDFeBase",
    "MDFeCreate",
    "MDFeUpdate",
    "MDFeResponse",
    "MDFeDocumentoBase",
    "MDFeDocumentoCreate",
    "MDFeDocumentoResponse",
    "MDFeVeiculoBase",
    "MDFeVeiculoCreate",
    "MDFeVeiculoResponse",
    "MDFeCondutorBase",
    "MDFeCondutorCreate",
    "MDFeCondutorResponse",
    "MDFePercursoBase",
    "MDFePercursoCreate",
    "MDFePercursoResponse",
    "StatusMDFeEnum",
    "TipoDocumentoEnum",

    # NFS-e (módulo faturamento)
    "NfseInvoiceCreate",
    "NfseInvoiceCreateFromSubscription",
    "NfseInvoiceCreateFromOS",
    "NfseIssueRequest",
    "NfseCancelRequest",
    "NfseInvoiceResponse",
    "TenantNfseConfigUpdate",
    "TenantNfseConfigResponse",
] 