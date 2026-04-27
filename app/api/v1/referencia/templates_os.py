# -*- coding: utf-8 -*-
"""
REFERÊNCIA DO CERTILOG - API para Templates de OS - Form Builder
Este arquivo é uma cópia de referência do sistema Certilog.
Não deve ser usado diretamente no PDV Ibix.
Adaptar conforme necessário para implementação futura.

API para Templates de OS - Form Builder
Gerencia templates de formulários de OS com versionamento e RBAC Corporativo
"""

import logging
from typing import List, Optional

from app.core.auth import get_current_user
from app.core.rbac import is_super_admin, require_permission
from app.database.base import get_db
from app.models.comum import ComumUsuario
from app.models.manutencao import ManutencaoOrdemServico, ManutencaoTemplateOS, ManutencaoVersaoTemplateOS
from app.schemas.manutencao import (
    TemplateOSCreate,
    TemplateOSDuplicate,
    TemplateOSResponse,
    TemplateOSUpdate,
    TemplateRenderResponse,
    VersaoTemplateOSCreate,
    VersaoTemplateOSResponse,
)
from app.services.rbac_corporativo_service import get_unidades_usuario
from app.services.template_binding_service import TemplateBindingResolver
from app.services.template_os_service import (
    atualizar_template,
    criar_template,
    duplicar_template,
    filtrar_templates_por_escopo,
    obter_versao_atual,
    publicar_template,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Templates de OS - Form Builder"])


# ============================================================================
# TEMPLATES
# ============================================================================

@router.get("", response_model=List[TemplateOSResponse])
async def listar_templates(
    tipo_os: Optional[str] = Query(None, description="Filtrar por tipo de OS"),
    status_filter: Optional[str] = Query(None, description="Filtrar por status: rascunho, publicado, arquivado"),
    unidade_id: Optional[int] = Query(None, description="Filtrar por unidade (None = corporativos + todas unidades)"),
    escopo: Optional[str] = Query(None, description="Filtrar por escopo: 'corporativo', 'unidade' ou None (todos)"),
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """
    Listar templates de OS com filtros hierárquicos RBAC
    
    - SUPER_ADMIN: vê todos os templates (sem filtro de escopo)
    - GERENTE_CORPORATIVO: vê todos os templates
    - GESTOR_UNIDADE: vê templates corporativos + templates da sua unidade
    - TECNICO/SOLICITANTE: vê templates corporativos + templates da sua unidade
    """
    try:
        filtros = {}
        if tipo_os:
            filtros["tipo_os"] = tipo_os
        if status_filter:
            filtros["status"] = status_filter
        
        # SUPER_ADMIN vê todos os templates sem filtro de escopo
        if is_super_admin(current_user, db):
            logger.info("SUPER_ADMIN: listando todos os templates sem filtro de escopo")
            query = db.query(ManutencaoTemplateOS).filter(
                ManutencaoTemplateOS.tenant_id == current_user.tenant_id,
                ManutencaoTemplateOS.ativo == True
            )
            if "tipo_os" in filtros:
                query = query.filter(ManutencaoTemplateOS.tipo_os == filtros["tipo_os"])
            if "status" in filtros:
                query = query.filter(ManutencaoTemplateOS.status == filtros["status"])
            templates = query.all()
        else:
            # Aplicar filtros hierárquicos
            templates = filtrar_templates_por_escopo(db, current_user, filtros)
        
        logger.info(f"Templates encontrados após filtrar_templates_por_escopo: {len(templates)}")
        
        # Debug: listar todos os templates do tenant (para verificar se o template foi criado)
        todos_templates_tenant = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.tenant_id == current_user.tenant_id,
            ManutencaoTemplateOS.ativo == True
        ).all()
        logger.info(f"DEBUG: Total de templates ativos no tenant {current_user.tenant_id}: {len(todos_templates_tenant)}")
        for t in todos_templates_tenant:
            logger.info(f"  - Template ID={t.id}, nome={t.nome}, unidade_id={t.unidade_id}, status={t.status}, ativo={t.ativo}")
        
        # Filtros adicionais opcionais
        if unidade_id is not None:
            templates = [t for t in templates if t.unidade_id == unidade_id]
        
        if escopo == "corporativo":
            templates = [t for t in templates if t.unidade_id is None]
        elif escopo == "unidade":
            templates = [t for t in templates if t.unidade_id is not None]
        
        logger.info(f"Templates após filtros adicionais: {len(templates)}")
        
        # Retornar templates usando model_validate do Pydantic
        resultado = []
        for template in templates:
            try:
                versao_atual = obter_versao_atual(db, template.id)
                
                # Serializar template
                template_dict = TemplateOSResponse.model_validate(template).model_dump(by_alias=True)
                
                # Adicionar versão atual se existir
                if versao_atual:
                    template_dict["versao_atual"] = VersaoTemplateOSResponse.model_validate(versao_atual).model_dump(by_alias=True)
                else:
                    template_dict["versao_atual"] = None
                
                template_dict["versoes"] = []  # Será preenchido se necessário
                resultado.append(template_dict)
            except Exception as e:
                logger.error(f"Erro ao serializar template {template.id}: {e}", exc_info=True)
                # Continuar com próximo template mesmo se houver erro em um
                continue
        
        logger.info(f"Listando {len(resultado)} templates para usuário {current_user.id}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao listar templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar templates: {str(e)}"
        )


@router.get("/padrao/{tipo_os_id}", response_model=Optional[TemplateOSResponse])
async def obter_template_padrao(
    tipo_os_id: int,
    unidade_id: Optional[int] = Query(None, description="ID da unidade (usa unidade do usuário se None)"),
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """
    Buscar template padrão para um tipo de OS específico
    
    Prioridade de busca:
    1. Template da unidade específica com tipo_os_id correspondente
    2. Template corporativo (unidade_id IS NULL) com tipo_os_id correspondente
    3. Se não encontrar, retorna None (não é erro - permite criar OS sem template)
    """
    try:
        # Validar se tipo_os_id existe (mas não bloquear se não encontrar template padrão)
        from app.models.manutencao import ManutencaoTipoOS
        tipo_os = db.query(ManutencaoTipoOS).filter(
            ManutencaoTipoOS.id == tipo_os_id,
            ManutencaoTipoOS.tenant_id == current_user.tenant_id,
            ManutencaoTipoOS.ativo == True
        ).first()
        
        # Se tipo_os não existe ou está inativo, retornar None (não é erro - permite criar OS sem template)
        # O tipo_os_id será validado na criação da OS
        if not tipo_os:
            logger.warning(f"Tipo de OS {tipo_os_id} não encontrado ou inativo para tenant {current_user.tenant_id}")
            return None
        
        # Se unidade_id não fornecido, usar unidade do usuário
        if unidade_id is None:
            unidade_id = current_user.unidade_id
        
        # Primeira tentativa: buscar template da unidade específica
        template = None
        if unidade_id is not None:
            template = db.query(ManutencaoTemplateOS).filter(
                ManutencaoTemplateOS.tenant_id == current_user.tenant_id,
                ManutencaoTemplateOS.tipo_os_id == tipo_os_id,
                ManutencaoTemplateOS.unidade_id == unidade_id,
                ManutencaoTemplateOS.status == "publicado",
                ManutencaoTemplateOS.ativo == True
            ).first()
            if template:
                logger.info(f"Template padrão encontrado na unidade {unidade_id}: template_id={template.id}, nome={template.nome}")
        
        # Segunda tentativa: buscar template corporativo (unidade_id IS NULL)
        if template is None:
            template = db.query(ManutencaoTemplateOS).filter(
                ManutencaoTemplateOS.tenant_id == current_user.tenant_id,
                ManutencaoTemplateOS.tipo_os_id == tipo_os_id,
                ManutencaoTemplateOS.unidade_id.is_(None),
                ManutencaoTemplateOS.status == "publicado",
                ManutencaoTemplateOS.ativo == True
            ).first()
            if template:
                logger.info(f"Template padrão encontrado corporativo: template_id={template.id}, nome={template.nome}")
        
        # Se não encontrou template padrão, retornar None (não é erro)
        if template is None:
            logger.info(f"Nenhum template padrão encontrado para tipo_os_id={tipo_os_id}, unidade_id={unidade_id}, tenant_id={current_user.tenant_id}")
            return None
        
        # Validar acesso hierárquico
        if not is_super_admin(current_user, db) and current_user.papel_organizacional != "gerente_corporativo":
            unidades_acessiveis = get_unidades_usuario(current_user, db, incluir_filhas=False)
            if template.unidade_id is not None and template.unidade_id not in unidades_acessiveis:
                # Se não tem acesso ao template da unidade, retornar None
                return None
        
        # Obter versão atual
        versao_atual = obter_versao_atual(db, template.id)
        
        # Serializar template
        template_dict = TemplateOSResponse.model_validate(template).model_dump(by_alias=True)
        if versao_atual:
            versao_dict = VersaoTemplateOSResponse.model_validate(versao_atual).model_dump(by_alias=True)
            template_dict["versao_atual"] = versao_dict
        else:
            template_dict["versao_atual"] = None
        template_dict["versoes"] = []
        
        return template_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar template padrão: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar template padrão: {str(e)}"
        )


@router.get("/{template_id}", response_model=TemplateOSResponse)
async def obter_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """Obter detalhes de um template específico"""
    try:
        template = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.id == template_id,
            ManutencaoTemplateOS.tenant_id == current_user.tenant_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template não encontrado"
            )
        
        # Validar acesso hierárquico
        # SUPER_ADMIN e GERENTE_CORPORATIVO podem acessar todos os templates
        if is_super_admin(current_user, db) or current_user.papel_organizacional == "gerente_corporativo":
            pass  # Pode acessar qualquer template
        else:
            unidades_acessiveis = get_unidades_usuario(current_user, db, incluir_filhas=False)
            if template.unidade_id is not None and template.unidade_id not in unidades_acessiveis:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para acessar este template"
                )
        
        versao_atual = obter_versao_atual(db, template_id)
        
        template_dict = TemplateOSResponse.model_validate(template).model_dump(by_alias=True)
        if versao_atual:
            versao_dict = VersaoTemplateOSResponse.model_validate(versao_atual).model_dump(by_alias=True)
            template_dict["versao_atual"] = versao_dict
        else:
            template_dict["versao_atual"] = None
        template_dict["versoes"] = []
        
        return template_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter template: {str(e)}"
        )


