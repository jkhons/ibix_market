# PDV Ibix - Helpers para erros de banco (PostgreSQL)
"""Detecção de violação de unicidade (PostgreSQL)."""

from typing import Optional


def is_unique_violation(e: Exception) -> bool:
    """Retorna True se a exceção for violação de constraint única (PostgreSQL)."""
    if e is None:
        return False
    orig = getattr(e, "orig", None)
    if orig is None:
        return False
    # PostgreSQL: código 23505 = unique_violation
    return getattr(orig, "pgcode", None) == "23505"


def get_constraint_name(e: Exception) -> Optional[str]:
    """Retorna o nome da constraint envolvida, se disponível (PostgreSQL)."""
    orig = getattr(e, "orig", None)
    if orig is None:
        return None
    diag = getattr(orig, "diag", None)
    if diag is not None:
        return getattr(diag, "constraint_name", None)
    return None
