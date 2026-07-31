# PDV Ibix - API Movimentos de Caixa (Fase 3.2 - sangria/suprimento)
"""Listar e registrar sangria/suprimento por abertura de caixa. Senha mestra por estabelecimento (Fase 3)."""
from typing import List, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.audit import audit_action
from ...core.middleware import get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope, get_cliente_ids_escopo_caixa
from ...database.connection import get_db
from ...models import AberturaCaixa, Caixa, Configuracao, Empresa, MovimentoCaixa, Usuario
from ...schemas.movimento_caixa import MovimentoCaixaCreate, MovimentoCaixaResponse

CAIXA_SENHA_MESTRA_PREFIX = "caixa_senha_mestra_"

router = APIRouter(prefix="/movimentos-caixa", tags=["Movimentos de caixa (sangria/suprimento)"])

ROLES_CAIXA = ("Superadministrador", "Administrador", "Cliente Administrador", "Operador PDV")


class SenhaMestraConfig(BaseModel):
    """Configurar senha mestra do caixa por estabelecimento."""
    cliente_id: int
    senha_mestra: str  # Será hasheada antes de salvar


def _role_ok(user: Usuario) -> bool:
    role_nome = user.role.nome if user.role else None
    return role_nome in ROLES_CAIXA


def _cliente_id_caixa(db: Session, caixa: Caixa) -> Optional[int]:
    emp = db.query(Empresa).filter(Empresa.id == caixa.empresa_id).first()
    return int(emp.cliente_id) if emp and emp.cliente_id is not None else None


def _can_access_abertura(
    scope: ClienteScope,
    caixa: Caixa,
    role_nome: Optional[str],
    db: Session,
    user_id: int,
) -> bool:
    if not scope.must_filter_by_cliente():
        return True
    cid = _cliente_id_caixa(db, caixa)
    if cid is None:
        return False
    cliente_ids = get_cliente_ids_escopo_caixa(db, user_id, role_nome, scope)
    if cliente_ids is None:
        return True
    return cid in cliente_ids


