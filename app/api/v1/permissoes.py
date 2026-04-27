"""
PDV Ibix - API de Permissões
Endpoints para gerenciamento de permissões do sistema RBAC
Acesso exclusivo para Administradores
"""

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.audit import audit_action
from ...core.middleware import forbid_cliente_access, require_superadmin
from ...database.connection import get_db
from ...models import Permissao, Role, RolePermissao, Usuario
from ...schemas.permissao import (
    PermissaoCreate,
    PermissaoListResponse,
    PermissaoResponse,
    PermissaoUpdate,
    PermissoesPorModuloResponse,
    RolePermissoesResponse,
    RolePermissoesUpdate,
)

ROLE_SUPERADMIN = "Superadministrador"

def _eh_superadmin(current_user: Usuario) -> bool:
    return bool(current_user.role and current_user.role.nome == ROLE_SUPERADMIN)

def _admin_nao_pode_role_superadmin(role: Role, current_user: Usuario) -> None:
    """Raises HTTP 403 if current user is Admin and role is Superadministrador."""
    if role.nome == ROLE_SUPERADMIN and not _eh_superadmin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a permissões desta role"
        )

router = APIRouter(
    prefix="/permissoes",
    tags=["Permissões"],
    dependencies=[Depends(forbid_cliente_access)]
)


@router.get("/", response_model=PermissaoListResponse)
async def listar_permissoes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    modulo: Optional[str] = None,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_superadmin())
):
    """
    Listar todas as permissões do sistema (apenas Superadministrador)
    
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Número máximo de registros a retornar
    - **modulo**: Filtrar por módulo específico
    - **ativo**: Filtrar por status (True/False)
    """
    query = db.query(Permissao)
    
    if modulo:
        query = query.filter(Permissao.modulo == modulo)
    
    if ativo is not None:
        query = query.filter(Permissao.ativo == ativo)
    
    total = query.count()
    permissoes = query.order_by(Permissao.modulo, Permissao.acao).offset(skip).limit(limit).all()
    
    # Contar permissões por módulo
    modulos_count = db.query(
        Permissao.modulo,
        func.count(Permissao.id).label('count')
    ).filter(Permissao.ativo == True).group_by(Permissao.modulo).all()
    
    modulos_dict = {modulo: count for modulo, count in modulos_count}
    
    return {
        "permissoes": permissoes,
        "total": total,
        "modulos": modulos_dict,
        "skip": skip,
        "limit": limit
    }


@router.get("/modulo/{modulo}", response_model=PermissoesPorModuloResponse)
async def listar_permissoes_por_modulo(
    modulo: str,
    role_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_superadmin())
):
    """
    Listar permissões de um módulo específico (apenas Superadministrador)
    
    - **modulo**: Nome do módulo (usuarios, clientes, etc)
    - **role_id**: Se fornecido, indica quais permissões estão selecionadas
    """
    permissoes = db.query(Permissao).filter(
        Permissao.modulo == modulo,
        Permissao.ativo == True
    ).order_by(Permissao.acao).all()
    
    if not permissoes:
        raise HTTPException(status_code=404, detail=f"Módulo '{modulo}' não encontrado")
    
    total_selecionadas = 0
    if role_id:
        # Contar quantas permissões deste módulo a role possui
        total_selecionadas = db.query(func.count(RolePermissao.id)).join(
            Permissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == role_id,
            Permissao.modulo == modulo
        ).scalar()
    
    return {
        "modulo": modulo,
        "permissoes": permissoes,
        "total": len(permissoes),
        "total_selecionadas": total_selecionadas
    }


@router.get("/{permissao_id}", response_model=PermissaoResponse)
async def obter_permissao(
    permissao_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_superadmin())
):
    """
    Obter uma permissão específica por ID (apenas Superadministrador)
    """
    permissao = db.query(Permissao).filter(Permissao.id == permissao_id).first()
    
    if not permissao:
        raise HTTPException(status_code=404, detail="Permissão não encontrada")
    
    return permissao


@router.post("/", response_model=PermissaoResponse, status_code=status.HTTP_201_CREATED)
async def criar_permissao(
    permissao: PermissaoCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_superadmin())
):
    """
    Criar uma nova permissão (apenas Superadministrador)
    
    **Nota:** Permissões geralmente são criadas via migração de banco de dados
    """
    # Verificar se já existe
    permissao_existente = db.query(Permissao).filter(Permissao.nome == permissao.nome).first()
    if permissao_existente:
        raise HTTPException(status_code=400, detail="Permissão com este nome já existe")
    
    db_permissao = Permissao(
        nome=permissao.nome,
        descricao=permissao.descricao,
        modulo=permissao.modulo,
        acao=permissao.acao,
        ativo=permissao.ativo
    )
    
    db.add(db_permissao)
    db.commit()
    db.refresh(db_permissao)
    
    return db_permissao


@router.put("/{permissao_id}", response_model=PermissaoResponse)
async def atualizar_permissao(
    permissao_id: int,
    permissao: PermissaoUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_superadmin())
):
    """
    Atualizar uma permissão existente (apenas Superadministrador)
    """
    db_permissao = db.query(Permissao).filter(Permissao.id == permissao_id).first()
    
    if not db_permissao:
        raise HTTPException(status_code=404, detail="Permissão não encontrada")
    
    # Atualizar campos fornecidos
    for key, value in permissao.dict(exclude_unset=True).items():
        setattr(db_permissao, key, value)
    
    db.commit()
    db.refresh(db_permissao)
    
    return db_permissao