@router.post("", response_model=TemplateOSResponse, status_code=status.HTTP_201_CREATED)
async def criar_template_os(
    dados: TemplateOSCreate,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:templates:criar"))
):
    """
    Criar novo template de OS (sempre inicia como rascunho)
    
    - GERENTE_CORPORATIVO: pode criar para qualquer unidade ou corporativo
    - GESTOR_UNIDADE: pode criar apenas para sua unidade
    """
    try:
        template = criar_template(db, dados.model_dump(), current_user)
        
        # Carregar versão atual se existir
        versao_atual = obter_versao_atual(db, template.id)
        
        # Serializar resposta
        template_dict = TemplateOSResponse.model_validate(template).model_dump(by_alias=True)
        if versao_atual:
            template_dict["versao_atual"] = VersaoTemplateOSResponse.model_validate(versao_atual).model_dump(by_alias=True)
        else:
            template_dict["versao_atual"] = None
        template_dict["versoes"] = []
        
        return template_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar template: {str(e)}"
        )


@router.put("/{template_id}", response_model=TemplateOSResponse)
async def atualizar_template_os(
    template_id: int,
    dados: TemplateOSUpdate,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:templates:editar"))
):
    """
    Atualizar template
    
    - Templates em rascunho: podem ser editados normalmente
    - Templates publicados: podem ser editados, mas voltam para rascunho
    - Templates arquivados: não podem ser editados
    
    - Valida escopo hierárquico antes de atualizar
    """
    try:
        template = atualizar_template(db, template_id, dados.model_dump(exclude_unset=True), current_user)
        return TemplateOSResponse.model_validate(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar template: {str(e)}"
        )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def arquivar_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:templates:arquivar"))
):
    """Arquivar template (soft delete)"""
    try:
        template = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.id == template_id,
            ManutencaoTemplateOS.tenant_id == current_user.tenant_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template não encontrado"
            )
        
        template.status = "arquivado"
        template.ativo = False
        template.atualizado_por = current_user.id
        
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao arquivar template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao arquivar template: {str(e)}"
        )


