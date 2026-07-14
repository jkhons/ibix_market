# PDV Ibix - API de Usuários
# Enforcement por permissão granular (usuarios:visualizar, usuarios:criar, etc.) e escopo para Administrador
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.audit import audit_action
from app.core.auth import AuthConfig
from app.core.db_errors import is_unique_violation
from app.core.logging import log_error
from app.core.middleware import require_permission, require_superadmin, require_superadmin_or_admin
from app.core.pii import apply_usuario_pii_mask, mask_email
from app.core.pii_access import audit_pii_access, user_can_view_pii
from app.database.connection import get_db
from app.models.administrador_cliente import AdministradorCliente
from app.models.administrador_cliente_administrador import AdministradorClienteAdministrador
from app.models.area_cliente import AreaCliente
from app.models.cliente_administrador_cliente import ClienteAdministradorCliente
from app.models.cliente_administrador_tecnico import ClienteAdministradorTecnico
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.schemas.usuario import (
    RepresentanteListResponse,
    UsuarioCreate,
    UsuarioListResponse,
    UsuarioResponse,
    UsuarioUpdate,
)
from app.services.brand_scope_service import (
    assert_usuario_in_admin_brand_scope,
    brand_scope_meta,
    filter_user_ids_by_admin_brand,
    filter_usuario_query_by_admin_brand,
    resolve_admin_brand_scope,
    tenant_ids_for_admin_brand,
)

# Roles que o Cliente Administrador pode atribuir: Técnico, Subcliente e Contador (Contador já fica vinculado a ele)
ROLES_PERMITIDAS_CLIENTE_ADMIN: Tuple[str, ...] = ("Técnico", "Subcliente", "Contador")


class ClientesVinculadosBody(BaseModel):
    """Body para PUT clientes-vinculados (Saas.md - UI Administrador)"""
    cliente_ids: List[int] = []


def _allowed_user_ids_for_admin(db: Session, admin_user_id: int) -> List[int]:
    """IDs de usuários que o Administrador pode ver: ele mesmo + Cliente Administradores vinculados a ele."""
    rows = db.query(AdministradorClienteAdministrador.usuario_id_cliente_administrador).filter(
        AdministradorClienteAdministrador.usuario_id_administrador == admin_user_id
    ).all()
    ids = [admin_user_id] + [r[0] for r in rows]
    return ids


def _allowed_user_ids_for_cliente_admin(db: Session, client_admin_user_id: int) -> List[int]:
    """IDs de usuários que o Cliente Administrador pode ver: ele mesmo + técnicos da equipe + Contadores vinculados a ele."""
    rows = db.query(ClienteAdministradorTecnico.usuario_id_tecnico).filter(
        ClienteAdministradorTecnico.usuario_id_cliente_admin == client_admin_user_id
    ).all()
    contador_rows = db.query(Usuario.id).filter(
        Usuario.contador_vinculado_cliente_administrador_id == client_admin_user_id
    ).all()
    contador_ids = [r[0] for r in contador_rows]
    ids = [client_admin_user_id] + [r[0] for r in rows] + list(contador_ids)
    return list(dict.fromkeys(ids))  # sem duplicatas


def _role_permitida_para_cliente_admin(db: Session, role_id: int) -> bool:
    """Retorna True se a role_id é permitida para Cliente Administrador (Técnico, Subcliente ou Contador)."""
    role = db.query(Role).filter(Role.id == role_id).first()
    return role is not None and role.nome in ROLES_PERMITIDAS_CLIENTE_ADMIN


def _role_nome_by_id(db: Session, role_id: int) -> Optional[str]:
    """Retorna o nome da role pelo id."""
    role = db.query(Role).filter(Role.id == role_id).first()
    return role.nome if role else None


