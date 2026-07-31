# PDV Ibix — Utilitários PII (Fase 4 LGPD)
"""Mascaramento de dados pessoais em respostas de API sem permissão dedicada."""
from __future__ import annotations

import re
from typing import Any, Optional


def mask_cpf(value: Optional[str]) -> Optional[str]:
    if not value or not str(value).strip():
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 11:
        return "***"
    return f"***.***.***-{digits[-2:]}"


def mask_rg(value: Optional[str]) -> Optional[str]:
    if not value or not str(value).strip():
        return None
    s = str(value).strip()
    if len(s) <= 4:
        return "***"
    return f"***{s[-4:]}"


def mask_documento_path(value: Optional[str]) -> Optional[str]:
    if not value or not str(value).strip():
        return None
    return "[documento restrito]"


def mask_cnpj(value: Optional[str]) -> Optional[str]:
    if not value or not str(value).strip():
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) < 4:
        return "***"
    return f"**.***.***/****-{digits[-2:]}"


def mask_telefone(value: Optional[str]) -> Optional[str]:
    if not value or not str(value).strip():
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) < 4:
        return "***"
    return f"****-{digits[-4:]}"


def mask_email(value: Optional[str]) -> Optional[str]:
    if not value or "@" not in str(value):
        return None
    local, _, domain = str(value).strip().partition("@")
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


def apply_usuario_pii_mask(payload: dict[str, Any], *, reveal: bool) -> dict[str, Any]:
    """Oculta CPF/RG/documento_path quando reveal=False."""
    if reveal:
        return payload
    out = dict(payload)
    if out.get("cpf") is not None:
        out["cpf"] = mask_cpf(out.get("cpf"))
    if out.get("rg") is not None:
        out["rg"] = mask_rg(out.get("rg"))
    if out.get("documento_path") is not None:
        out["documento_path"] = mask_documento_path(out.get("documento_path"))
    return out


def apply_cliente_pii_mask(payload: dict[str, Any], *, reveal: bool) -> dict[str, Any]:
    """Oculta CPF/CNPJ/telefone/e-mail quando reveal=False."""
    if reveal:
        return payload
    out = dict(payload)
    if out.get("cpf") is not None:
        out["cpf"] = mask_cpf(out.get("cpf"))
    if out.get("cnpj") is not None:
        out["cnpj"] = mask_cnpj(out.get("cnpj"))
    if out.get("telefone") is not None:
        out["telefone"] = mask_telefone(out.get("telefone"))
    if out.get("email") is not None:
        out["email"] = mask_email(out.get("email"))
    return out


def apply_entregador_pii_mask(payload: dict[str, Any], *, reveal: bool) -> dict[str, Any]:
    """Oculta CPF/telefone/CNH quando reveal=False."""
    if reveal:
        return payload
    out = dict(payload)
    if out.get("cpf") is not None:
        out["cpf"] = mask_cpf(out.get("cpf"))
    if out.get("telefone") is not None:
        out["telefone"] = mask_telefone(out.get("telefone"))
    if out.get("cnh_arquivo_path") is not None:
        out["cnh_arquivo_path"] = mask_documento_path(out.get("cnh_arquivo_path"))
    return out
