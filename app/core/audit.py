# PDV Ibix - Auditoria de ações sensíveis (Saas.md 1.4)
"""Registro de ações para conformidade e análise. Não logar senhas, tokens ou dados pessoais em claro.
Helper audit_action persiste em audit_log (com tenant_id) e grava em arquivo."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models.audit_log import AuditLog
from .logging import log_audit


def _mask(value: Any) -> str:
    """Mascara valores sensíveis em detalhes."""
    if value is None:
        return ""
    s = str(value)
    if "senha" in s.lower() or "password" in s.lower() or "token" in s.lower():
        return "[REDACTED]"
    return s


def audit_action(
    db: Session,
    acao: str,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    recurso_tipo: Optional[str] = None,
    recurso_id: Optional[int] = None,
    ip: Optional[str] = None,
    request_id: Optional[str] = None,
    detalhes: Optional[str] = None,
) -> None:
    """
    Persiste ação em audit_log e grava em arquivo. Use em todas as ações críticas.
    tenant_id: nullable para SuperAdmin; derivado do usuário quando possível.
    """
    user_str = str(user_id) if user_id is not None else "system"
    parts = [f"acao={acao}", f"user_id={user_str}"]
    if tenant_id is not None:
        parts.append(f"tenant_id={tenant_id}")
    if recurso_tipo:
        parts.append(f"recurso={recurso_tipo}")
    if recurso_id is not None:
        parts.append(f"recurso_id={recurso_id}")
    if ip:
        parts.append(f"ip={ip}")
    if detalhes:
        parts.append(f"detalhes={_mask(detalhes)}")
    log_audit(acao, user_str, " | ".join(parts))

    try:
        entry = AuditLog(
            user_id=user_id,
            tenant_id=tenant_id,
            acao=acao,
            recurso_tipo=recurso_tipo,
            recurso_id=recurso_id,
            ip=ip,
            request_id=request_id,
            detalhes=_mask(detalhes) if detalhes else None,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
        raise


def log_audit_action(
    acao: str,
    user_id: Optional[int] = None,
    recurso_tipo: Optional[str] = None,
    recurso_id: Optional[int] = None,
    detalhes: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    """
    Registra ação sensível apenas em arquivo (legado). Preferir audit_action(db, ...) quando db disponível.
    Ex.: login_sucesso, login_falha, role_alterada, usuario_excluido.
    """
    user_str = str(user_id) if user_id is not None else "system"
    parts = [f"acao={acao}", f"user_id={user_str}"]
    if recurso_tipo:
        parts.append(f"recurso={recurso_tipo}")
    if recurso_id is not None:
        parts.append(f"recurso_id={recurso_id}")
    if ip:
        parts.append(f"ip={ip}")
    if detalhes:
        parts.append(f"detalhes={_mask(detalhes)}")
    log_audit(acao, user_str, " | ".join(parts))
