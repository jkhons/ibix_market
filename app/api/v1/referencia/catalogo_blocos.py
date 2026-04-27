# -*- coding: utf-8 -*-
"""
REFERÊNCIA DO CERTILOG - API para Catálogo de Blocos Reutilizáveis
Este arquivo é uma cópia de referência do sistema Certilog.
Não deve ser usado diretamente no PDV Ibix.
Adaptar conforme necessário para implementação futura.

API para Catálogo de Blocos Reutilizáveis - Form Builder
Gerencia catálogo de blocos com RBAC Corporativo
"""

import logging
from typing import List, Optional

from app.core.auth import get_current_user
from app.core.rbac import require_permission
from app.database.base import get_db
from app.models.comum import ComumUsuario
from app.models.manutencao import ManutencaoCatalogoBloco
from app.schemas.manutencao import CatalogoBlocoCreate, CatalogoBlocoResponse, CatalogoBlocoUpdate
from app.services.rbac_corporativo_service import get_unidades_usuario, validar_escopo_unidade
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Catálogo de Blocos - Form Builder"])


# ============================================================================
# CATÁLOGO DE BLOCOS
# ============================================================================

@router.get("", response_model=List[CatalogoBlocoResponse])
async def listar_blocos(
    tipo_bloco: Optional[str] = Query(None, description="Filtrar por tipo de bloco"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    busca: Optional[str] = Query(None, description="Busca textual no nome"),
    unidade_id: Optional[int] = Query(None, description="Filtrar por unidade"),
    escopo: Optional[str] = Query(None, description="Filtrar por escopo: 'corporativo', 'unidade' ou None (todos)"),
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """
    Listar blocos do catálogo com filtros hierárquicos RBAC
    
    - GERENTE_CORPORATIVO: vê todos os blocos
    - GESTOR_UNIDADE: vê blocos corporativos + blocos da sua unidade
    - TECNICO/SOLICITANTE: vê blocos corporativos + blocos da sua unidade
    """
    try:
        query = db.query(ManutencaoCatalogoBloco).filter(
            ManutencaoCatalogoBloco.tenant_id == current_user.tenant_id,
            ManutencaoCatalogoBloco.ativo == True
        )
        
        # Aplicar filtros hierárquicos
        if current_user.papel_organizacional == "gerente_corporativo":
            # GERENTE_CORPORATIVO vê todos
            pass
        else:
            # Outros perfis: vê corporativos + suas unidades
            unidades_acessiveis = get_unidades_usuario(current_user, db, incluir_filhas=False)
            query = query.filter(
                or_(
                    ManutencaoCatalogoBloco.unidade_id.is_(None),  # Corporativos
                    ManutencaoCatalogoBloco.unidade_id.in_(unidades_acessiveis)  # Suas unidades
                )
            )
        
        # Filtros adicionais
        if tipo_bloco:
            query = query.filter(ManutencaoCatalogoBloco.tipo_bloco == tipo_bloco)
        if categoria:
            query = query.filter(ManutencaoCatalogoBloco.categoria == categoria)
        if busca:
            query = query.filter(ManutencaoCatalogoBloco.nome.like(f"%{busca}%"))
        if unidade_id is not None:
            query = query.filter(ManutencaoCatalogoBloco.unidade_id == unidade_id)
        if escopo == "corporativo":
            query = query.filter(ManutencaoCatalogoBloco.unidade_id.is_(None))
        elif escopo == "unidade":
            query = query.filter(ManutencaoCatalogoBloco.unidade_id.isnot(None))
        
        blocos = query.order_by(ManutencaoCatalogoBloco.nome).all()
        return [CatalogoBlocoResponse.model_validate(b) for b in blocos]
        
    except Exception as e:
        logger.error(f"Erro ao listar blocos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar blocos: {str(e)}"
        )


@router.get("/{bloco_id}", response_model=CatalogoBlocoResponse)
async def obter_bloco(
    bloco_id: int,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """Obter detalhes de um bloco específico"""
    try:
        bloco = db.query(ManutencaoCatalogoBloco).filter(
            ManutencaoCatalogoBloco.id == bloco_id,
            ManutencaoCatalogoBloco.tenant_id == current_user.tenant_id
        ).first()
        
        if not bloco:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bloco não encontrado"
            )
        
        # Validar acesso hierárquico
        if current_user.papel_organizacional != "gerente_corporativo":
            unidades_acessiveis = get_unidades_usuario(current_user, db, incluir_filhas=False)
            if bloco.unidade_id is not None and bloco.unidade_id not in unidades_acessiveis:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para acessar este bloco"
                )
        
        return CatalogoBlocoResponse.model_validate(bloco)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter bloco: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter bloco: {str(e)}"
        )


