# PDV Ibix — Contexto estruturado automático nos logs (Fase 9)
"""Injeta request_id, tenant_id, brand_id, brand_slug em todo log via ContextVar."""
from __future__ import annotations

import logging
from typing import Any

from app.core.request_context import get_request_context


class RequestContextLogFilter(logging.Filter):
    """Prefixa record.msg com key=value do contexto HTTP/Celery."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_request_context()
        if not ctx:
            return True
        parts: list[str] = []
        for key in ("request_id", "tenant_id", "brand_id", "brand_slug", "user_id"):
            val = ctx.get(key)
            if val is not None and val != "":
                parts.append(f"{key}={val}")
        if not parts:
            return True
        prefix = " ".join(parts) + " "
        try:
            msg = record.getMessage()
            if not msg.startswith(prefix.rstrip()):
                record.msg = prefix + msg
                record.args = ()
        except Exception:
            pass
        return True


def install_structured_log_context() -> None:
    """Registra filtro nos loggers principais da aplicação."""
    filt = RequestContextLogFilter()
    for name in ("pdv_solumatica", "app", ""):
        log = logging.getLogger(name)
        if not any(isinstance(f, RequestContextLogFilter) for f in log.filters):
            log.addFilter(filt)
        for h in log.handlers:
            if not any(isinstance(f, RequestContextLogFilter) for f in h.filters):
                h.addFilter(filt)
