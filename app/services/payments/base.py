# PDV Ibix - Interface base de provedor (marketplace checkout redirecionado)
"""Contrato único multi-gateway: create_checkout, fetch_payment, refund, parse_webhook, supports_method, connect_account."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass
class CheckoutResult:
    """Retorno normalizado de create_checkout (desacopla front do gateway)."""
    provider: str
    checkout_type: str  # redirect, qr_code, etc.
    payment_method: str
    provider_checkout_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    redirect_url: Optional[str] = None
    qr_code: Optional[str] = None
    qr_code_base64: Optional[str] = None
    copy_paste_code: Optional[str] = None
    expires_at: Optional[str] = None  # ISO datetime
    external_reference: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class NormalizedWebhookEvent:
    """Evento de webhook normalizado para processamento interno."""
    provider: str
    event_key: str
    event_type: Optional[str] = None
    provider_event_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    normalized_status: Optional[str] = None
    signature_valid: bool = False
    raw_payload: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None


class PaymentProviderBase(ABC):
    """Interface que provedores de pagamento (Mercado Pago, Asaas, etc.) implementam para checkout marketplace."""

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Código do provedor (mercadopago, asaas, pagarme, stripe)."""
        pass

    def connect_account(self, credentials: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """OAuth/conexão delegada. V1 pode não implementar; retorna status."""
        return {"connected": False, "message": "Não implementado na V1"}

    @abstractmethod
    def create_checkout(
        self,
        amount: Decimal,
        payment_method: str,
        external_reference: str,
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CheckoutResult:
        """Cria sessão de checkout; retorna redirect_url e/ou dados Pix. Credentials já descriptografadas."""
        pass

    @abstractmethod
    def fetch_payment(
        self,
        provider_payment_id: str,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Consulta pagamento no provedor. Retorna dict com status e dados ou None."""
        pass

    @abstractmethod
    def refund(
        self,
        provider_payment_id: str,
        amount: Optional[Decimal] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Solicita estorno (total ou parcial). Retorna dict com success, provider_refund_id, message."""
        pass

    @abstractmethod
    def parse_webhook(
        self,
        payload: bytes,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[NormalizedWebhookEvent]:
        """Parseia e valida webhook; retorna evento normalizado ou None se inválido."""
        pass

    def supports_method(self, method: str) -> bool:
        """Retorna True se o provedor suporta o método (pix, credit_card)."""
        return method.lower() in ("pix", "credit_card", "credit", "debit", "boleto")
