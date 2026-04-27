# PDV Ibix - Mapeamento de status de pagamento (marketplace)
"""Status internos normalizados e regras de transição. Centraliza dicts espalhados."""
from typing import Dict, Tuple

# Status internos de pagamento (PaymentTransaction)
CREATED = "created"
PENDING = "pending"
AUTHORIZED = "authorized"
PAID = "paid"
REFUSED = "refused"
CANCELLED = "cancelled"
EXPIRED = "expired"
PARTIALLY_REFUNDED = "partially_refunded"
REFUNDED = "refunded"
CHARGEBACK = "chargeback"

STATUS_INTERNOS = {
    CREATED,
    PENDING,
    AUTHORIZED,
    PAID,
    REFUSED,
    CANCELLED,
    EXPIRED,
    PARTIALLY_REFUNDED,
    REFUNDED,
    CHARGEBACK,
}

# Métodos de pagamento V1
METHOD_PIX = "pix"
METHOD_CREDIT_CARD = "credit_card"

METHODS_V1 = {METHOD_PIX, METHOD_CREDIT_CARD}

# Mapeamento por provedor (status externo -> interno)
_MP_MAP: Dict[str, str] = {
    "approved": PAID,
    "authorized": AUTHORIZED,
    "in_process": PENDING,
    "pending": PENDING,
    "rejected": REFUSED,
    "cancelled": CANCELLED,
    "refunded": REFUNDED,
    "partially_refunded": PARTIALLY_REFUNDED,
    "charged_back": CHARGEBACK,
}

_PAGBANK_MAP: Dict[str, str] = {
    "paid": PAID,
    "authorized": AUTHORIZED,
    "in_analysis": PENDING,
    "waiting": PENDING,
    "declined": REFUSED,
    "canceled": CANCELLED,
    "refunded": REFUNDED,
}

_PAGARME_MAP: Dict[str, str] = {
    "paid": PAID,
    "pending": PENDING,
    "failed": REFUSED,
    "canceled": CANCELLED,
    "closed": PAID,
    "refunded": REFUNDED,
    "partially_refunded": PARTIALLY_REFUNDED,
}


def to_internal(provider_code: str, provider_status: str) -> str:
    """Converte status do provedor para status interno."""
    if not provider_status:
        return PENDING
    key = (provider_status or "").strip().lower()
    prov = (provider_code or "").lower()
    if prov == "mercadopago":
        return _MP_MAP.get(key, PENDING)
    if prov == "pagbank":
        return _PAGBANK_MAP.get(key, PENDING)
    if prov == "pagarme":
        return _PAGARME_MAP.get(key, PENDING)
    if key in ("approved", "paid", "completed"):
        return PAID
    if key in ("authorized",):
        return AUTHORIZED
    if key in ("rejected", "refused", "failed", "declined"):
        return REFUSED
    if key in ("cancelled", "canceled"):
        return CANCELLED
    if key in ("refunded",):
        return REFUNDED
    if key in ("expired",):
        return EXPIRED
    return PENDING


def is_terminal(status: str) -> bool:
    """Retorna True se o status é terminal (não muda mais)."""
    if not status:
        return False
    s = status.lower()
    return s in (PAID, REFUSED, CANCELLED, EXPIRED, REFUNDED, CHARGEBACK)


# Transições permitidas (from_status -> set(to_status))
_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    CREATED: (PENDING, CANCELLED),
    PENDING: (AUTHORIZED, PAID, REFUSED, CANCELLED, EXPIRED),
    AUTHORIZED: (PAID, REFUSED, CANCELLED, EXPIRED),
    PAID: (PARTIALLY_REFUNDED, REFUNDED, CHARGEBACK),
    REFUSED: (),  # terminal
    CANCELLED: (),  # terminal
    EXPIRED: (),  # terminal
    PARTIALLY_REFUNDED: (REFUNDED,),
    REFUNDED: (),  # terminal
    CHARGEBACK: (),  # terminal
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Retorna True se a transição from_status -> to_status é permitida."""
    if not from_status or not to_status:
        return False
    f = from_status.lower()
    t = to_status.lower()
    allowed = _TRANSITIONS.get(f, ())
    return t in allowed