@router.delete("/{template_id}/apagar", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """
    Apagar template permanentemente (hard delete) - Apenas SUPER_ADMIN
    
    Verifica se há ordens de serviço usando o template antes de deletar.
    Se houver, retorna erro informando a quantidade de OS que usam o template.
    """
    try:
        # Verificar se usuário é SUPER_ADMIN
        if not is_super_admin(current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas SUPER_ADMIN pode apagar templates permanentemente"
            )
        
        # Buscar template
        template = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.id == template_id,
            ManutencaoTemplateOS.tenant_id == current_user.tenant_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template não encontrado"
            )
        
        # Verificar se há ordens de serviço usando este template
        os_count = db.query(ManutencaoOrdemServico).filter(
            ManutencaoOrdemServico.template_id == template_id,
            ManutencaoOrdemServico.ativo == True
        ).count()
        
        if os_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível apagar o template '{template.nome}'. Existem {os_count} ordem(ns) de serviço usando este template. Arquivar o template ao invés de apagá-lo."
            )
        
        # Verificar se há versões do template
        db.query(ManutencaoVersaoTemplateOS).filter(
            ManutencaoVersaoTemplateOS.template_id == template_id
        ).count()
        
        # Deletar template (cascade vai deletar versões automaticamente devido ao relacionamento)
        db.delete(template)
        db.commit()
        
        logger.info(f"Template {template_id} ({template.nome}) apagado permanentemente por SUPER_ADMIN {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao apagar template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao apagar template: {str(e)}"
        )


