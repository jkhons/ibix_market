# PDV Ibix - API de Roles (RBAC)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.middleware import AuthMiddleware, forbid_cliente_access
from ...database.connection import get_db
from ...models import Role, RolePermissao, Usuario


# Schemas
class RoleCreate(BaseModel):
    """Schema para criação de role"""
    nome: str = Field(..., min_length=2, max_length=50, description="Nome da role")
    descricao: Optional[str] = Field(None, description="Descrição da role")
    ativo: bool = Field(True, description="Status ativo/inativo")

class RoleUpdate(BaseModel):
    """Schema para atualização de role"""
    nome: Optional[str] = Field(None, min_length=2, max_length=50, description="Nome da role")
    descricao: Optional[str] = Field(None, description="Descrição da role")
    ativo: Optional[bool] = Field(None, description="Status ativo/inativo")

class RoleResponse(BaseModel):
    """Schema para resposta de role"""
    id: int
    nome: str
    descricao: Optional[str]
    ativo: bool
    total_usuarios: int = 0
    total_permissoes: int = 0
    
    class Config:
        from_attributes = True

class RoleListResponse(BaseModel):
    """Schema para resposta de lista de roles"""
    roles: List[RoleResponse]
    total: int

router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
    dependencies=[Depends(forbid_cliente_access)]
)

ROLE_SUPERADMIN = "Superadministrador"

def _eh_superadmin(current_user: Usuario) -> bool:
    return bool(current_user.role and current_user.role.nome == ROLE_SUPERADMIN)

def _ensure_superadmin_only(current_user: Usuario) -> None:
    """Apenas Superadministrador pode gerenciar roles (Administrador não)."""
    if not _eh_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Acesso negado. Gerenciamento de funções é restrito ao Superadministrador.")

@router.get("/", response_model=RoleListResponse)
async def listar_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user)
):
    """Listar roles com filtros opcionais. Apenas Superadministrador."""
    _ensure_superadmin_only(current_user)
    query = db.query(Role)
    
    if ativo is not None:
        query = query.filter(Role.ativo == ativo)
    
    total = query.count()
    roles = query.offset(skip).limit(limit).all()
    
    # Adicionar contadores
    roles_response = []
    for role in roles:
        total_usuarios = db.query(Usuario).filter(Usuario.role_id == role.id).count()
        total_permissoes = db.query(RolePermissao).filter(RolePermissao.role_id == role.id).count()
        
        role_data = RoleResponse(
            id=role.id,
            nome=role.nome,
            descricao=role.descricao,
            ativo=role.ativo,
            total_usuarios=total_usuarios,
            total_permissoes=total_permissoes
        )
        roles_response.append(role_data)
    
    return {
        "roles": roles_response,
        "total": total
    }

@router.get("/{role_id}", response_model=RoleResponse)
async def obter_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user)
):
    """Obter role por ID. Apenas Superadministrador."""
    _ensure_superadmin_only(current_user)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role não encontrada")
    
    total_usuarios = db.query(Usuario).filter(Usuario.role_id == role.id).count()
    total_permissoes = db.query(RolePermissao).filter(RolePermissao.role_id == role.id).count()
    
    return RoleResponse(
        id=role.id,
        nome=role.nome,
        descricao=role.descricao,
        ativo=role.ativo,
        total_usuarios=total_usuarios,
        total_permissoes=total_permissoes
    )

@router.post("/", response_model=RoleResponse)
async def criar_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user)
):
    """Criar nova role (apenas Superadministrador)"""
    _ensure_superadmin_only(current_user)
    try:
        # Verificar se nome já existe
        role_existente = db.query(Role).filter(Role.nome == role.nome).first()
        if role_existente:
            raise HTTPException(status_code=400, detail="Já existe uma role com este nome")
        
        # Criar role
        db_role = Role(
            nome=role.nome,
            descricao=role.descricao,
            ativo=role.ativo
        )
        
        db.add(db_role)
        db.commit()
        db.refresh(db_role)
        
        return RoleResponse(
            id=db_role.id,
            nome=db_role.nome,
            descricao=db_role.descricao,
            ativo=db_role.ativo,
            total_usuarios=0,
            total_permissoes=0
        )
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Erro de integridade do banco de dados")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@router.put("/{role_id}", response_model=RoleResponse)
async def atualizar_role(
    role_id: int,
    role: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user)
):
    """Atualizar role existente (apenas Superadministrador)."""
    _ensure_superadmin_only(current_user)
    try:
        db_role = db.query(Role).filter(Role.id == role_id).first()
        if not db_role:
            raise HTTPException(status_code=404, detail="Role não encontrada")
        
        # Verificar se nome já existe (exceto para a role atual)
        if role.nome and role.nome != db_role.nome:
            role_existente = db.query(Role).filter(
                Role.nome == role.nome,
                Role.id != role_id
            ).first()
            if role_existente:
                raise HTTPException(status_code=400, detail="Já existe uma role com este nome")
        
        # Atualizar campos
        if role.nome:
            db_role.nome = role.nome
        if role.descricao is not None:
            db_role.descricao = role.descricao
        if role.ativo is not None:
            db_role.ativo = role.ativo
        
        db.commit()
        db.refresh(db_role)
        
        total_usuarios = db.query(Usuario).filter(Usuario.role_id == db_role.id).count()
        total_permissoes = db.query(RolePermissao).filter(RolePermissao.role_id == db_role.id).count()
        
        return RoleResponse(
            id=db_role.id,
            nome=db_role.nome,
            descricao=db_role.descricao,
            ativo=db_role.ativo,
            total_usuarios=total_usuarios,
            total_permissoes=total_permissoes
        )
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Erro de integridade do banco de dados")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@router.delete("/{role_id}")
async def excluir_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user)
):
    """Excluir role (apenas Superadministrador)."""
    _ensure_superadmin_only(current_user)
    try:
        db_role = db.query(Role).filter(Role.id == role_id).first()
        if not db_role:
            raise HTTPException(status_code=404, detail="Role não encontrada")
        
        # Verificar se há usuários usando esta role
        total_usuarios = db.query(Usuario).filter(Usuario.role_id == role_id).count()
        if total_usuarios > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível excluir esta role. Existem {total_usuarios} usuário(s) vinculado(s) a ela."
            )
        
        db.delete(db_role)
        db.commit()
        
        return {"message": "Role excluída com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")