def _vinculo_cliente_administrador(db: Session, usuario: Usuario) -> Tuple[Optional[int], Optional[str]]:
    """
    Para usuário com role Técnico ou Subcliente, retorna (id, nome) do Cliente Administrador
    ao qual está vinculado. Caso contrário retorna (None, None).
    - Técnico: vínculo em cliente_administrador_tecnicos (usuario_id_tecnico -> usuario_id_cliente_admin).
    - Subcliente: vínculo via AreaCliente (usuario_id -> cliente_id) e ClienteAdministradorCliente (cliente_id -> usuario_id CA).
    """
    role_nome = None
    if usuario.role and getattr(usuario.role, "nome", None):
        role_nome = usuario.role.nome
    elif usuario.role_id:
        role_nome = _role_nome_by_id(db, usuario.role_id)
    if not role_nome or role_nome not in ("Técnico", "Subcliente"):
        return None, None
    if role_nome == "Técnico":
        row = (
            db.query(ClienteAdministradorTecnico.usuario_id_cliente_admin)
            .filter(ClienteAdministradorTecnico.usuario_id_tecnico == usuario.id)
            .first()
        )
        if not row:
            return None, None
        ca = db.query(Usuario).filter(Usuario.id == row[0]).first()
        return (row[0], ca.nome if ca else None)
    # Subcliente: AreaCliente.usuario_id -> cliente_id; depois ClienteAdministradorCliente.cliente_id -> usuario_id (CA)
    ac = (
        db.query(AreaCliente.cliente_id)
        .filter(AreaCliente.usuario_id == usuario.id, AreaCliente.ativo == True)
        .first()
    )
    if not ac:
        return None, None
    cac = (
        db.query(ClienteAdministradorCliente.usuario_id)
        .filter(ClienteAdministradorCliente.cliente_id == ac[0])
        .first()
    )
    if not cac:
        return None, None
    ca = db.query(Usuario).filter(Usuario.id == cac[0]).first()
    return (cac[0], ca.nome if ca else None)


usuarios_router = APIRouter(
    prefix="/usuarios",
    dependencies=[Depends(require_superadmin_or_admin)]
)

def _usuario_payload(usuario: Usuario, db: Session, current_user: Usuario, *, reveal: Optional[bool] = None) -> dict:
    is_superadmin = current_user.role and current_user.role.nome == "Superadministrador"
    payload = {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "cargo": usuario.cargo or "",
        "ativo": usuario.ativo,
        "cpf": getattr(usuario, "cpf", None),
        "rg": getattr(usuario, "rg", None),
        "documento_path": getattr(usuario, "documento_path", None),
        "role_id": usuario.role_id,
        "role": usuario.role,
        "contador_vinculado_cliente_administrador_id": getattr(
            usuario, "contador_vinculado_cliente_administrador_id", None
        ),
        "created_at": usuario.created_at,
        "updated_at": usuario.updated_at,
        "vinculo_cliente_administrador_id": getattr(usuario, "vinculo_cliente_administrador_id", None),
        "vinculo_cliente_administrador_nome": getattr(usuario, "vinculo_cliente_administrador_nome", None),
    }
    if is_superadmin:
        ca_id, ca_nome = _vinculo_cliente_administrador(db, usuario)
        payload["vinculo_cliente_administrador_id"] = ca_id
        payload["vinculo_cliente_administrador_nome"] = ca_nome
    if reveal is None:
        reveal = user_can_view_pii(db, current_user)
    return apply_usuario_pii_mask(payload, reveal=reveal)


def _admin_role_id(db: Session) -> Optional[int]:
    row = db.query(Role.id).filter(Role.nome == "Administrador", Role.ativo.is_(True)).first()
    return int(row[0]) if row else None


