# PDV Ibix - Re-export RBAC a partir do middleware (compatibilidade com código de referência)
"""
Módulo de compatibilidade para código que importa de app.core.rbac.
No PDV Ibix a autorização está em app.core.middleware; este módulo re-exporta
require_permission e fornece is_super_admin para uso em código de referência (ex.: app.api.v1.referencia).
Não montar routers de referência sem adaptar imports e modelos ao PDV Ibix.
"""
from ..models.usuario import Usuario


def is_super_admin(user: Usuario) -> bool:
    """Retorna True se o usuário tem role Superadministrador."""
    return bool(user and user.role and user.role.nome == "Superadministrador")
