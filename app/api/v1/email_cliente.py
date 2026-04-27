# PDV Ibix - API de configuração de e-mail por cliente (apenas Superadministrador)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

# Importar helpers de config (mesmo módulo que configuracoes usa)
from app.api.v1.configuracoes import get_configuracao, set_configuracao
from app.core.email_funcoes import chave_email_cliente_from, chave_email_cliente_from_name
from app.core.middleware import AuthMiddleware, require_permission
from app.core.scope import get_cliente_scope
from app.database.connection import get_db
from app.models.area_cliente import AreaCliente
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.usuario import Usuario

router = APIRouter(
    prefix="/email-cliente",
    tags=["E-mail por cliente"],
    dependencies=[
        Depends(AuthMiddleware.get_current_user),
        Depends(require_permission("email_cliente")),
    ],
)


class EmailClienteItemResponse(BaseModel):
    cliente_id: int
    nome: str
    from_email: str = ""
    from_name: str = ""


class EmailClienteListResponse(BaseModel):
    clientes: List[EmailClienteItemResponse]
    ativo: bool = False

    @field_validator("ativo", mode="before")
    @classmethod
    def ativo_never_none(cls, v):
        if v is None:
            return False
        return bool(v)


class EmailClienteGetResponse(BaseModel):
    cliente_id: int
    from_email: str = ""
    from_name: str = ""


class EmailClienteUpdate(BaseModel):
    from_email: Optional[str] = None
    from_name: Optional[str] = None


def _allowed_cliente_ids_para_email_cliente(scope, db: Session, current_user: Usuario) -> Optional[List[int]]:
    """
    Lista de cliente_id válidos para configuração de e-mail por cliente no contexto fiscal.
    - Superadministrador/Administrador: sem filtro (None).
    - Cliente Administrador: apenas clientes emissores (empresa fiscal), incluindo o próprio.
    """
    if scope.is_superadmin or scope.see_all:
        return None
    if not scope.allowed_ids:
        return []
    if not current_user.role or current_user.role.nome != "Cliente Administrador":
        return list(scope.allowed_ids)

    ids_empresa_fiscal = {
        r[0]
        for r in db.query(Empresa.cliente_id)
        .filter(
            Empresa.cliente_id.isnot(None),
            Empresa.cliente_id.in_(scope.allowed_ids),
        )
        .distinct()
        .all()
    }
    area_own = db.query(AreaCliente.cliente_id).filter(
        AreaCliente.usuario_id == current_user.id,
        AreaCliente.ativo == True,
        AreaCliente.nome_area == "administrador",
    ).first()

    ids = set(ids_empresa_fiscal)
    if area_own and area_own[0]:
        ids.add(area_own[0])
    result = [cid for cid in scope.allowed_ids if cid in ids]
    return result


def _scope_allows_cliente(scope, cliente_id: int, db: Session, current_user: Usuario) -> bool:
    """Retorna True se o usuário pode acessar o cliente_id (escopo)."""
    allowed = _allowed_cliente_ids_para_email_cliente(scope, db, current_user)
    if allowed is None:
        return True
    return cliente_id in allowed


def _get_scope(db: Session, current_user: Usuario):
    role_nome = current_user.role.nome if current_user.role else None
    return get_cliente_scope(db, current_user.id, role_nome, None)


@router.get("/", response_model=EmailClienteListResponse)
def listar_email_por_cliente(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Lista clientes do escopo do usuário com from_email/from_name. Cliente Admin = seus clientes; Admin/Superadmin = todos."""
    scope = _get_scope(db, current_user)
    # Flag global: se desativada, front pode esconder a seção (garantir bool para Pydantic)
    cfg_flag = get_configuracao(db, "email_separado_por_cliente_ativo")
    ativo = bool(cfg_flag and str(getattr(cfg_flag, "valor", "") or "").strip().lower() == "true")
    # Superadministrador sempre vê a seção ativa para poder configurar e ativar para os demais
    if scope.is_superadmin:
        ativo = True

    allowed = _allowed_cliente_ids_para_email_cliente(scope, db, current_user)
    if allowed is None:
        clientes_q = db.query(Cliente).order_by(Cliente.nome)
    else:
        if not allowed:
            return EmailClienteListResponse(clientes=[], ativo=bool(ativo))
        clientes_q = db.query(Cliente).filter(Cliente.id.in_(allowed)).order_by(Cliente.nome)

    clientes = clientes_q.all()
    result = []
    for c in clientes:
        cfg_from = get_configuracao(db, chave_email_cliente_from(c.id))
        cfg_name = get_configuracao(db, chave_email_cliente_from_name(c.id))
        result.append(
            EmailClienteItemResponse(
                cliente_id=c.id,
                nome=c.nome or "",
                from_email=(cfg_from.valor or "").strip() if cfg_from else "",
                from_name=(cfg_name.valor or "").strip() if cfg_name else "",
            )
        )
    # Garantir ativo sempre bool (evita ValidationError se cfg_flag/valor forem inesperados)
    return EmailClienteListResponse(clientes=result, ativo=bool(ativo))


@router.get("/{cliente_id}", response_model=EmailClienteGetResponse)
def obter_email_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Retorna from_email e from_name do cliente. Apenas clientes no escopo."""
    scope = _get_scope(db, current_user)
    if not _scope_allows_cliente(scope, cliente_id, db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cliente fora do seu escopo.")

    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")

    cfg_from = get_configuracao(db, chave_email_cliente_from(cliente_id))
    cfg_name = get_configuracao(db, chave_email_cliente_from_name(cliente_id))
    return EmailClienteGetResponse(
        cliente_id=cliente_id,
        from_email=(cfg_from.valor or "").strip() if cfg_from else "",
        from_name=(cfg_name.valor or "").strip() if cfg_name else "",
    )


@router.put("/{cliente_id}", response_model=EmailClienteGetResponse)
def salvar_email_cliente(
    cliente_id: int,
    payload: EmailClienteUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Salva from_email e from_name do cliente. Apenas clientes no escopo."""
    scope = _get_scope(db, current_user)
    if not _scope_allows_cliente(scope, cliente_id, db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cliente fora do seu escopo.")

    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")

    if payload.from_email is not None:
        set_configuracao(
            db,
            chave_email_cliente_from(cliente_id),
            payload.from_email.strip(),
            f"E-mail remetente do cliente {cliente_id}",
        )
    if payload.from_name is not None:
        set_configuracao(
            db,
            chave_email_cliente_from_name(cliente_id),
            payload.from_name.strip(),
            f"Nome remetente do cliente {cliente_id}",
        )
    cfg_from = get_configuracao(db, chave_email_cliente_from(cliente_id))
    cfg_name = get_configuracao(db, chave_email_cliente_from_name(cliente_id))
    return EmailClienteGetResponse(
        cliente_id=cliente_id,
        from_email=(cfg_from.valor or "").strip() if cfg_from else "",
        from_name=(cfg_name.valor or "").strip() if cfg_name else "",
    )