def _scoped_usuarios_query(
    db: Session,
    current_user: Usuario,
    effective_brand: Optional[int],
):
    """Query base de Usuario com o mesmo escopo de listar_usuarios."""
    role_nome = current_user.role.nome if current_user.role else None
    query = db.query(Usuario)
    if role_nome == "Superadministrador":
        query, force_empty = filter_usuario_query_by_admin_brand(query, effective_brand, db)
        if force_empty:
            return query, True
    elif role_nome == "Administrador":
        allowed_ids = _allowed_user_ids_for_admin(db, current_user.id)
        if effective_brand is not None:
            allowed_ids = filter_user_ids_by_admin_brand(db, allowed_ids, effective_brand)
            if not allowed_ids:
                return query, True
        query = query.filter(Usuario.id.in_(allowed_ids))
    elif role_nome == "Cliente Administrador":
        allowed_ids = _allowed_user_ids_for_cliente_admin(db, current_user.id)
        if effective_brand is not None:
            allowed_ids = filter_user_ids_by_admin_brand(db, allowed_ids, effective_brand)
            if not allowed_ids:
                return query, True
        query = query.filter(Usuario.id.in_(allowed_ids))
    else:
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito a Superadministrador, Administrador ou Cliente Administrador com escopo",
        )
    return query, False


@usuarios_router.get("/representantes", response_model=RepresentanteListResponse)
def listar_representantes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("usuarios:visualizar")),
):
    """Lista leve de Administradores para o card Representantes (sem serialização pesada)."""
    effective_brand = resolve_admin_brand_scope(request, db)
    admin_role_id = _admin_role_id(db)
    if not admin_role_id:
        return {"representantes": [], "total": 0}
    if current_user.role and current_user.role.nome == "Superadministrador" and effective_brand is not None:
        if not tenant_ids_for_admin_brand(db, effective_brand):
            return {"representantes": [], "total": 0}

    query, force_empty = _scoped_usuarios_query(db, current_user, effective_brand)
    if force_empty:
        return {"representantes": [], "total": 0}

    rows = (
        query.filter(Usuario.role_id == admin_role_id)
        .with_entities(Usuario.id, Usuario.nome, Usuario.email, Usuario.ativo)
        .order_by(Usuario.nome.asc())
        .limit(100)
        .all()
    )
    reveal_pii = user_can_view_pii(db, current_user)
    representantes = []
    for uid, nome, email, ativo in rows:
        email_out = email if reveal_pii else mask_email(email)
        representantes.append(
            {
                "id": uid,
                "nome": nome or "",
                "email": email_out or "",
                "ativo": bool(ativo),
            }
        )
    return {"representantes": representantes, "total": len(representantes)}


@usuarios_router.get("/", response_model=UsuarioListResponse)
def listar_usuarios(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    ativo: Optional[bool] = None,
    nome: Optional[str] = Query(None, description="Filtrar por nome (contém)"),
    role_id: Optional[int] = Query(None, description="Filtrar por função (role_id)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("usuarios:visualizar")),
):
    """Listar usuários. Superadmin: todos (ou só da marca no host derivado). Administrador/CA: escopo + marca."""
    effective_brand = resolve_admin_brand_scope(request, db)
    brand_scope = brand_scope_meta(request, db, effective_brand)
    empty_payload = {"usuarios": [], "total": 0, "skip": skip, "limit": limit, "brand_scope": brand_scope}

    role_nome = current_user.role.nome if current_user.role else None
    if role_nome == "Superadministrador" and effective_brand is not None:
        if not tenant_ids_for_admin_brand(db, effective_brand):
            return empty_payload

    scoped, force_empty = _scoped_usuarios_query(db, current_user, effective_brand)
    if force_empty:
        return empty_payload

    query = scoped.options(joinedload(Usuario.role))
    if ativo is not None:
        query = query.filter(Usuario.ativo == ativo)
    if nome:
        query = query.filter(Usuario.nome.ilike(f"%{nome}%"))
    if role_id is not None:
        query = query.filter(Usuario.role_id == role_id)
    total = query.count()
    usuarios = query.offset(skip).limit(limit).all()
    reveal_pii = user_can_view_pii(db, current_user)
    serialized = [
        UsuarioResponse.model_validate(_usuario_payload(u, db, current_user, reveal=reveal_pii))
        for u in usuarios
    ]
    return {"usuarios": serialized, "total": total, "skip": skip, "limit": limit, "brand_scope": brand_scope}

@usuarios_router.get("/{usuario_id}", response_model=UsuarioResponse)
def obter_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("usuarios:visualizar")),
):
    """Obter usuário por ID. Administrador/Cliente Administrador só podem ver usuários no seu escopo."""
    usuario = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if current_user.role and current_user.role.nome == "Administrador":
        allowed = _allowed_user_ids_for_admin(db, current_user.id)
        if usuario_id not in allowed:
            raise HTTPException(status_code=403, detail="Usuário fora do seu escopo")
    elif current_user.role and current_user.role.nome == "Cliente Administrador":
        allowed = _allowed_user_ids_for_cliente_admin(db, current_user.id)
        if usuario_id not in allowed:
            raise HTTPException(status_code=403, detail="Usuário fora do seu escopo")
    elif current_user.role and current_user.role.nome == "Superadministrador":
        assert_usuario_in_admin_brand_scope(db, usuario, request)
    if current_user.role and current_user.role.nome == "Superadministrador":
        ca_id, ca_nome = _vinculo_cliente_administrador(db, usuario)
        setattr(usuario, "vinculo_cliente_administrador_id", ca_id)
        setattr(usuario, "vinculo_cliente_administrador_nome", ca_nome)
    if user_can_view_pii(db, current_user):
        from app.core.rate_limiter import get_client_ip

        audit_pii_access(
            db,
            acao="pii_acesso_usuario",
            actor=current_user,
            recurso_tipo="usuario",
            recurso_id=usuario_id,
            ip=get_client_ip(request),
            request_id=getattr(request.state, "request_id", None),
        )
    return UsuarioResponse.model_validate(_usuario_payload(usuario, db, current_user))

