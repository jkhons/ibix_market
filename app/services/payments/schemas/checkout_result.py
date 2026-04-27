# PDV Ibix - DTO de retorno do checkout (marketplace)
"""Schema padronizado para o front consumir redirect_url e dados do gateway."""
from typing import Optional

from pydantic import BaseModel, Field


class CheckoutResultSchema(BaseModel):
    """Retorno da API de criação de checkout (create_checkout)."""
    provider: str = Field(..., description="Código do provedor (mercadopago, etc.)")
    checkout_type: str = Field(default="redirect", description="redirect, qr_code, etc.")
    payment_method: str = Field(..., description="pix, credit_card")
    provider_checkout_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    redirect_url: Optional[str] = Field(None, description="URL para redirecionar o usuário ao gateway")
    qr_code: Optional[str] = None
    qr_code_base64: Optional[str] = None
    copy_paste_code: Optional[str] = None
    expires_at: Optional[str] = None
    external_reference: Optional[str] = None
    raw_payload: Optional[dict] = None

    model_config = {"extra": "allow"}
