# PDV Ibix - API Minha equipe (Saas.md Fase 6.2)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.audit import audit_action
from ...core.auth import AuthConfig
from ...core.middleware import AuthMiddleware, get_cliente_scope_dep, require_cliente_administrador
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import (
    AreaCliente,
    ClienteAdministradorCliente,
    ClienteAdministradorTecnico,
    Role,
    Usuario,
)
from ...schemas.cliente import ClienteCreate, ClienteResponse
from ...schemas.minha_equipe import SubClienteUsuarioCreate, VincularTecnicoRequest
from ...services.cliente_service import ClienteService

router = APIRouter(
    prefix="/minha-equipe",
    tags=["Minha equipe"],
    dependencies=[Depends(require_cliente_administrador())],
)


def _scope_allows_cliente(scope: ClienteScope, cliente_id: int) -> bool:
    if scope.is_superadmin or scope.see_all:
        return True
    return cliente_id in scope.allowed_ids


@router.post("/clientes", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
async def criar_sub_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Cria um sub-cliente e vincula ao Cliente Administrador atual."""
    cliente = ClienteService.criar_cliente(db, cliente_data)
    db.add(ClienteAdministradorCliente(usuario_id=current_user.id, cliente_id=cliente.id))
    db.commit()
    db.refresh(cliente)
    audit_action(
        db,
        "sub_cliente_criado",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="cliente",
        recurso_id=cliente.id,
        detalhes=f"minha_equipe cliente_id={cliente.id}",
    )
    return ClienteResponse(
        id=cliente.id,
        nome=cliente.nome,
        cnpj=cliente.cnpj,
        cep=cliente.cep,
        endereco=cliente.endereco,
        cidade=cliente.cidade,
        uf=cliente.uf,
        contato=cliente.contato,
        telefone=cliente.telefone,
        email=cliente.email,
        created_at=cliente.created_at.isoformat() if cliente.created_at else None,
        updated_at=cliente.updated_at.isoformat() if cliente.updated_at else None,
    )


@router.get("/clientes/{cliente_id}/usuarios")
async def listar_usuarios_sub_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista usuários (role Subcliente) vinculados ao cliente via AreaCliente. Só se cliente no escopo."""
    if not _scope_allows_cliente(scope, cliente_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cliente fora do seu escopo")
    rows = (
        db.query(Usuario.id, Usuario.nome, Usuario.email, Usuario.cargo)
        .join(AreaCliente, AreaCliente.usuario_id == Usuario.id)
        .filter(AreaCliente.cliente_id == cliente_id, AreaCliente.ativo == True)
        .all()
    )
    return [
        {"id": r.id, "nome": r.nome, "email": r.email, "cargo": r.cargo or "Subcliente"}
        for r in rows
    ]


@router.post("/clientes/{cliente_id}/usuarios", status_code=status.HTTP_201_CREATED)
async def adicionar_usuario_sub_cliente(
    cliente_id: int,
    body: SubClienteUsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria usuário com role Subcliente e vincula ao cliente (AreaCliente). Só se cliente no escopo."""
    if not _scope_allows_cliente(scope, cliente_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cliente fora do seu escopo")
    existing = db.query(Usuario).filter(Usuario.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")
    role_subcliente = db.query(Role).filter(Role.nome == "Subcliente").first()
    if not role_subcliente:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Role Subcliente não configurada",
        )
    senha_hash = AuthConfig.get_password_hash(body.senha)
    user = Usuario(
        nome=body.nome,
        email=body.email,
        senha_hash=senha_hash,
        cargo="Subcliente",
        role_id=role_subcliente.id,
        ativo=True,
    )
    db.add(user)
    db.flush()
    db.add(AreaCliente(usuario_id=user.id, cliente_id=cliente_id, nome_area="padrao", ativo=True))
    db.commit()
    db.refresh(user)
    audit_action(
        db,
        "usuario_sub_cliente_criado",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="usuario",
        recurso_id=user.id,
        detalhes=f"cliente_id={cliente_id} email={user.email}",
    )
    return {"id": user.id, "nome": user.nome, "email": user.email}


@router.get("/tecnicos")
async def listar_tecnicos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Lista técnicos vinculados ao Cliente Administrador atual."""
    role_tecnico = db.query(Role).filter(Role.nome == "Técnico").first()
    if not role_tecnico:
        return []
    ids = [
        r.usuario_id_tecnico
        for r in db.query(ClienteAdministradorTecnico).filter(
            ClienteAdministradorTecnico.usuario_id_cliente_admin == current_user.id
        ).all()
    ]
    if not ids:
        return []
    usuarios = (
        db.query(Usuario)
        .filter(Usuario.id.in_(ids), Usuario.role_id == role_tecnico.id)
        .all()
    )
    return [
        {"id": u.id, "nome": u.nome, "email": u.email, "ativo": u.ativo}
        for u in usuarios
    ]


@router.get("/tecnicos/disponiveis")
async def listar_tecnicos_disponiveis(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Para Cliente Administrador: não expõe lista de técnicos de fora da sua organização.
    Retorna lista vazia; o vínculo é feito apenas por email (backend valida se o técnico já pertence a outra equipe)."""
    # Cliente Administrador só vê técnicos da sua organização (já vinculados em GET /tecnicos).
    # Não retornamos lista de "técnicos livres" para evitar que ele veja técnicos de fora da sua organização.
    return []


@router.post("/tecnicos", status_code=status.HTTP_201_CREATED)
async def vincular_tecnico(
    body: VincularTecnicoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Vincula um técnico à equipe do Cliente Administrador (ClienteAdministradorTecnico).
    Se o usuário não existir, cria automaticamente com role Técnico (exige nome e senha).
    Lugar e função distintos do modal em /clientes (que cria Subcliente via AreaCliente)."""
    if not body.email and body.usuario_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe email ou usuario_id",
        )
    role_tecnico = db.query(Role).filter(Role.nome == "Técnico").first()
    if not role_tecnico:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Role Técnico não configurada",
        )
    if body.usuario_id is not None:
        tecnico = db.query(Usuario).filter(Usuario.id == body.usuario_id).first()
    else:
        tecnico = db.query(Usuario).filter(Usuario.email == body.email).first()

    if not tecnico:
        if body.usuario_id is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        # Criar automaticamente usuário com role Técnico e vincular ao Cliente Administrador
        if not body.nome or not body.senha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário não encontrado. Para cadastrar novo técnico, informe nome e senha.",
            )
        senha_hash = AuthConfig.get_password_hash(body.senha)
        tecnico = Usuario(
            nome=body.nome,
            email=body.email,
            senha_hash=senha_hash,
            cargo="Técnico",
            role_id=role_tecnico.id,
            ativo=True,
        )
        db.add(tecnico)
        db.flush()
    else:
        if tecnico.role_id != role_tecnico.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este email já está cadastrado com outra função. Apenas usuários com função Técnico podem ser vinculados.",
            )
    # Técnico só pode pertencer a um Cliente Administrador: não permitir vincular se já estiver em outra equipe
    vinculo_outro_ca = (
        db.query(ClienteAdministradorTecnico)
        .filter(ClienteAdministradorTecnico.usuario_id_tecnico == tecnico.id)
        .filter(ClienteAdministradorTecnico.usuario_id_cliente_admin != current_user.id)
        .first()
    )
    if vinculo_outro_ca:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este técnico já está vinculado a outro Cliente Administrador. Só é possível vincular técnicos que ainda não pertencem a outra equipe.",
        )
    existing = (
        db.query(ClienteAdministradorTecnico)
        .filter(
            ClienteAdministradorTecnico.usuario_id_cliente_admin == current_user.id,
            ClienteAdministradorTecnico.usuario_id_tecnico == tecnico.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Técnico já vinculado à sua equipe")
    db.add(
        ClienteAdministradorTecnico(
            usuario_id_cliente_admin=current_user.id,
            usuario_id_tecnico=tecnico.id,
        )
    )
    db.commit()
    audit_action(
        db,
        "tecnico_vinculado",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="usuario",
        recurso_id=tecnico.id,
        detalhes=f"tecnico_id={tecnico.id}",
    )
    return {"id": tecnico.id, "nome": tecnico.nome, "email": tecnico.email}


@router.delete("/tecnicos/{usuario_id_tecnico}", status_code=status.HTTP_204_NO_CONTENT)
async def desvincular_tecnico(
    usuario_id_tecnico: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Remove vínculo do técnico com o Cliente Administrador."""
    v = (
        db.query(ClienteAdministradorTecnico)
        .filter(
            ClienteAdministradorTecnico.usuario_id_cliente_admin == current_user.id,
            ClienteAdministradorTecnico.usuario_id_tecnico == usuario_id_tecnico,
        )
        .first()
    )
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vínculo não encontrado")
    db.delete(v)
    db.commit()
    audit_action(
        db,
        "tecnico_desvinculado",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="usuario",
        recurso_id=usuario_id_tecnico,
        detalhes="minha_equipe",
    )