@usuarios_router.post("/", response_model=UsuarioResponse)
def criar_usuario(
    request: Request,
    usuario: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("usuarios:criar")),
):
    """Criar novo usuário. Exige usuarios:criar. Cliente Administrador só pode criar Técnico, Subcliente ou Contador (Contador já fica vinculado a ele)."""
    try:
        # Cliente Administrador só pode criar usuários da sua hierarquia (Técnico, Subcliente, Contador)
        if current_user.role and current_user.role.nome == "Cliente Administrador":
            if not _role_permitida_para_cliente_admin(db, usuario.role_id):
                raise HTTPException(
                    status_code=403,
                    detail="Cliente Administrador só pode criar usuários com função Técnico, Subcliente ou Contador."
                )
        # Verificar se email já existe
        usuario_existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
        if usuario_existente:
            raise HTTPException(status_code=400, detail="Email já está em uso")
        
        # Criar hash da senha
        senha_hash = AuthConfig.get_password_hash(usuario.senha)
        
        # Se Cliente Administrador está criando um Contador, vincular ao próprio CA (Contador só vê dados desse CA)
        contador_vinculado_ca_id = None
        if current_user.role and current_user.role.nome == "Cliente Administrador":
            if _role_nome_by_id(db, usuario.role_id) == "Contador":
                contador_vinculado_ca_id = current_user.id

        # Criar usuário
        db_usuario = Usuario(
            nome=usuario.nome,
            email=usuario.email,
            senha_hash=senha_hash,
            cargo=usuario.cargo if usuario.cargo else "Usuário",
            ativo=usuario.ativo,
            role_id=usuario.role_id,
            contador_vinculado_cliente_administrador_id=contador_vinculado_ca_id,
            cpf=getattr(usuario, "cpf", None),
            rg=getattr(usuario, "rg", None),
            documento_path=getattr(usuario, "documento_path", None),
        )
        
        db.add(db_usuario)
        db.commit()
        db.refresh(db_usuario)
        # Recarregar com role para a resposta serializar corretamente
        db_usuario = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == db_usuario.id).first()
        return db_usuario

    except IntegrityError as e:
        db.rollback()
        if is_unique_violation(e):
            raise HTTPException(status_code=400, detail="Email já está em uso")
        raise HTTPException(status_code=400, detail="Erro de integridade do banco de dados")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        log_error("criar_usuario", exc_info=e)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@usuarios_router.put("/{usuario_id}", response_model=UsuarioResponse)
