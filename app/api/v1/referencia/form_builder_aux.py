# -*- coding: utf-8 -*-
"""
REFERÊNCIA DO CERTILOG - API Auxiliar para Form Builder
Este arquivo é uma cópia de referência do sistema Certilog.
Não deve ser usado diretamente no PDV Ibix.
Adaptar conforme necessário para implementação futura.

API Auxiliar para Form Builder - Dados do Sistema
Fornece dados necessários para blocos CMMS (equipamentos, materiais, técnicos, etc.)
Seguindo rigorosamente MAPA_SISTEMA - SEM dados hardcoded
"""

import logging
from typing import Optional

from app.core.auth import get_current_user
from app.core.rbac import require_permission
from app.database.base import get_db
from app.models.comum import ComumUsuario
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Form Builder - Dados Auxiliares"])


@router.get("/os-corretiva/blocos-contrato")
async def obter_contrato_blocos_os_corretiva_endpoint(
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:os:visualizar"))
):
    """
    Contrato de blocos da OS corretiva (OS_CORRETIVA_IMPREVISTA).

    Independente de template/schema publicado (fail-safe).
    """
    from app.services.os_corretiva_blocos_contrato import obter_contrato_blocos_os_corretiva

    return obter_contrato_blocos_os_corretiva()


@router.get("/materiais")
async def buscar_materiais(
    busca: Optional[str] = Query(None, description="Busca por nome ou código"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """
    Busca itens do catálogo para bloco de Materiais/Peças do Form Builder
    
    Retorna lista de itens cadastrados no catálogo (comum_itens).
    Busca por código ou nome, retorna apenas itens ativos.
    """
    try:
        query = """
            SELECT 
                i.id,
                i.codigo_interno as codigo,
                i.nome,
                i.tipo_item,
                i.uom_id,
                u.codigo as uom_codigo,
                u.simbolo as uom_simbolo,
                u.nome as uom_nome
            FROM comum_itens i
            LEFT JOIN comum_uom u ON i.uom_id = u.id
            WHERE i.tenant_id = :tenant_id AND i.ativo = TRUE
        """
        params = {'tenant_id': current_user.tenant_id}
        
        if busca:
            query += " AND (i.codigo_interno LIKE :busca OR i.nome LIKE :busca)"
            params['busca'] = f"%{busca}%"
        
        query += " ORDER BY i.codigo_interno ASC, i.nome ASC LIMIT :limit OFFSET :skip"
        params['limit'] = limit
        params['skip'] = skip
        
        result = db.execute(text(query), params)
        materiais = []
        for row in result:
            materiais.append({
                'id': row.id,
                'codigo': row.codigo,
                'codigo_interno': row.codigo,  # Alias para compatibilidade
                'nome': row.nome,
                'tipo_item': row.tipo_item,
                'uom_id': row.uom_id,
                'uom_codigo': row.uom_codigo,
                'uom_simbolo': row.uom_simbolo or row.uom_codigo or 'un',
                'uom_nome': row.uom_nome,
                'unidade_medida': row.uom_simbolo or row.uom_codigo or 'un',  # Compatibilidade
                'label': f"{row.codigo} - {row.nome}" if row.codigo else row.nome
            })
        
        return materiais
        
    except Exception as e:
        logger.error(f"Erro ao buscar materiais: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao buscar materiais: {str(e)}")


@router.get("/tecnicos")
async def buscar_tecnicos(
    equipe_id: Optional[int] = Query(None, description="Filtrar por equipe"),
    busca: Optional[str] = Query(None, description="Busca por nome"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:tecnicos:visualizar"))
):
    """
    Busca técnicos para bloco de Apontamento de Horas
    
    Retorna lista de técnicos disponíveis para apontamento.
    """
    try:
        query = """
            SELECT DISTINCT
                u.id,
                u.nome,
                u.email,
                u.username
            FROM comum_usuarios u
            INNER JOIN comum_usuarios_roles ur ON u.id = ur.usuario_id
            INNER JOIN comum_roles r ON ur.role_id = r.id
            WHERE u.tenant_id = :tenant_id 
            AND u.ativo = TRUE
            AND r.nome = 'TENANT_OPERATOR'
        """
        params = {'tenant_id': current_user.tenant_id}
        
        if equipe_id:
            query += """
                AND u.id IN (
                    SELECT tecnico_id FROM manutencao_tecnico_equipe 
                    WHERE equipe_id = :equipe_id AND ativo = TRUE
                )
            """
            params['equipe_id'] = equipe_id
        
        if busca:
            query += " AND (u.nome LIKE :busca OR u.email LIKE :busca OR u.username LIKE :busca)"
            params['busca'] = f"%{busca}%"
        
        query += " ORDER BY u.nome LIMIT :limit OFFSET :skip"
        params['limit'] = limit
        params['skip'] = skip
        
        result = db.execute(text(query), params)
        tecnicos = []
        for row in result:
            tecnicos.append({
                'id': row.id,
                'nome': row.nome,
                'email': row.email,
                'username': row.username,
                'label': row.nome
            })
        
        return tecnicos
        
    except Exception as e:
        logger.error(f"Erro ao buscar técnicos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao buscar técnicos: {str(e)}")


@router.get("/ativos")
async def buscar_ativos(
    unidade_id: Optional[int] = Query(None, description="Filtrar por unidade (padrão: unidade do usuário)"),
    setor_id: Optional[int] = Query(None, description="Filtrar por setor"),
    busca: Optional[str] = Query(None, description="Busca por nome ou código"),
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:ativos:visualizar"))
):
    """
    Busca ativos para bloco de Ativos do Form Builder
    
    Retorna lista de ativos disponíveis para seleção no formulário.
    Por padrão, filtra pela unidade do usuário solicitante.
    Dados vêm do cadastro de ativos (manutencao_ativos).
    """
    try:
        # Se unidade_id não for fornecido, usar a unidade do usuário
        unidade_filtro = unidade_id
        if unidade_filtro is None and current_user.unidade_id:
            unidade_filtro = current_user.unidade_id
        
        query = """
            SELECT 
                a.id, 
                a.codigo, 
                a.nome, 
                a.tipo, 
                a.setor_id, 
                a.localizacao, 
                a.fabricante, 
                a.modelo,
                s.unidade_id
            FROM manutencao_ativos a
            LEFT JOIN manutencao_setores s ON a.setor_id = s.id
            WHERE a.tenant_id = :tenant_id AND a.ativo = TRUE
        """
        params = {'tenant_id': current_user.tenant_id}
        
        # Filtrar por unidade (via setor)
        if unidade_filtro:
            query += " AND s.unidade_id = :unidade_id"
            params['unidade_id'] = unidade_filtro
        
        # Filtrar por setor
        if setor_id:
            query += " AND a.setor_id = :setor_id"
            params['setor_id'] = setor_id
        
        # Busca por nome ou código
        if busca:
            query += " AND (a.nome LIKE :busca OR a.codigo LIKE :busca)"
            params['busca'] = f"%{busca}%"
        
        query += " ORDER BY a.nome LIMIT :limit OFFSET :skip"
        params['limit'] = limit
        params['skip'] = skip
        
        result = db.execute(text(query), params)
        ativos = []
        for row in result:
            ativos.append({
                'id': row.id,
                'codigo': row.codigo,
                'nome': row.nome,
                'tipo': row.tipo,
                'setor_id': row.setor_id,
                'localizacao': row.localizacao,
                'fabricante': row.fabricante,
                'modelo': row.modelo,
                'unidade_id': row.unidade_id,
                'label': f"{row.codigo} - {row.nome}" if row.codigo else row.nome
            })
        
        return ativos
        
    except Exception as e:
        logger.error(f"Erro ao buscar ativos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao buscar ativos: {str(e)}")


@router.get("/setores")
async def buscar_setores(
    unidade_id: Optional[int] = Query(None, description="Filtrar por unidade"),
    busca: Optional[str] = Query(None, description="Busca por nome"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:setores:visualizar"))
):
    """
    Busca setores para filtros em blocos CMMS
    
    Retorna lista de setores disponíveis.
    """
    try:
        query = """
            SELECT id, nome, codigo, unidade_id
            FROM manutencao_setores
            WHERE tenant_id = :tenant_id AND ativo = TRUE
        """
        params = {'tenant_id': current_user.tenant_id}
        
        if unidade_id:
            query += " AND unidade_id = :unidade_id"
            params['unidade_id'] = unidade_id
        
        if busca:
            query += " AND (nome LIKE :busca OR codigo LIKE :busca)"
            params['busca'] = f"%{busca}%"
        
        query += " ORDER BY nome LIMIT :limit OFFSET :skip"
        params['limit'] = limit
        params['skip'] = skip
        
        result = db.execute(text(query), params)
        setores = []
        for row in result:
            setores.append({
                'id': row.id,
                'nome': row.nome,
                'codigo': row.codigo,
                'unidade_id': row.unidade_id,
                'label': f"{row.codigo} - {row.nome}" if row.codigo else row.nome
            })
        
        return setores
        
    except Exception as e:
        logger.error(f"Erro ao buscar setores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao buscar setores: {str(e)}")
