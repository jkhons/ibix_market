# PDV Ibix — RBAC e auditoria de acesso a PII (Fase 4 LGPD)
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.audit import audit_action
from app.core.middleware import get_user_permissions
from app.models.usuario import Usuario

PERMISSAO_PII = "pii:visualizar"

# Roles que operam dados de clientes do tenant — veem CPF/CNPJ/contato sem permissão extra.
_ROLES_PII_CLIENTE_NATIVO = frozenset(
    {
        "Superadministrador",
        "Administrador",
        "Cliente Administrador",
    }
)


def user_can_view_pii(db: Session, user: Usuario) -> bool:
    role_nome = (user.role.nome if user.role else "") or ""
    if role_nome in _ROLES_PII_CLIENTE_NATIVO:
        return True
    return PERMISSAO_PII in get_user_permissions(user.id, db)


def audit_pii_access(
    db: Session,
    *,
    acao: str,
    actor: Usuario,
    recurso_tipo: str,
    recurso_id: Optional[int] = None,
    ip: Optional[str] = None,
    request_id: Optional[str] = None,
    detalhes: Optional[str] = None,
) -> None:
    audit_action(
        db,
        acao,
        user_id=actor.id,
        tenant_id=getattr(actor, "tenant_id", None),
        recurso_tipo=recurso_tipo,
        recurso_id=recurso_id,
        ip=ip,
        request_id=request_id,
        detalhes=detalhes,
    )