def atualizar_usuario(
    usuario_id: int,
    request: Request,
    usuario: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("usuarios:editar")),
):
    """Atualizar usuário existente. Exige usuarios:editar. Administrador só pode editar usuários no seu escopo."""
    try:
        db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not db_usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        if current_user.role and current_user.role.nome == "Administrador":
            allowed = _allowed_user_ids_for_admin(db, current_user.id)
            if usuario_id not in allowed:
                raise HTTPException(status_code=403, detail="Usuário fora do seu escopo")
        elif current_user.role and current_user.role.nome == "Cliente Administrador":
            allowed = _allowed_user_ids_for_cliente_admin(db, current_user.id)
            if usuario_id not in allowed:
                raise HTTPException(status_code=403, detail="Usuário fora do seu escopo")
            # Cliente Administrador não pode atribuir role Administrador ou Superadministrador
            if usuario.role_id is not None and usuario.role_id != db_usuario.role_id:
                if not _role_permitida_para_cliente_admin(db, usuario.role_id):
                    raise HTTPException(
                        status_code=403,
                        detail="Cliente Administrador só pode atribuir função Técnico, Subcliente ou Contador."
                    )
        elif current_user.role and current_user.role.nome == "Superadministrador":
            assert_usuario_in_admin_brand_scope(db, db_usuario, request)
        
        # Verificar se email já existe (exceto para o usuário atual)
        if usuario.email and usuario.email != db_usuario.email:
            usuario_existente = db.query(Usuario).filter(
                Usuario.email == usuario.email,
                Usuario.id != usuario_id
            ).first()
            if usuario_existente:
                raise HTTPException(status_code=400, detail="Email já está em uso")
        
        # Atualizar campos
        if usuario.nome:
            db_usuario.nome = usuario.nome
        if usuario.email:
            db_usuario.email = usuario.email
        if usuario.cargo:
            db_usuario.cargo = usuario.cargo
        dump = usuario.model_dump(exclude_unset=True)
        pii_fields = {"cpf", "rg", "documento_path"}
        if pii_fields.intersection(dump.keys()) and not user_can_view_pii(db, current_user):
            raise HTTPException(
                status_code=403,
                detail="Permissão necessária para alterar dados pessoais (PII): pii:visualizar",
            )
        if "cpf" in dump:
            db_usuario.cpf = usuario.cpf
        if "rg" in dump:
            db_usuario.rg = usuario.rg
        if "documento_path" in dump:
            db_usuario.documento_path = usuario.documento_path
        if pii_fields.intersection(dump.keys()):
            audit_pii_access(
                db,
                acao="pii_alteracao_usuario",
                actor=current_user,
                recurso_tipo="usuario",
                recurso_id=usuario_id,
                detalhes=f"campos={','.join(sorted(pii_fields.intersection(dump.keys())))}",
            )
        if usuario.ativo is not None:
            db_usuario.ativo = usuario.ativo
        if usuario.role_id is not None:
            if db_usuario.role_id != usuario.role_id:
                audit_action(
                    db,
                    "role_alterada",
                    user_id=current_user.id,
                    tenant_id=getattr(current_user, "tenant_id", None),
                    recurso_tipo="usuario",
                    recurso_id=usuario_id,
                    detalhes=f"role_id={usuario.role_id}",
                )
                from app.core.middleware import PermissionCache
                from app.core.redis_cache import invalidate_permissions
                invalidate_permissions(usuario_id)
                PermissionCache.invalidate(usuario_id)
            db_usuario.role_id = usuario.role_id
        # Contador: vínculo ao Cliente Administrador (CA que edita impõe o próprio id; Superadmin/Admin podem setar)
        if current_user.role and current_user.role.nome == "Cliente Administrador":
            role_final_id = usuario.role_id if usuario.role_id is not None else db_usuario.role_id
            if _role_nome_by_id(db, role_final_id) == "Contador":
                db_usuario.contador_vinculado_cliente_administrador_id = current_user.id
        elif "contador_vinculado_cliente_administrador_id" in usuario.model_dump(exclude_unset=True):
            db_usuario.contador_vinculado_cliente_administrador_id = usuario.contador_vinculado_cliente_administrador_id

        # Atualizar senha se fornecida
        if usuario.senha:
            db_usuario.senha_hash = AuthConfig.get_password_hash(usuario.senha)
        
        db.commit()
        db.refresh(db_usuario)
        db_usuario = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == usuario_id).first()
        return db_usuario

    except IntegrityError as e:
        db.rollback()
        if is_unique_violation(e):
            raise HTTPException(status_code=400, detail="Email já está em uso")
        raise HTTPException(status_code=400, detail="Erro de integridade do banco de dados")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        log_error("atualizar_usuario", exc_info=e)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@usuarios_router.get("/{usuario_id}/clientes-vinculados")
