# PDV Ibix - Configuração Schemas
from typing import List, Optional

from pydantic import BaseModel


class ConfiguracaoBase(BaseModel):
    chave: str
    valor: str
    descricao: Optional[str] = None

class ConfiguracaoCreate(ConfiguracaoBase):
    pass

class ConfiguracaoUpdate(BaseModel):
    valor: str
    descricao: Optional[str] = None

class ConfiguracaoResponse(ConfiguracaoBase):
    id: int
    
    class Config:
        from_attributes = True

# E-mail por função: remetente (from_email, from_name) por codigo de função
class EmailFuncaoItem(BaseModel):
    codigo: str
    label: str
    descricao: Optional[str] = None
    from_email: str = ""
    from_name: str = ""


class EmailFuncaoItemUpdate(BaseModel):
    codigo: str
    from_email: Optional[str] = None
    from_name: Optional[str] = None


class EmailFuncoesResponse(BaseModel):
    funcoes: List[EmailFuncaoItem]


class EmailFuncoesUpdate(BaseModel):
    funcoes: List[EmailFuncaoItemUpdate]


# WhatsApp (apenas Superadministrador)
class ConfiguracaoWhatsAppResponse(BaseModel):
    ativo: bool = False
    phone_number_id: Optional[str] = None
    verify_token: Optional[str] = None
    business_account_id: Optional[str] = None
    token_preenchido: bool = False
    app_secret_preenchido: bool = False


class ConfiguracaoWhatsAppRequest(BaseModel):
    ativo: bool = False
    phone_number_id: Optional[str] = None
    token: Optional[str] = None
    verify_token: Optional[str] = None
    business_account_id: Optional[str] = None
    app_secret: Optional[str] = None
