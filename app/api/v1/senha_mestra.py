# PDV Ibix - API Senha mestra por estabelecimento (Fase 5.2)
"""Definir e validar senha mestra por estabelecimento. Política: por estabelecimento, validade temporária, nunca hardcoded."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import AuthConfig
from app.core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from app.core.scope import ClienteScope
from app.database.connection import get_db
from app.models import SenhaMestraEstabelecimento, Usuario

router = APIRouter(prefix="/senha-mestra", tags=["Senha mestra (Fase 5.2)"])


class DefinirSenhaBody(BaseModel):
    cliente_id: int
    senha: str
    expira_em_horas: Optional[int] = None  # null = até próxima alteração


class ValidarSenhaBody(BaseModel):
    cliente_id: int
    senha: str


def _cliente_no_escopo(cliente_id: int, scope: ClienteScope) -> bool:
    if not scope.must_filter_by_cliente():
        return True
    return scope.allowed_ids is not None and cliente_id in scope.allowed_ids


@router.post("/definir")
async def definir_senha_mestra(
    body: DefinirSenhaBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Define ou atualiza a senha mestra do estabelecimento. Apenas Super Admin, Admin ou CA (no escopo)."""
    role = (current_user.role.nome if current_user.role else "") or ""
    if role not in ("Superadministrador", "Administrador", "Cliente Administrador"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para definir senha mestra")
    if not _cliente_no_escopo(body.cliente_id, scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Estabelecimento fora do escopo")
    if not body.senha or len(body.senha.strip()) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha deve ter no mínimo 4 caracteres")
    hash_val = AuthConfig.get_password_hash(body.senha.strip())
    expira_em = None
    if body.expira_em_horas is not None and body.expira_em_horas > 0:
        expira_em = datetime.now(timezone.utc) + timedelta(hours=body.expira_em_horas)
    rec = db.query(SenhaMestraEstabelecimento).filter(SenhaMestraEstabelecimento.cliente_id == body.cliente_id).first()
    if rec:
        rec.senha_hash = hash_val
        rec.expira_em = expira_em
    else:
        rec = SenhaMestraEstabelecimento(cliente_id=body.cliente_id, senha_hash=hash_val, expira_em=expira_em)
        db.add(rec)
    db.commit()
    return {"ok": True, "message": "Senha mestra definida.", "expira_em": rec.expira_em.isoformat() if rec.expira_em else None}


@router.post("/validar")
async def validar_senha_mestra(
    body: ValidarSenhaBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Valida a senha mestra do estabelecimento (para sangria, suprimento, desconto, etc.). Retorna valido: true/false."""
    if not _cliente_no_escopo(body.cliente_id, scope):
        return {"valido": False}
    rec = db.query(SenhaMestraEstabelecimento).filter(SenhaMestraEstabelecimento.cliente_id == body.cliente_id).first()
    if not rec:
        return {"valido": False}
    now = datetime.now(timezone.utc)
    if rec.expira_em and rec.expira_em.tzinfo is None:
        rec.expira_em = rec.expira_em.replace(tzinfo=timezone.utc)
    if rec.expira_em and rec.expira_em < now:
        return {"valido": False}
    valido = AuthConfig.verify_password(body.senha, rec.senha_hash)
    return {"valido": valido}