@router.post("", response_model=CatalogoBlocoResponse, status_code=status.HTTP_201_CREATED)
async def criar_bloco(
    dados: CatalogoBlocoCreate,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:catalogo:criar"))
):
    """
    Criar novo bloco no catálogo
    
    - GERENTE_CORPORATIVO: pode criar para qualquer unidade ou corporativo
    - GESTOR_UNIDADE: pode criar apenas para sua unidade
    """
    try:
        unidade_id = dados.unidade_id
        
        # Validar escopo hierárquico
        if unidade_id is not None:
            pode_acessar, mensagem = validar_escopo_unidade(current_user, unidade_id, db)
            if not pode_acessar:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Não pode criar bloco para unidade {unidade_id}: {mensagem}"
                )
        
        if current_user.papel_organizacional == "gestor_unidade":
            if unidade_id is not None and unidade_id != current_user.unidade_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Só pode criar blocos para sua unidade"
                )
        
        # Verificar se já existe bloco com mesmo nome e versão
        query = db.query(ManutencaoCatalogoBloco).filter(
            ManutencaoCatalogoBloco.tenant_id == current_user.tenant_id,
            ManutencaoCatalogoBloco.nome == dados.nome,
            ManutencaoCatalogoBloco.versao == dados.versao
        )
        if unidade_id is None:
            query = query.filter(ManutencaoCatalogoBloco.unidade_id.is_(None))
        else:
            query = query.filter(ManutencaoCatalogoBloco.unidade_id == unidade_id)
        
        if query.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe bloco com nome '{dados.nome}' versão '{dados.versao}' para este escopo"
            )
        
        # Criar bloco
        bloco = ManutencaoCatalogoBloco(
            tenant_id=current_user.tenant_id,
            unidade_id=unidade_id,
            nome=dados.nome,
            tipo_bloco=dados.tipo_bloco,
            categoria=dados.categoria,
            tags=dados.tags,
            versao=dados.versao,
            schema_bloco_json=dados.bloco_schema,  # Usar o nome interno do campo
            preview_html=dados.preview_html,
            criado_por=current_user.id
        )
        
        db.add(bloco)
        db.commit()
        db.refresh(bloco)
        
        logger.info(f"Bloco criado: ID={bloco.id}, nome={bloco.nome}, unidade_id={unidade_id}")
        return CatalogoBlocoResponse.model_validate(bloco)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar bloco: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar bloco: {str(e)}"
        )


@router.put("/{bloco_id}", response_model=CatalogoBlocoResponse)
async def atualizar_bloco(
    bloco_id: int,
    dados: CatalogoBlocoUpdate,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:catalogo:editar"))
):
    """
    Atualizar bloco (cria nova versão se versão for alterada)
    
    - Valida escopo hierárquico antes de atualizar
    """
    try:
        bloco = db.query(ManutencaoCatalogoBloco).filter(
            ManutencaoCatalogoBloco.id == bloco_id,
            ManutencaoCatalogoBloco.tenant_id == current_user.tenant_id
        ).first()
        
        if not bloco:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bloco não encontrado"
            )
        
        # Validar escopo hierárquico
        unidade_id = dados.unidade_id if dados.unidade_id is not None else bloco.unidade_id
        if unidade_id is not None:
            pode_acessar, mensagem = validar_escopo_unidade(current_user, unidade_id, db)
            if not pode_acessar:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Não pode editar bloco para unidade {unidade_id}: {mensagem}"
                )
        
        if current_user.papel_organizacional == "gestor_unidade":
            if unidade_id is not None and unidade_id != current_user.unidade_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Só pode editar blocos da sua unidade"
                )
        
        # Atualizar campos
        dados_dict = dados.model_dump(exclude_unset=True, by_alias=False)  # Usar nomes internos
        # Mapear nome interno para nome do modelo
        if 'bloco_schema' in dados_dict:
            dados_dict['schema_bloco_json'] = dados_dict.pop('bloco_schema')
        for campo, valor in dados_dict.items():
            setattr(bloco, campo, valor)
        
        bloco.atualizado_por = current_user.id
        
        db.commit()
        db.refresh(bloco)
        
        logger.info(f"Bloco atualizado: ID={bloco.id}")
        return CatalogoBlocoResponse.model_validate(bloco)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar bloco: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar bloco: {str(e)}"
        )


@router.delete("/{bloco_id}", status_code=status.HTTP_204_NO_CONTENT)
async def arquivar_bloco(
    bloco_id: int,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:catalogo:arquivar"))
):
    """Arquivar bloco (soft delete)"""
    try:
        bloco = db.query(ManutencaoCatalogoBloco).filter(
            ManutencaoCatalogoBloco.id == bloco_id,
            ManutencaoCatalogoBloco.tenant_id == current_user.tenant_id
        ).first()
        
        if not bloco:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bloco não encontrado"
            )
        
        bloco.ativo = False
        bloco.atualizado_por = current_user.id
        
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao arquivar bloco: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao arquivar bloco: {str(e)}"
        )


@router.get("/{bloco_id}/preview", response_class=HTMLResponse)
async def preview_bloco(
    bloco_id: int,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """Obter preview HTML do bloco"""
    try:
        bloco = db.query(ManutencaoCatalogoBloco).filter(
            ManutencaoCatalogoBloco.id == bloco_id,
            ManutencaoCatalogoBloco.tenant_id == current_user.tenant_id
        ).first()
        
        if not bloco:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bloco não encontrado"
            )
        
        # Retornar preview HTML ou HTML básico
        preview = bloco.preview_html or f"<div>Preview do bloco: {bloco.nome}</div>"
        return preview
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter preview: {str(e)}"
        )
