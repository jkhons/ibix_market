# PDV Ibix - Secrets candidatos para validação de webhook Mercado Pago (x-signature)
"""Única fonte da lista de secrets usada em POST /api/webhooks/mercadopago.

Ordem (documentação operacional):
1. Secret global: billing_mp_webhook_secret (Configuracao) → fallback env MP_WEBHOOK_SECRET via get_mp_webhook_secret.
2. Por estabelecimento (PaymentProviderConfig ativo, provider mercadopago):
   - Coluna webhook_secret_encrypted (decrypt_text), se preenchida;
   - Credenciais JSON: webhook_secret, WEBHOOK_SECRET, mp_webhook_secret.

Sem duplicar o mesmo valor na lista. Não logar secrets."""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.billing_config import get_mp_webhook_secret
from app.models import PaymentProviderConfig
from app.services.payments.credentials import decrypt_credentials, decrypt_text


def _append_if_new(secrets: List[str], value: Optional[str]) -> None:
    if value is None:
        return
    s = str(value).strip()
    if s and s not in secrets:
        secrets.append(s)


def list_mp_webhook_secret_candidates(db: Session) -> List[str]:
    """
    Retorna lista ordenada de secrets para tentar verify_webhook_signature até o primeiro match.

    Inclui get_mp_webhook_secret (sem leitura duplicada de MP_WEBHOOK_SECRET) e todas as fontes
    por cliente (coluna dedicada + JSON).
    """
    secrets: List[str] = []
    _append_if_new(secrets, get_mp_webhook_secret(db))

    configs = (
        db.query(PaymentProviderConfig)
        .filter(
            PaymentProviderConfig.provider_code == "mercadopago",
            PaymentProviderConfig.is_active.is_(True),
        )
        .order_by(PaymentProviderConfig.id.desc())
        .limit(100)
        .all()
    )
    for cfg in configs:
        if getattr(cfg, "webhook_secret_encrypted", None):
            col = decrypt_text(cfg.webhook_secret_encrypted)
            _append_if_new(secrets, col)
        creds = decrypt_credentials(cfg.credentials_encrypted) or {}
        for key in ("webhook_secret", "WEBHOOK_SECRET", "mp_webhook_secret"):
            val = creds.get(key)
            if val:
                _append_if_new(secrets, str(val))

    return secrets
