# PDV Ibix — Configuração de notificações de novo cadastro CA (plataforma)
"""Chaves em `configuracoes`; leitura explícita com default True se registro ausente (bancos pré-migration)."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Configuracao

CHAVE_NOVO_CA_EMAIL_ENABLED = "platform_novo_ca_email_enabled"
CHAVE_NOVO_CA_IN_APP_ENABLED = "platform_novo_ca_in_app_enabled"


def _truthy(val: Optional[str]) -> bool:
    if val is None:
        return True
    s = str(val).strip().lower()
    if s == "":
        return True
    return s in ("1", "true", "yes", "on", "sim")


def get_novo_ca_email_enabled(db: Session) -> bool:
    row = db.query(Configuracao).filter(Configuracao.chave == CHAVE_NOVO_CA_EMAIL_ENABLED).first()
    if not row:
        return True
    return _truthy(row.valor)


def get_novo_ca_in_app_enabled(db: Session) -> bool:
    row = db.query(Configuracao).filter(Configuracao.chave == CHAVE_NOVO_CA_IN_APP_ENABLED).first()
    if not row:
        return True
    return _truthy(row.valor)


def upsert_config_bool(db: Session, chave: str, enabled: bool, descricao: str) -> None:
    val = "true" if enabled else "false"
    row = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if row:
        row.valor = val
    else:
        db.add(Configuracao(chave=chave, valor=val, descricao=descricao))
