# PDV Ibix — Provedor de segredos (Fase 9 — extensível para cofre externo)
"""
Ordem de resolução:
1. Variável de ambiente
2. Arquivo em SECRETS_DIR/{name} (modo 0600 recomendado)
3. Erro explícito se required=True

Integração futura: Vault / AWS Secrets Manager via SECRETS_BACKEND=vault|aws
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def secrets_dir() -> Optional[Path]:
    raw = (os.getenv("SECRETS_DIR") or "").strip()
    if not raw:
        return None
    return Path(raw)


def get_secret(name: str, *, required: bool = False, env_fallback: Optional[str] = None) -> str:
    """Obtém segredo por env ou arquivo. Sem fallback silencioso quando required=True."""
    env_name = env_fallback or name
    val = (os.getenv(env_name) or "").strip()
    if val:
        return val

    sdir = secrets_dir()
    if sdir is not None:
        path = sdir / name
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()

    if required:
        raise RuntimeError(
            f"Segredo obrigatório ausente: {name} (env {env_name} ou {sdir}/{name if sdir else 'SECRETS_DIR'})"
        )
    return ""


def secrets_backend() -> str:
    return (os.getenv("SECRETS_BACKEND") or "env").strip().lower()