@router.post("/{template_id}/publicar", response_model=VersaoTemplateOSResponse, status_code=status.HTTP_201_CREATED)
async def publicar_template_os(
    template_id: int,
    dados: VersaoTemplateOSCreate,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:templates:publicar"))
):
    """
    Publicar template criando nova versão
    
    - Valida schema antes de publicar
    - Encerra versão anterior automaticamente
    - Template passa para status 'publicado'
    """
    try:
        versao = publicar_template(
            db,
            template_id,
            dados.versao,
            dados.formulario_schema,  # Usar o nome interno do campo
            current_user
        )
        return VersaoTemplateOSResponse.model_validate(versao)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao publicar template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao publicar template: {str(e)}"
        )


@router.post("/{template_id}/duplicar", response_model=TemplateOSResponse, status_code=status.HTTP_201_CREATED)
async def duplicar_template_os(
    template_id: int,
    dados: TemplateOSDuplicate,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:templates:criar"))
):
    """
    Duplicar template existente para nova unidade ou com novo nome
    
    - Copia todas as versões do template original
    - Template duplicado sempre inicia como "rascunho"
    - GERENTE_CORPORATIVO: pode duplicar para qualquer unidade
    - GESTOR_UNIDADE: pode duplicar apenas para sua unidade
    """
    try:
        # Log detalhado dos dados recebidos
        dados_dict = dados.model_dump()
        logger.info(f"📋 Dados recebidos para duplicação: template_id={template_id}, nome={dados_dict.get('nome')}, unidade_id={dados_dict.get('unidade_id')} (tipo={type(dados_dict.get('unidade_id')).__name__})")
        
        template_duplicado = duplicar_template(
            db,
            template_id,
            dados_dict,
            current_user
        )
        
        # Carregar versão atual se existir
        versao_atual = obter_versao_atual(db, template_duplicado.id)
        
        # Serializar resposta
        template_dict = TemplateOSResponse.model_validate(template_duplicado).model_dump(by_alias=True)
        if versao_atual:
            template_dict["versao_atual"] = VersaoTemplateOSResponse.model_validate(versao_atual).model_dump(by_alias=True)
        else:
            template_dict["versao_atual"] = None
        template_dict["versoes"] = []
        
        return template_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao duplicar template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao duplicar template: {str(e)}"
        )


@router.get("/{template_id}/versoes", response_model=List[VersaoTemplateOSResponse])
async def listar_versoes_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """Listar todas as versões de um template"""
    try:
        template = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.id == template_id,
            ManutencaoTemplateOS.tenant_id == current_user.tenant_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template não encontrado"
            )
        
        versoes = db.query(ManutencaoVersaoTemplateOS).filter(
            ManutencaoVersaoTemplateOS.template_id == template_id
        ).order_by(ManutencaoVersaoTemplateOS.data_inicio_vigencia.desc()).all()
        
        return [VersaoTemplateOSResponse.model_validate(v) for v in versoes]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar versões: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar versões: {str(e)}"
        )


@router.get("/{template_id}/versao/{versao}", response_model=VersaoTemplateOSResponse)
async def obter_versao_especifica(
    template_id: int,
    versao: str,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(get_current_user)
):
    """Obter versão específica de um template"""
    try:
        versao_obj = db.query(ManutencaoVersaoTemplateOS).filter(
            ManutencaoVersaoTemplateOS.template_id == template_id,
            ManutencaoVersaoTemplateOS.versao == versao
        ).first()
        
        if not versao_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Versão {versao} não encontrada para este template"
            )
        
        return VersaoTemplateOSResponse.model_validate(versao_obj)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter versão: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter versão: {str(e)}"
        )


