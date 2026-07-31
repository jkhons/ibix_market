# PDV Ibix - Códigos de desconto + divulgadores (Fase 2)
"""CRUD codigos_desconto, divulgadores e regras. Criar/editar só Super Admin; listar/ver para Admin (filtrado)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from ...core.audit import audit_action
from ...core.middleware import get_current_user, require_superadmin, require_superadmin_or_admin
from ...core.scope import resolve_tenant_pagador
from ...database.connection import get_db
from ...models import Usuario
from ...models.codigo_desconto import CodigoDesconto
from ...models.divulgador import Divulgador
from ...models.divulgador_regra import DivulgadorRegra
from ...schemas.codigo_desconto import (
    CodigoDescontoCreate,
    CodigoDescontoResponse,
    CodigoDescontoUpdate,
    DivulgadorCreate,
    DivulgadorRegraCreate,
    DivulgadorRegraResponse,
    DivulgadorRegraUpdate,
    DivulgadorResponse,
    DivulgadorUpdate,
)
from ...services.codigo_desconto_lookup import buscar_codigo_desconto_ativo_por_entrada

router = APIRouter(tags=["Códigos de Desconto e Divulgadores"])


# ── Divulgadores ──────────────────────────────────────────────────────────────

def _is_administrador(current_user: Usuario) -> bool:
    return bool(current_user.role and current_user.role.nome == "Administrador")


@router.get("/divulgadores", response_model=List[DivulgadorResponse])
def listar_divulgadores(
    ativo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    q = db.query(Divulgador)
    if _is_administrador(current_user):
        q = q.filter(Divulgador.usuario_id == current_user.id)
    if ativo is not None:
        q = q.filter(Divulgador.ativo == ativo)
    return q.order_by(Divulgador.nome).all()


@router.post("/divulgadores", response_model=DivulgadorResponse, status_code=status.HTTP_201_CREATED)
def criar_divulgador(
    body: DivulgadorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    div = Divulgador(
        nome=body.nome,
        cpf_cnpj=body.cpf_cnpj,
        email=body.email,
        usuario_id=body.usuario_id,
        ativo=True,
    )
    db.add(div)
    db.commit()
    db.refresh(div)
    audit_action(
        db, "divulgador_criado",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="divulgador", recurso_id=div.id,
    )
    return div


@router.patch("/divulgadores/{div_id}", response_model=DivulgadorResponse)
def atualizar_divulgador(
    div_id: int,
    body: DivulgadorUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    div = db.query(Divulgador).filter(Divulgador.id == div_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Divulgador não encontrado")
    for field in ("nome", "cpf_cnpj", "email", "ativo", "usuario_id"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(div, field, val)
    db.commit()
    db.refresh(div)
    audit_action(
        db, "divulgador_atualizado",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="divulgador", recurso_id=div.id,
    )
    return div


# ── Regras de comissão ────────────────────────────────────────────────────────

@router.get("/divulgadores/{div_id}/regras", response_model=List[DivulgadorRegraResponse])
def listar_regras(
    div_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    div = db.query(Divulgador).filter(Divulgador.id == div_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Divulgador não encontrado")
    if _is_administrador(current_user) and div.usuario_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Divulgador não encontrado")
    return db.query(DivulgadorRegra).filter(DivulgadorRegra.divulgador_id == div_id).all()


@router.post("/divulgadores/{div_id}/regras", response_model=DivulgadorRegraResponse, status_code=status.HTTP_201_CREATED)
def criar_regra(
    div_id: int,
    body: DivulgadorRegraCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    if not db.query(Divulgador).filter(Divulgador.id == div_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Divulgador não encontrado")
    regra = DivulgadorRegra(
        divulgador_id=div_id,
        percentual_plano_ativo=body.percentual_plano_ativo,
        recebe_primeira_parcela=body.recebe_primeira_parcela,
        percentual_comissao=body.percentual_comissao,
    )
    db.add(regra)
    db.commit()
    db.refresh(regra)
    audit_action(
        db, "divulgador_regra_criada",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="divulgador_regra", recurso_id=regra.id,
    )
    return regra


@router.patch("/divulgadores/{div_id}/regras/{regra_id}", response_model=DivulgadorRegraResponse)
def atualizar_regra(
    div_id: int,
    regra_id: int,
    body: DivulgadorRegraUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    div = db.query(Divulgador).filter(Divulgador.id == div_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Divulgador não encontrado")
    regra = db.query(DivulgadorRegra).filter(
        DivulgadorRegra.id == regra_id,
        DivulgadorRegra.divulgador_id == div_id,
    ).first()
    if not regra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    for field in ("percentual_plano_ativo", "recebe_primeira_parcela", "percentual_comissao"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(regra, field, val)
    db.commit()
    db.refresh(regra)
    audit_action(
        db, "divulgador_regra_atualizada",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="divulgador_regra", recurso_id=regra.id,
    )
    return regra


# ── Códigos de desconto ──────────────────────────────────────────────────────

@router.get("/codigos-desconto", response_model=List[CodigoDescontoResponse])
def listar_codigos(
    ativo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    q = db.query(CodigoDesconto).options(
        joinedload(CodigoDesconto.divulgador).joinedload(Divulgador.usuario)
    )
    if _is_administrador(current_user):
        q = q.join(Divulgador, CodigoDesconto.divulgador_id == Divulgador.id).filter(
            Divulgador.usuario_id == current_user.id
        )
    if ativo is not None:
        q = q.filter(CodigoDesconto.ativo == ativo)
    codes = q.order_by(CodigoDesconto.codigo).all()
    result = []
    for c in codes:
        data = CodigoDescontoResponse.model_validate(c).model_dump()
        data["representante_nome"] = (
            c.divulgador.usuario.nome if c.divulgador and getattr(c.divulgador, "usuario", None) else None
        )
        result.append(CodigoDescontoResponse(**data))
    return result


@router.get("/codigos-desconto/validar/{codigo}", response_model=CodigoDescontoResponse)
def validar_codigo(
    codigo: str,
    db: Session = Depends(get_db),
):
    """Endpoint público: verifica se o código é válido e retorna dados. Usado no cadastro.
    Só considera válido se o código estiver ativo e vinculado a um representante (divulgador com usuario_id)."""
    cod = buscar_codigo_desconto_ativo_por_entrada(db, codigo)
    if not cod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código não encontrado ou expirado.")
    if not cod.divulgador_id or not cod.divulgador or not cod.divulgador.usuario_id or not cod.divulgador.usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código ativo, mas não vinculado a um representante. O administrador deve vincular o código a um Representante em Códigos de desconto.",
        )
    data = CodigoDescontoResponse.model_validate(cod).model_dump()
    data["representante_nome"] = cod.divulgador.usuario.nome if cod.divulgador.usuario else None
    return CodigoDescontoResponse(**data)

@router.get("/codigos-desconto/{codigo_id}", response_model=CodigoDescontoResponse)
def detalhe_codigo(
    codigo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    cod = db.query(CodigoDesconto).filter(CodigoDesconto.id == codigo_id).first()
    if not cod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código de desconto não encontrado")
    if _is_administrador(current_user):
        if not cod.divulgador_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código de desconto não encontrado")
        div = db.query(Divulgador).filter(Divulgador.id == cod.divulgador_id).first()
        if not div or div.usuario_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código de desconto não encontrado")
    return cod


@router.post("/codigos-desconto", response_model=CodigoDescontoResponse, status_code=status.HTTP_201_CREATED)
def criar_codigo(
    body: CodigoDescontoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    existing = db.query(CodigoDesconto).filter(CodigoDesconto.codigo == body.codigo).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Código já existe")

    div = None
    if body.representante_usuario_id is not None:
        admin_user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == body.representante_usuario_id).first()
        if not admin_user or not admin_user.role or admin_user.role.nome != "Administrador":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O representante deve ser um usuário com função Administrador.",
            )
        div = db.query(Divulgador).filter(Divulgador.usuario_id == body.representante_usuario_id).first()
        if not div:
            div = Divulgador(
                nome=f"Representante - {admin_user.nome}",
                usuario_id=admin_user.id,
                ativo=True,
            )
            db.add(div)
            db.flush()
    elif body.divulgador_id:
        div = db.query(Divulgador).filter(Divulgador.id == body.divulgador_id).first()
        if not div:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Divulgador não encontrado")
        if not div.usuario_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O divulgador deve estar vinculado a um Representante (Administrador). Edite o divulgador e selecione o Usuário Administrador.",
            )
        admin_user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == div.usuario_id).first()
        if not admin_user or not admin_user.role or admin_user.role.nome != "Administrador":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O divulgador deve estar vinculado a um usuário com função Administrador (Representante).",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o Representante (representante_usuario_id) ou um divulgador vinculado a um Representante (divulgador_id).",
        )

    cod = CodigoDesconto(
        codigo=body.codigo.upper().strip(),
        tipo_promocao=body.tipo_promocao,
        desconto_primeira_parcela_percent=body.desconto_primeira_parcela_percent,
        desconto_mensalidade_percent=body.desconto_mensalidade_percent,
        meses_desconto=body.meses_desconto,
        ativo=True,
        divulgador_id=div.id,
    )
    db.add(cod)
    db.commit()
    db.refresh(cod)
    audit_action(
        db, "codigo_desconto_criado",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="codigo_desconto", recurso_id=cod.id, detalhes=f"codigo={cod.codigo}",
    )
    return cod


def _resolver_divulgador_por_representante(db: Session, representante_usuario_id: int):
    """Encontra ou cria divulgador vinculado ao Representante (Administrador)."""
    admin_user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == representante_usuario_id).first()
    if not admin_user or not admin_user.role or admin_user.role.nome != "Administrador":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O representante deve ser um usuário com função Administrador.",
        )
    div = db.query(Divulgador).filter(Divulgador.usuario_id == representante_usuario_id).first()
    if not div:
        div = Divulgador(
            nome=f"Representante - {admin_user.nome}",
            usuario_id=admin_user.id,
            ativo=True,
        )
        db.add(div)
        db.flush()
    return div


@router.patch("/codigos-desconto/{codigo_id}", response_model=CodigoDescontoResponse)
def atualizar_codigo(
    codigo_id: int,
    body: CodigoDescontoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    cod = (
        db.query(CodigoDesconto)
        .options(joinedload(CodigoDesconto.divulgador).joinedload(Divulgador.usuario))
        .filter(CodigoDesconto.id == codigo_id)
        .first()
    )
    if not cod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código não encontrado")
    if getattr(body, "representante_usuario_id", None) is not None:
        div = _resolver_divulgador_por_representante(db, body.representante_usuario_id)
        cod.divulgador_id = div.id
    for field in ("tipo_promocao", "desconto_primeira_parcela_percent", "desconto_mensalidade_percent", "meses_desconto", "ativo", "divulgador_id"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(cod, field, val)
    db.commit()
    db.refresh(cod)
    audit_action(
        db, "codigo_desconto_atualizado",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="codigo_desconto", recurso_id=cod.id,
    )
    data = CodigoDescontoResponse.model_validate(cod).model_dump()
    data["representante_nome"] = (
        cod.divulgador.usuario.nome if cod.divulgador and getattr(cod.divulgador, "usuario", None) else None
    )
    return CodigoDescontoResponse(**data)