def get_clientes_vinculados(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    """Retorna cliente_ids que o Administrador pode acessar. Apenas Superadmin. (Saas.md)"""
    usuario = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    assert_usuario_in_admin_brand_scope(db, usuario, request)
    if not usuario.role or usuario.role.nome != "Administrador":
        return {"cliente_ids": []}
    rows = db.query(AdministradorCliente.cliente_id).filter(
        AdministradorCliente.usuario_id == usuario_id
    ).all()
    return {"cliente_ids": [r[0] for r in rows]}


@usuarios_router.put("/{usuario_id}/clientes-vinculados")
def put_clientes_vinculados(
    usuario_id: int,
    request: Request,
    body: ClientesVinculadosBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Define clientes que o Administrador pode acessar. Apenas Superadmin. (Saas.md)"""
    usuario = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    assert_usuario_in_admin_brand_scope(db, usuario, request)
    if not usuario.role or usuario.role.nome != "Administrador":
        raise HTTPException(status_code=400, detail="Só é possível definir clientes para usuários com role Administrador")
    db.query(AdministradorCliente).filter(AdministradorCliente.usuario_id == usuario_id).delete()
    for cid in body.cliente_ids:
        db.add(AdministradorCliente(usuario_id=usuario_id, cliente_id=cid))
    db.commit()
    audit_action(
        db,
        "admin_clientes_alterados",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="usuario",
        recurso_id=usuario_id,
        detalhes=f"cliente_ids={body.cliente_ids}",
    )
    return {"cliente_ids": body.cliente_ids}


@usuarios_router.delete("/{usuario_id}")
def excluir_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("usuarios:excluir")),
):
    """Excluir usuário. Exige usuarios:excluir. Administrador só pode excluir usuários no seu escopo."""
    try:
        db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not db_usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        if current_user.role and current_user.role.nome == "Administrador":
            allowed = _allowed_user_ids_for_admin(db, current_user.id)
            if usuario_id not in allowed:
                raise HTTPException(status_code=403, detail="Usuário fora do seu escopo")
        elif current_user.role and current_user.role.nome == "Cliente Administrador":
            allowed = _allowed_user_ids_for_cliente_admin(db, current_user.id)
            if usuario_id not in allowed:
                raise HTTPException(status_code=403, detail="Usuário fora do seu escopo")
        elif current_user.role and current_user.role.nome == "Superadministrador":
            assert_usuario_in_admin_brand_scope(db, db_usuario, request)
        
        # Verificar se usuário tem relacionamentos (opcional)
        # Pode ser implementado para evitar exclusão de usuários com dados relacionados
        audit_action(
            db,
            "usuario_excluido",
            user_id=current_user.id,
            tenant_id=getattr(current_user, "tenant_id", None),
            recurso_tipo="usuario",
            recurso_id=usuario_id,
        )
        db.delete(db_usuario)
        db.commit()
        
        return {"message": "Usuário excluído com sucesso"}

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir este usuário porque existem registros vinculados a ele."
        )
    except Exception as e:
        db.rollback()
        log_error("excluir_usuario", exc_info=e)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")