@router.get("/{template_id}/render", response_model=TemplateRenderResponse)
async def renderizar_template(
    template_id: int,
    os_id: Optional[int] = Query(None, description="ID da OS para resolver bindings"),
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:templates:visualizar"))
):
    """
    Renderizar template com bindings resolvidos
    
    Se os_id for fornecido, resolve todos os bindings usando dados da OS.
    Caso contrário, retorna template sem bindings resolvidos.
    """
    try:
        # Carregar template
        template = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.id == template_id,
            ManutencaoTemplateOS.tenant_id == current_user.tenant_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template não encontrado"
            )
        
        # Validar acesso hierárquico
        if current_user.papel_organizacional != "gerente_corporativo":
            unidades_acessiveis = get_unidades_usuario(current_user, db, incluir_filhas=False)
            if template.unidade_id is not None and template.unidade_id not in unidades_acessiveis:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para acessar este template"
                )
        
        # Obter versão atual
        versao_atual = obter_versao_atual(db, template_id)
        
        if not versao_atual or not versao_atual.schema_json:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template não possui versão publicada ou schema inválido"
            )
        
        # Obter schema
        schema = versao_atual.schema_json
        if isinstance(schema, str):
            import json
            schema = json.loads(schema)
        
        # Obter contexto completo se os_id fornecido
        contexto = {}
        if os_id:
            contexto = TemplateBindingResolver.obter_contexto_completo(
                os_id=os_id,
                db=db,
                current_user=current_user
            )
        else:
            # Contexto mínimo sem OS - incluir informações do template
            contexto = {
                "os": None,
                "user": {
                    "id": current_user.id,
                    "name": current_user.nome,
                    "email": current_user.email,
                    "username": current_user.username,
                    "role": None,
                    "papel_organizacional": current_user.papel_organizacional,
                    "unidade_id": current_user.unidade_id,
                },
                "status": None,
                "template": {
                    "nome": template.nome,
                    "criado_em": template.criado_em.isoformat() if template.criado_em else None,
                    "atualizado_em": template.atualizado_em.isoformat() if template.atualizado_em else None,
                    "versao": versao_atual.versao if versao_atual else None
                },
                "templateNome": template.nome,
                "refs": {
                    "company": None,
                    "unit": None,
                    "program": {
                        "name": template.nome,
                        "code": None,
                        "revision_number": versao_atual.versao if versao_atual else None,
                        "revision_date": versao_atual.data_inicio_vigencia.isoformat() if versao_atual and versao_atual.data_inicio_vigencia else None
                    },
                    "asset": None,
                    "setor": None
                }
            }
        
        # Resolver bindings no schema
        schema_resolvido = TemplateBindingResolver.resolver_bindings_schema(schema, contexto)
        
        return TemplateRenderResponse(
            template_id=template.id,
            template_nome=template.nome,
            formulario_schema=schema_resolvido,
            contexto=contexto,
            os_id=os_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao renderizar template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao renderizar template: {str(e)}"
        )


