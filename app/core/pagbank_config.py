# PDV Ibix - Configuração PagBank Connect (OAuth)
"""Leitura de credenciais da aplicação PagBank Connect (client_id, client_secret, sandbox)."""
import os
from typing import Optional

from sqlalchemy.orm import Session


def _get_from_configuracoes(db: Optional[Session], chave: str) -> Optional[str]:
    """Busca chave na tabela configuracoes (fallback para env)."""
    if not db:
        return None
    try:
        from app.core.billing_secrets import decrypt_stored_secret, is_billing_secret_key
        from app.models.configuracao import Configuracao

        row = db.query(Configuracao).filter(Configuracao.chave == chave).first()
        if row and row.valor:
            raw = row.valor.strip()
            if is_billing_secret_key(chave):
                return decrypt_stored_secret(raw)
            return raw
    except Exception:
        pass
    return None


def get_pagbank_client_id(db: Optional[Session] = None) -> str:
    """Retorna o client_id da aplicação PagBank Connect."""
    val = _get_from_configuracoes(db, "payment_pagbank_connect_client_id")
    if val:
        return val
    val = os.environ.get("PAGBANK_CONNECT_CLIENT_ID", "").strip()
    if not val:
        raise ValueError(
            "PagBank Connect não configurado. Defina PAGBANK_CONNECT_CLIENT_ID "
            "no ambiente ou na tabela configuracoes (chave payment_pagbank_connect_client_id)."
        )
    return val


def get_pagbank_client_secret(db: Optional[Session] = None) -> str:
    """Retorna o client_secret da aplicação PagBank Connect."""
    val = _get_from_configuracoes(db, "payment_pagbank_connect_client_secret")
    if val:
        return val
    val = os.environ.get("PAGBANK_CONNECT_CLIENT_SECRET", "").strip()
    if not val:
        raise ValueError(
            "PagBank Connect não configurado. Defina PAGBANK_CONNECT_CLIENT_SECRET "
            "no ambiente ou na tabela configuracoes (chave payment_pagbank_connect_client_secret)."
        )
    return val


def is_pagbank_sandbox(db: Optional[Session] = None) -> bool:
    """Retorna True se deve usar ambiente sandbox do PagBank."""
    val = _get_from_configuracoes(db, "payment_pagbank_connect_sandbox")
    if val is not None:
        return val.lower() in ("true", "1", "yes", "sim")
    return os.environ.get("PAGBANK_CONNECT_SANDBOX", "true").strip().lower() in ("true", "1", "yes", "sim")


def get_pagbank_base_url(db: Optional[Session] = None) -> str:
    """URL base da API PagBank (sandbox ou produção)."""
    if is_pagbank_sandbox(db):
        return "https://sandbox.api.pagseguro.com"
    return "https://api.pagseguro.com"


def get_pagbank_connect_url(db: Optional[Session] = None) -> str:
    """URL base do Connect PagBank (sandbox ou produção)."""
    if is_pagbank_sandbox(db):
        return "https://connect.sandbox.pagbank.com.br"
    return "https://connect.pagbank.com.br"