@router.delete("/{permissao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_permissao(
    permissao_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_superadmin())
):
    """
    Excluir uma permissão (apenas Superadministrador)
    
    **Atenção:** Isso removerá a permissão de todas as roles
    """
    db_permissao = db.query(Permissao).filter(Permissao.id == permissao_id).first()
    
    if not db_permissao:
        raise HTTPException(status_code=404, detail="Permissão não encontrada")
    
    # Verificar se está sendo usada
    roles_usando = db.query(func.count(RolePermissao.id)).filter(
        RolePermissao.permissao_id == permissao_id
    ).scalar()
    
    if roles_usando > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Permissão está sendo usada por {roles_usando} role(s). Remova-a das roles primeiro."
        )
    
    db.delete(db_permissao)
    db.commit()
    
    return {"message": "Permissão excluída com sucesso"}


# ==================== ENDPOINTS DE ROLES E PERMISSÕES ====================

@router.get("/role/{role_id}", response_model=RolePermissoesResponse)
async def obter_permissoes_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin())
):
    """
    Obter todas as permissões de uma role específica (apenas Superadministrador).
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role não encontrada")
    _admin_nao_pode_role_superadmin(role, current_user)
    
    # Buscar permissões da role
    permissoes = db.query(Permissao).join(
        RolePermissao, Permissao.id == RolePermissao.permissao_id
    ).filter(
        RolePermissao.role_id == role_id,
        Permissao.ativo == True
    ).order_by(Permissao.modulo, Permissao.acao).all()
    
    permissoes_ids = [p.id for p in permissoes]
    
    return {
        "role_id": role.id,
        "role_nome": role.nome,
        "permissoes": permissoes,
        "total_permissoes": len(permissoes),
        "permissoes_ids": permissoes_ids
    }


@router.put("/role/{role_id}", response_model=Dict)
async def atualizar_permissoes_role(
    role_id: int,
    dados: RolePermissoesUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin())
):
    """
    Atualizar as permissões de uma role (apenas Superadministrador).
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role não encontrada")
    _admin_nao_pode_role_superadmin(role, current_user)
    
    # Validar que todas as permissões existem
    permissoes_validas = db.query(Permissao.id).filter(
        Permissao.id.in_(dados.permissoes_ids),
        Permissao.ativo == True
    ).all()
    
    permissoes_validas_ids = [p[0] for p in permissoes_validas]
    
    if len(permissoes_validas_ids) != len(dados.permissoes_ids):
        raise HTTPException(
            status_code=400,
            detail="Uma ou mais permissões fornecidas não existem ou estão inativas"
        )
    
    # Remover todas as permissões atuais da role
    db.query(RolePermissao).filter(RolePermissao.role_id == role_id).delete()
    
    # Adicionar novas permissões
    for permissao_id in dados.permissoes_ids:
        role_permissao = RolePermissao(
            role_id=role_id,
            permissao_id=permissao_id
        )
        db.add(role_permissao)
    
    db.commit()
    from app.core.middleware import PermissionCache
    from app.core.redis_cache import invalidate_permissions_for_role
    invalidate_permissions_for_role(role_id, db)
    PermissionCache.invalidate()
    audit_action(
        db,
        "permissoes_alteradas",
        user_id=current_user.id if hasattr(current_user, "id") else None,
        tenant_id=getattr(current_user, "tenant_id", None) if hasattr(current_user, "tenant_id") else None,
        recurso_tipo="role",
        recurso_id=role_id,
        detalhes=f"role_nome={role.nome} total={len(dados.permissoes_ids)}",
    )
    return {
        "message": "Permissões atualizadas com sucesso",
        "role_id": role_id,
        "role_nome": role.nome,
        "total_permissoes": len(dados.permissoes_ids),
        "permissoes_atualizadas": len(dados.permissoes_ids)
    }


@router.get("/agrupadas/modulos", response_model=Dict)
async def listar_permissoes_agrupadas(
    role_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin())
):
    """
    Listar todas as permissões agrupadas por módulo.
    Se role_id for fornecido, indica quais permissões estão selecionadas.
    Administrador não pode consultar seleção da role Superadministrador.
    """
    if role_id:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role:
            _admin_nao_pode_role_superadmin(role, current_user)
    # Buscar todas as permissões ativas
    permissoes = db.query(Permissao).filter(Permissao.ativo == True).order_by(
        Permissao.modulo, Permissao.acao
    ).all()
    
    # Agrupar por módulo
    permissoes_por_modulo = {}
    for permissao in permissoes:
        if permissao.modulo not in permissoes_por_modulo:
            permissoes_por_modulo[permissao.modulo] = []
        permissoes_por_modulo[permissao.modulo].append({
            "id": permissao.id,
            "nome": permissao.nome,
            "descricao": permissao.descricao,
            "acao": permissao.acao,
            "selecionada": False
        })
    
    # Se role_id for fornecido, marcar permissões selecionadas
    if role_id:
        permissoes_role = db.query(RolePermissao.permissao_id).filter(
            RolePermissao.role_id == role_id
        ).all()
        
        permissoes_role_ids = [p[0] for p in permissoes_role]
        
        for modulo in permissoes_por_modulo:
            for perm in permissoes_por_modulo[modulo]:
                perm["selecionada"] = perm["id"] in permissoes_role_ids
    
    return {
        "modulos": permissoes_por_modulo,
        "total_permissoes": len(permissoes),
        "total_modulos": len(permissoes_por_modulo)
    }