@router.get("/{template_origem_id}/comparar/{template_destino_id}", response_model=dict)
async def comparar_templates(
    template_origem_id: int,
    template_destino_id: int,
    db: Session = Depends(get_db),
    current_user: ComumUsuario = Depends(require_permission("manutencao:templates:visualizar"))
):
    """
    Comparar dois templates para verificar se a clonagem foi completa
    Útil para validar se todos os dados foram copiados corretamente
    """
    import json
    
    try:
        # Buscar templates
        template_origem = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.id == template_origem_id,
            ManutencaoTemplateOS.tenant_id == current_user.tenant_id
        ).first()
        
        template_destino = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.id == template_destino_id,
            ManutencaoTemplateOS.tenant_id == current_user.tenant_id
        ).first()
        
        if not template_origem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template origem (ID {template_origem_id}) não encontrado"
            )
        
        if not template_destino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template destino (ID {template_destino_id}) não encontrado"
            )
        
        # Buscar versões
        versoes_origem = db.query(ManutencaoVersaoTemplateOS).filter(
            ManutencaoVersaoTemplateOS.template_id == template_origem_id
        ).order_by(ManutencaoVersaoTemplateOS.versao).all()
        
        versoes_destino = db.query(ManutencaoVersaoTemplateOS).filter(
            ManutencaoVersaoTemplateOS.template_id == template_destino_id
        ).order_by(ManutencaoVersaoTemplateOS.versao).all()
        
        # Comparar número de versões
        num_versoes_origem = len(versoes_origem)
        num_versoes_destino = len(versoes_destino)
        
        # Comparar cada versão
        comparacao_versoes = []
        versoes_origem_dict = {v.versao: v for v in versoes_origem}
        versoes_destino_dict = {v.versao: v for v in versoes_destino}
        
        todas_versoes = set(list(versoes_origem_dict.keys()) + list(versoes_destino_dict.keys()))
        
        for versao_num in sorted(todas_versoes):
            v_origem = versoes_origem_dict.get(versao_num)
            v_destino = versoes_destino_dict.get(versao_num)
            
            if not v_origem:
                comparacao_versoes.append({
                    "versao": versao_num,
                    "status": "FALTANDO_ORIGEM",
                    "origem": None,
                    "destino": {
                        "id": v_destino.id,
                        "tem_schema": v_destino.schema_json is not None
                    }
                })
                continue
            
            if not v_destino:
                comparacao_versoes.append({
                    "versao": versao_num,
                    "status": "FALTANDO_DESTINO",
                    "origem": {
                        "id": v_origem.id,
                        "tem_schema": v_origem.schema_json is not None
                    },
                    "destino": None
                })
                continue
            
            # Comparar schema_json
            schema_origem = v_origem.schema_json
            schema_destino = v_destino.schema_json
            
            if isinstance(schema_origem, str):
                try:
                    schema_origem = json.loads(schema_origem)
                except:
                    schema_origem = {}
            
            if isinstance(schema_destino, str):
                try:
                    schema_destino = json.loads(schema_destino)
                except:
                    schema_destino = {}
            
            # Contar elementos
            campos_origem = len(schema_origem.get("campos", [])) if isinstance(schema_origem, dict) else 0
            secoes_origem = len(schema_origem.get("secoes", [])) if isinstance(schema_origem, dict) else 0
            blocos_origem = len(schema_origem.get("blocos_repetiveis", [])) if isinstance(schema_origem, dict) else 0
            
            campos_destino = len(schema_destino.get("campos", [])) if isinstance(schema_destino, dict) else 0
            secoes_destino = len(schema_destino.get("secoes", [])) if isinstance(schema_destino, dict) else 0
            blocos_destino = len(schema_destino.get("blocos_repetiveis", [])) if isinstance(schema_destino, dict) else 0
            
            # Verificar se são iguais
            iguais = (
                campos_origem == campos_destino and
                secoes_origem == secoes_destino and
                blocos_origem == blocos_destino
            )
            
            comparacao_versoes.append({
                "versao": versao_num,
                "status": "IGUAL" if iguais else "DIFERENTE",
                "origem": {
                    "id": v_origem.id,
                    "campos": campos_origem,
                    "secoes": secoes_origem,
                    "blocos_repetiveis": blocos_origem,
                    "tamanho_schema": len(json.dumps(schema_origem, default=str)) if schema_origem else 0
                },
                "destino": {
                    "id": v_destino.id,
                    "campos": campos_destino,
                    "secoes": secoes_destino,
                    "blocos_repetiveis": blocos_destino,
                    "tamanho_schema": len(json.dumps(schema_destino, default=str)) if schema_destino else 0
                }
            })
        
        # Resumo
        todas_iguais = all(c["status"] == "IGUAL" for c in comparacao_versoes)
        todas_versoes_presentes = num_versoes_origem == num_versoes_destino and all(
            c["status"] != "FALTANDO_DESTINO" and c["status"] != "FALTANDO_ORIGEM" 
            for c in comparacao_versoes
        )
        
        return {
            "template_origem": {
                "id": template_origem.id,
                "nome": template_origem.nome,
                "unidade_id": template_origem.unidade_id,
                "status": template_origem.status,
                "tipo_os": template_origem.tipo_os
            },
            "template_destino": {
                "id": template_destino.id,
                "nome": template_destino.nome,
                "unidade_id": template_destino.unidade_id,
                "status": template_destino.status,
                "tipo_os": template_destino.tipo_os
            },
            "resumo": {
                "versoes_origem": num_versoes_origem,
                "versoes_destino": num_versoes_destino,
                "todas_versoes_presentes": todas_versoes_presentes,
                "todas_versoes_iguais": todas_iguais,
                "status_geral": "✓ CLONAGEM COMPLETA" if (todas_versoes_presentes and todas_iguais) else "✗ CLONAGEM INCOMPLETA"
            },
            "comparacao_versoes": comparacao_versoes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao comparar templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao comparar templates: {str(e)}"
        )
