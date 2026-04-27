from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import log_error
from app.models.configuracao import Configuracao

CHAVE_WEBHOOK_VENDA_FECHADA_ENABLED = "integracoes.webhook.venda_fechada.enabled"
CHAVE_WEBHOOK_VENDA_FECHADA_URL = "integracoes.webhook.venda_fechada.url"
CHAVE_WEBHOOK_VENDA_FECHADA_TOKEN = "integracoes.webhook.venda_fechada.token"
CHAVE_WEBHOOK_VENDA_FECHADA_TIMEOUT = "integracoes.webhook.venda_fechada.timeout_seconds"


def _get_config(db: Session, chave: str) -> Optional[str]:
    item = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    return item.valor if item else None


def tenant_webhook_key(base_key: str, tenant_id: int) -> str:
    if tenant_id <= 0:
        raise ValueError("tenant_id inválido para configuração de integração")
    return f"{base_key}.tenant_{tenant_id}"


def _as_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "sim", "yes", "on"}


def _as_timeout_seconds(value: Optional[str]) -> int:
    if value is None or not value.strip():
        return 8
    parsed = int(value)
    if parsed <= 0:
        raise ValueError("Timeout do webhook de venda fechada deve ser maior que zero")
    return parsed


def queue_venda_fechada_webhook(
    db: Session,
    venda_id: int,
    numero_venda: str,
    cliente_id: Optional[int],
    total: Decimal | float,
    vendedor_id: int,
    tenant_id: Optional[int],
) -> bool:
    if not tenant_id:
        raise ValueError("Não foi possível emitir webhook de venda fechada sem tenant_id")

    cfg_enabled = tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_ENABLED, tenant_id)
    cfg_url = tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_URL, tenant_id)
    cfg_token = tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_TOKEN, tenant_id)
    cfg_timeout = tenant_webhook_key(CHAVE_WEBHOOK_VENDA_FECHADA_TIMEOUT, tenant_id)

    enabled = _as_bool(_get_config(db, cfg_enabled))
    if not enabled:
        return False

    webhook_url = _get_config(db, cfg_url)
    if not webhook_url:
        raise ValueError("Webhook de venda fechada está habilitado, mas URL não foi configurada")

    token = _get_config(db, cfg_token)
    timeout_seconds = _as_timeout_seconds(_get_config(db, cfg_timeout))

    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "venda.fechada",
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "cliente_id": cliente_id,
        "venda": {
            "id": venda_id,
            "numero_venda": numero_venda,
            "total": float(total),
            "vendedor_id": vendedor_id,
        },
    }

    try:
        from app.worker.tasks import dispatch_venda_fechada_webhook

        dispatch_venda_fechada_webhook.delay(
            webhook_url=webhook_url,
            payload=payload,
            token=token,
            timeout_seconds=timeout_seconds,
        )
        return True
    except Exception as exc:
        log_error(f"Falha ao enfileirar webhook venda.fechada: {exc}")
        return False