@router.post("/senha-mestra", status_code=status.HTTP_204_NO_CONTENT)
async def configurar_senha_mestra(
    body: SenhaMestraConfig,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Define a senha mestra para sangria/suprimento do estabelecimento. Super Admin, Admin ou CA (no escopo)."""
    role_nome = (current_user.role.nome if current_user.role else "") or ""
    if role_nome not in ("Superadministrador", "Administrador", "Cliente Administrador"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas Super Admin, Administrador ou Cliente Administrador podem configurar a senha mestra")
    if scope.must_filter_by_cliente() and (not scope.allowed_ids or body.cliente_id not in scope.allowed_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Estabelecimento fora do seu escopo")
    if not body.senha_mestra or len(body.senha_mestra.strip()) < 4:
        raise HTTPException(status_code=400, detail="Senha mestra deve ter no mínimo 4 caracteres")
    chave = f"{CAIXA_SENHA_MESTRA_PREFIX}{body.cliente_id}"
    hash_val = bcrypt.hashpw(body.senha_mestra.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if config:
        config.valor = hash_val
    else:
        db.add(Configuracao(chave=chave, valor=hash_val, descricao=f"Senha mestra caixa (estabelecimento {body.cliente_id})"))
    db.commit()
    return None


@router.get("/", response_model=List[MovimentoCaixaResponse])
async def listar_movimentos(
    abertura_caixa_id: int = Query(..., description="ID da abertura de caixa"),
    tipo: Optional[str] = Query(None, description="sangria | suprimento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista movimentos (sangria/suprimento) de uma abertura de caixa. Requer permissão de caixa."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para acessar movimentos de caixa")
    ab = db.query(AberturaCaixa).filter(AberturaCaixa.id == abertura_caixa_id).first()
    if not ab:
        raise HTTPException(status_code=404, detail="Abertura de caixa não encontrada")
    caixa = db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_abertura(scope, caixa, role_nome, db, current_user.id):
        raise HTTPException(status_code=403, detail="Abertura fora do escopo")
    q = db.query(MovimentoCaixa).filter(MovimentoCaixa.abertura_caixa_id == abertura_caixa_id)
    if tipo:
        q = q.filter(MovimentoCaixa.tipo == tipo)
    rows = q.order_by(MovimentoCaixa.created_at.desc()).all()
    return [MovimentoCaixaResponse.model_validate(r) for r in rows]


def _exige_senha_mestra(db: Session, cliente_id: int) -> bool:
    """Verifica se o estabelecimento tem senha mestra configurada para sangria/suprimento."""
    chave = f"{CAIXA_SENHA_MESTRA_PREFIX}{cliente_id}"
    c = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    return c is not None and bool(c.valor)


class ExigeSenhaResponse(BaseModel):
    exige_senha: bool


@router.get("/exige-senha-mestra", response_model=ExigeSenhaResponse)
async def exige_senha_mestra(
    abertura_caixa_id: int = Query(..., description="ID da abertura de caixa"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Verifica se o estabelecimento (da abertura) exige senha mestra para sangria/suprimento."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")
    ab = db.query(AberturaCaixa).filter(AberturaCaixa.id == abertura_caixa_id).first()
    if not ab:
        raise HTTPException(status_code=404, detail="Abertura de caixa não encontrada")
    caixa = db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_abertura(scope, caixa, role_nome, db, current_user.id):
        raise HTTPException(status_code=403, detail="Abertura fora do escopo")
    cid = _cliente_id_caixa(db, caixa)
    if cid is None:
        return ExigeSenhaResponse(exige_senha=False)
    return ExigeSenhaResponse(exige_senha=_exige_senha_mestra(db, cid))


@router.post("/", response_model=MovimentoCaixaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_movimento(
    body: MovimentoCaixaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Registra sangria ou suprimento. Se o estabelecimento tiver senha mestra configurada, senha_mestra é obrigatória."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para registrar movimento de caixa")
    if body.tipo not in ("sangria", "suprimento"):
        raise HTTPException(status_code=400, detail="tipo deve ser 'sangria' ou 'suprimento'")
    ab = db.query(AberturaCaixa).filter(AberturaCaixa.id == body.abertura_caixa_id).first()
    if not ab:
        raise HTTPException(status_code=404, detail="Abertura de caixa não encontrada")
    caixa = db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_abertura(scope, caixa, role_nome, db, current_user.id):
        raise HTTPException(status_code=403, detail="Abertura fora do escopo")
    cliente_est = _cliente_id_caixa(db, caixa)
    if cliente_est is None:
        raise HTTPException(status_code=400, detail="Empresa do caixa sem cliente vinculado")
    # Senha mestra: se estabelecimento exige, validar body.senha_mestra
    if _exige_senha_mestra(db, cliente_est):
        if not getattr(body, "senha_mestra", None) or not body.senha_mestra.strip():
            raise HTTPException(status_code=400, detail="Senha mestra é obrigatória para sangria/suprimento neste estabelecimento")
        chave = f"{CAIXA_SENHA_MESTRA_PREFIX}{cliente_est}"
        config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
        if config and config.valor:
            try:
                if not bcrypt.checkpw(body.senha_mestra.encode("utf-8"), config.valor.encode("utf-8")):
                    raise HTTPException(status_code=403, detail="Senha mestra inválida")
            except (ValueError, TypeError):
                raise HTTPException(status_code=403, detail="Senha mestra inválida")
    m = MovimentoCaixa(
        abertura_caixa_id=body.abertura_caixa_id,
        tipo=body.tipo,
        valor=body.valor,
        usuario_id=current_user.id,
        observacao=body.observacao,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    audit_action(
        db,
        f"caixa_{body.tipo}",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="movimento_caixa",
        recurso_id=m.id,
        detalhes=f"abertura_id={body.abertura_caixa_id} valor={body.valor} tipo={body.tipo}",
    )
    return MovimentoCaixaResponse.model_validate(m)


@router.get("/{movimento_id}", response_model=MovimentoCaixaResponse)
async def obter_movimento(
    movimento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para acessar movimentos de caixa")
    m = db.query(MovimentoCaixa).filter(MovimentoCaixa.id == movimento_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")
    ab = db.query(AberturaCaixa).filter(AberturaCaixa.id == m.abertura_caixa_id).first()
    if not ab:
        raise HTTPException(status_code=404, detail="Abertura de caixa não encontrada")
    caixa = db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_abertura(scope, caixa, role_nome, db, current_user.id):
        raise HTTPException(status_code=403, detail="Movimento fora do escopo")
    return MovimentoCaixaResponse.model_validate(m)
