# -*- coding: utf-8 -*-
"""
REFERÊNCIA DO CERTILOG - Serviço de Templates de OS - Form Builder
Este arquivo é uma cópia de referência do sistema Certilog.
Não deve ser usado diretamente no PDV Ibix.
Adaptar conforme necessário para implementação futura.

Serviço de Templates de OS - Form Builder
Gerencia criação, atualização, versionamento e publicação de templates
"""

import copy
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.models.comum import ComumUsuario
from app.models.manutencao import ManutencaoOrdemServico, ManutencaoTemplateOS, ManutencaoVersaoTemplateOS
from app.services.rbac_corporativo_service import get_unidades_usuario, validar_escopo_unidade
from app.utils.datetime_utils import now_brasil_naive
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def criar_template(
    db: Session,
    dados: Dict[str, Any],
    usuario: ComumUsuario
) -> ManutencaoTemplateOS:
    """
    Cria um novo template de OS
    
    Args:
        db: Sessão do banco de dados
        dados: Dados do template (nome, tipo_os, descricao, unidade_id)
        usuario: Usuário criador
        
    Returns:
        ManutencaoTemplateOS: Template criado
        
    Raises:
        HTTPException: Se usuário não tem permissão para criar template na unidade especificada
    """
    unidade_id = dados.get("unidade_id")
    
    # Validar escopo hierárquico
    if unidade_id is not None:
        pode_acessar, mensagem = validar_escopo_unidade(usuario, unidade_id, db)
        if not pode_acessar:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Não pode criar template para unidade {unidade_id}: {mensagem}"
            )
    
    # Para GERENTE_CORPORATIVO, permitir qualquer unidade ou NULL
    # Para GESTOR_UNIDADE, só permite sua unidade
    if usuario.papel_organizacional == "gestor_unidade":
        if unidade_id is not None and unidade_id != usuario.unidade_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Só pode criar templates para sua unidade"
            )
    
    # Verificar se já existe template com mesmo nome
    query = db.query(ManutencaoTemplateOS).filter(
        ManutencaoTemplateOS.tenant_id == usuario.tenant_id,
        ManutencaoTemplateOS.nome == dados["nome"]
    )
    if unidade_id is None:
        query = query.filter(ManutencaoTemplateOS.unidade_id.is_(None))
    else:
        query = query.filter(ManutencaoTemplateOS.unidade_id == unidade_id)
    
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe template com nome '{dados['nome']}' para este escopo"
        )
    
    # Validar tipo_os_id se fornecido (verificar constraint única)
    tipo_os_id = dados.get("tipo_os_id")
    if tipo_os_id is not None:
        template_existente = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.tenant_id == usuario.tenant_id,
            ManutencaoTemplateOS.unidade_id == unidade_id,
            ManutencaoTemplateOS.tipo_os_id == tipo_os_id,
            ManutencaoTemplateOS.ativo == True
        ).first()
        
        if template_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um template padrão para este tipo de OS nesta unidade: {template_existente.nome}"
            )
    
    # Criar template
    template = ManutencaoTemplateOS(
        tenant_id=usuario.tenant_id,
        unidade_id=unidade_id,
        nome=dados["nome"],
        tipo_os=dados["tipo_os"],
        tipo_os_id=tipo_os_id,
        descricao=dados.get("descricao"),
        status="rascunho",
        criado_por=usuario.id
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Template criado: ID={template.id}, nome={template.nome}, unidade_id={unidade_id}")
    return template


def atualizar_template(
    db: Session,
    template_id: int,
    dados: Dict[str, Any],
    usuario: ComumUsuario
) -> ManutencaoTemplateOS:
    """
    Atualiza um template
    
    - Templates em rascunho: podem ser editados normalmente
    - Templates publicados: podem ser editados, mas voltam para rascunho
    - Templates arquivados: não podem ser editados
    
    Args:
        db: Sessão do banco de dados
        template_id: ID do template
        dados: Dados para atualizar
        usuario: Usuário atualizador
        
    Returns:
        ManutencaoTemplateOS: Template atualizado
    """
    template = db.query(ManutencaoTemplateOS).filter(
        ManutencaoTemplateOS.id == template_id,
        ManutencaoTemplateOS.tenant_id == usuario.tenant_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )
    
    # Templates publicados podem ser editados, mas voltam para rascunho
    # Templates arquivados não podem ser editados
    if template.status == "arquivado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Templates arquivados não podem ser editados"
        )
    
    # Se template está publicado, voltar para rascunho ao editar
    if template.status == "publicado":
        template.status = "rascunho"
        logger.info(f"Template {template_id} voltou para rascunho para edição")
    
    # Validar escopo hierárquico
    unidade_id = dados.get("unidade_id", template.unidade_id)
    if unidade_id is not None:
        pode_acessar, mensagem = validar_escopo_unidade(usuario, unidade_id, db)
        if not pode_acessar:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Não pode editar template para unidade {unidade_id}: {mensagem}"
            )
    
    if usuario.papel_organizacional == "gestor_unidade":
        if unidade_id is not None and unidade_id != usuario.unidade_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Só pode editar templates da sua unidade"
            )
    
    # Validar tipo_os_id se fornecido (verificar constraint única)
    if "tipo_os_id" in dados and dados["tipo_os_id"] is not None:
        tipo_os_id = dados["tipo_os_id"]
        # Verificar se já existe outro template padrão para mesma combinação
        template_existente = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.tenant_id == template.tenant_id,
            ManutencaoTemplateOS.unidade_id == template.unidade_id,
            ManutencaoTemplateOS.tipo_os_id == tipo_os_id,
            ManutencaoTemplateOS.id != template.id,
            ManutencaoTemplateOS.ativo == True
        ).first()
        
        if template_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um template padrão para este tipo de OS nesta unidade: {template_existente.nome}"
            )
    
    # Atualizar campos
    if "nome" in dados:
        template.nome = dados["nome"]
    if "tipo_os" in dados:
        template.tipo_os = dados["tipo_os"]
    if "tipo_os_id" in dados:
        template.tipo_os_id = dados["tipo_os_id"]
    if "descricao" in dados:
        template.descricao = dados["descricao"]
    if "unidade_id" in dados:
        template.unidade_id = dados["unidade_id"]
    
    template.atualizado_por = usuario.id
    
    db.commit()
    db.refresh(template)
    
    logger.info(f"Template atualizado: ID={template.id}")
    return template


def publicar_template(
    db: Session,
    template_id: int,
    versao: str,
    schema_json: Dict[str, Any],
    usuario: ComumUsuario
) -> ManutencaoVersaoTemplateOS:
    """
    Publica um template criando nova versão
    
    Args:
        db: Sessão do banco de dados
        template_id: ID do template
        versao: Versão a ser criada (ex: "1.0", "1.1", "2.0")
        schema_json: Schema JSON completo do formulário
        usuario: Usuário publicador
        
    Returns:
        ManutencaoVersaoTemplateOS: Nova versão criada
    """
    template = db.query(ManutencaoTemplateOS).filter(
        ManutencaoTemplateOS.id == template_id,
        ManutencaoTemplateOS.tenant_id == usuario.tenant_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )
    
    # Validar schema antes de publicar
    valido, erros = validar_schema(schema_json)
    if not valido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Schema inválido: {', '.join(erros)}"
        )
    
    # Verificar se versão já existe
    versao_existente = db.query(ManutencaoVersaoTemplateOS).filter(
        ManutencaoVersaoTemplateOS.template_id == template_id,
        ManutencaoVersaoTemplateOS.versao == versao
    ).first()
    
    if versao_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Versão {versao} já existe para este template"
        )
    
    # Encerrar versão anterior (se houver)
    versao_anterior = db.query(ManutencaoVersaoTemplateOS).filter(
        ManutencaoVersaoTemplateOS.template_id == template_id,
        ManutencaoVersaoTemplateOS.data_fim_vigencia.is_(None)
    ).first()
    
    if versao_anterior:
        versao_anterior.data_fim_vigencia = datetime.now()
    
    # Criar nova versão
    nova_versao = ManutencaoVersaoTemplateOS(
        template_id=template_id,
        versao=versao,
        schema_json=schema_json,
        data_inicio_vigencia=datetime.now(),
        data_fim_vigencia=None,  # Versão atual
        publicado_por=usuario.id,
        publicado_em=datetime.now(),
        criado_por=usuario.id
    )
    
    db.add(nova_versao)
    
    # Atualizar status do template para publicado
    template.status = "publicado"
    template.atualizado_por = usuario.id
    
    db.commit()
    db.refresh(nova_versao)
    
    logger.info(f"Template publicado: ID={template_id}, versão={versao}")
    return nova_versao


def obter_versao_atual(
    db: Session,
    template_id: int
) -> Optional[ManutencaoVersaoTemplateOS]:
    """
    Obtém a versão atual (vigente) do template
    
    Args:
        db: Sessão do banco de dados
        template_id: ID do template
        
    Returns:
        ManutencaoVersaoTemplateOS ou None se não houver versão vigente
    """
    return db.query(ManutencaoVersaoTemplateOS).filter(
        ManutencaoVersaoTemplateOS.template_id == template_id,
        ManutencaoVersaoTemplateOS.data_fim_vigencia.is_(None)
    ).first()


def validar_schema(schema_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Valida estrutura básica do schema JSON
    
    Args:
        schema_json: Schema JSON a validar
        
    Returns:
        Tuple[bool, List[str]]: (valido, lista_de_erros)
    """
    erros = []
    
    if not isinstance(schema_json, dict):
        return False, ["schema_json deve ser um objeto JSON"]
    
    # Validar estrutura básica
    if "layout" not in schema_json:
        erros.append("Campo 'layout' obrigatório no schema")
    
    if "campos" not in schema_json:
        erros.append("Campo 'campos' obrigatório no schema")
    elif not isinstance(schema_json["campos"], list):
        erros.append("Campo 'campos' deve ser uma lista")
    
    if "secoes" not in schema_json:
        erros.append("Campo 'secoes' obrigatório no schema")
    elif not isinstance(schema_json["secoes"], list):
        erros.append("Campo 'secoes' deve ser uma lista")
    
    # Validar campos
    if "campos" in schema_json and isinstance(schema_json["campos"], list):
        for i, campo in enumerate(schema_json["campos"]):
            if not isinstance(campo, dict):
                erros.append(f"Campo {i} deve ser um objeto")
                continue
            
            if "id" not in campo:
                erros.append(f"Campo {i} deve ter 'id'")
            if "tipo" not in campo:
                erros.append(f"Campo {i} deve ter 'tipo'")
            if "label" not in campo:
                erros.append(f"Campo {i} deve ter 'label'")
    
    return len(erros) == 0, erros


def aplicar_template_em_os(
    db: Session,
    os_id: int,
    template_id: int
) -> ManutencaoOrdemServico:
    """
    Aplica template a uma OS
    
    Args:
        db: Sessão do banco de dados
        os_id: ID da OS
        template_id: ID do template
        
    Returns:
        ManutencaoOrdemServico: OS atualizada
    """
    os = db.query(ManutencaoOrdemServico).filter(
        ManutencaoOrdemServico.id == os_id
    ).first()
    
    if not os:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OS não encontrada"
        )
    
    template = db.query(ManutencaoTemplateOS).filter(
        ManutencaoTemplateOS.id == template_id,
        ManutencaoTemplateOS.tenant_id == os.tenant_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )
    
    # Validar compatibilidade de escopo
    # Template corporativo pode ser usado por qualquer unidade
    # Template de unidade só pode ser usado por OS da mesma unidade
    if template.unidade_id is not None:
        if os.unidade_id != template.unidade_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template de unidade só pode ser usado por OS da mesma unidade"
            )
    
    # Obter versão atual do template
    versao_atual = obter_versao_atual(db, template_id)
    if not versao_atual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template não possui versão publicada"
        )
    
    # Aplicar template
    os.template_id = template_id
    os.template_versao_id = versao_atual.id
    os.schema_snapshot_json = versao_atual.schema_json  # Snapshot para auditoria
    os.dados_formulario_json = {}  # Inicializar dados vazios
    
    db.commit()
    db.refresh(os)
    
    logger.info(f"Template aplicado à OS: OS_ID={os_id}, Template_ID={template_id}, Versão={versao_atual.versao}")
    return os


def filtrar_templates_por_escopo(
    db: Session,
    usuario: ComumUsuario,
    filtros: Dict[str, Any]
) -> List[ManutencaoTemplateOS]:
    """
    Filtra templates por escopo hierárquico do usuário
    
    Args:
        db: Sessão do banco de dados
        usuario: Usuário para filtrar
        filtros: Filtros adicionais (tipo_os, status, etc.)
        
    Returns:
        List[ManutencaoTemplateOS]: Lista de templates filtrados
    """
    query = db.query(ManutencaoTemplateOS).filter(
        ManutencaoTemplateOS.tenant_id == usuario.tenant_id,
        ManutencaoTemplateOS.ativo == True
    )
    
    # Aplicar filtros adicionais
    if "tipo_os" in filtros:
        query = query.filter(ManutencaoTemplateOS.tipo_os == filtros["tipo_os"])
    if "status" in filtros:
        query = query.filter(ManutencaoTemplateOS.status == filtros["status"])
    
    # Aplicar filtro hierárquico
    if usuario.papel_organizacional == "gerente_corporativo":
        # GERENTE_CORPORATIVO vê todos (sem filtro adicional)
        logger.info("GERENTE_CORPORATIVO: retornando todos os templates (sem filtro de unidade)")
        pass
    elif usuario.papel_organizacional == "solicitante":
        # SOLICITANTE vê APENAS templates de sua unidade (NÃO vê corporativos)
        unidades_acessiveis = get_unidades_usuario(usuario, db, incluir_filhas=False)
        logger.info(f"SOLICITANTE {usuario.id}: unidades acessíveis = {unidades_acessiveis}")
        
        if unidades_acessiveis:
            # Apenas templates de suas unidades (NÃO corporativos)
            query = query.filter(ManutencaoTemplateOS.unidade_id.in_(unidades_acessiveis))
            logger.info(f"Filtro SOLICITANTE aplicado: unidade_id IN {unidades_acessiveis} (SEM templates corporativos)")
        else:
            # Solicitante sem unidade: não vê nenhum template
            query = query.filter(False)  # Retorna vazio
            logger.warning(f"SOLICITANTE {usuario.id} sem unidade - não verá nenhum template")
    else:
        # Outros perfis (gestor_unidade, coordenador, etc): vê corporativos + suas unidades
        unidades_acessiveis = get_unidades_usuario(usuario, db, incluir_filhas=False)
        logger.info(f"Usuário {usuario.id} ({usuario.papel_organizacional}): unidades acessíveis = {unidades_acessiveis}")
        
        # IMPORTANTE: Templates de unidade específica só aparecem para usuários dessa unidade
        # Templates corporativos (unidade_id=None) aparecem para gestores e acima
        query = query.filter(
            or_(
                ManutencaoTemplateOS.unidade_id.is_(None),  # Corporativos (todas unidades)
                ManutencaoTemplateOS.unidade_id.in_(unidades_acessiveis)  # Apenas suas unidades
            )
        )
        
        # Log adicional para debug de filtro
        logger.info(f"Filtro aplicado: unidade_id IS NULL OR unidade_id IN {unidades_acessiveis}")
    
    templates_resultado = query.all()
    logger.info(f"Templates encontrados para usuário {usuario.id}: {len(templates_resultado)} templates")
    
    # Validação pós-query: garantir que apenas templates corretos são retornados
    templates_filtrados = []
    unidades_usuario_validacao = get_unidades_usuario(usuario, db, incluir_filhas=False)
    
    for t in templates_resultado:
        # SOLICITANTE: não vê templates corporativos, apenas de sua unidade
        if usuario.papel_organizacional == "solicitante":
            if t.unidade_id is None:
                # Solicitante não deve ver templates corporativos
                logger.info(f"  ✗ REMOVENDO Template ID={t.id} (unidade_id=None) - SOLICITANTE não vê templates corporativos")
                continue
            elif t.unidade_id in unidades_usuario_validacao:
                templates_filtrados.append(t)
                logger.info(f"  ✓ Template ID={t.id}, nome={t.nome}, unidade_id={t.unidade_id} (acessível para solicitante)")
            else:
                logger.error(f"  ✗ REMOVENDO Template ID={t.id} (unidade_id={t.unidade_id}) - solicitante {usuario.id} não tem acesso! Unidades do usuário: {unidades_usuario_validacao}")
        else:
            # Outros perfis: templates corporativos aparecem para todos
            if t.unidade_id is None:
                templates_filtrados.append(t)
                logger.info(f"  ✓ Template ID={t.id}, nome={t.nome}, unidade_id=None (corporativo)")
            # Templates de unidade específica só aparecem para usuários dessa unidade
            elif t.unidade_id in unidades_usuario_validacao:
                templates_filtrados.append(t)
                logger.info(f"  ✓ Template ID={t.id}, nome={t.nome}, unidade_id={t.unidade_id} (acessível)")
            else:
                # Template não deveria aparecer - remover da lista
                logger.error(f"  ✗ REMOVENDO Template ID={t.id} (unidade_id={t.unidade_id}) - usuário {usuario.id} não tem acesso! Unidades do usuário: {unidades_usuario_validacao}")
    
    logger.info(f"Templates finais após validação para usuário {usuario.id}: {len(templates_filtrados)} templates")
    
    return templates_filtrados


def duplicar_template(
    db: Session,
    template_id: int,
    dados: Dict[str, Any],
    usuario: ComumUsuario
) -> ManutencaoTemplateOS:
    """
    Duplica um template existente para uma nova unidade ou com novo nome
    
    Args:
        db: Sessão do banco de dados
        template_id: ID do template original
        dados: Dados da duplicação (nome, unidade_id)
        usuario: Usuário que está duplicando
        
    Returns:
        ManutencaoTemplateOS: Template duplicado
        
    Raises:
        HTTPException: Se template não encontrado, sem permissão ou nome duplicado
    """
    # Buscar template original
    template_original = db.query(ManutencaoTemplateOS).filter(
        ManutencaoTemplateOS.id == template_id,
        ManutencaoTemplateOS.tenant_id == usuario.tenant_id
    ).first()
    
    if not template_original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )
    
    # Validar acesso ao template original
    if usuario.papel_organizacional != "gerente_corporativo":
        unidades_acessiveis = get_unidades_usuario(usuario, db, incluir_filhas=False)
        if template_original.unidade_id is not None and template_original.unidade_id not in unidades_acessiveis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para acessar este template"
            )
    
    # Validar permissão para criar template na unidade de destino
    unidade_id_destino = dados.get("unidade_id")
    
    # Log detalhado do valor recebido
    logger.info(f"🔍 Valor de unidade_id_destino recebido: {unidade_id_destino} (tipo={type(unidade_id_destino).__name__})")
    
    if unidade_id_destino is not None:
        pode_acessar, mensagem = validar_escopo_unidade(usuario, unidade_id_destino, db)
        if not pode_acessar:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Não pode criar template para unidade {unidade_id_destino}: {mensagem}"
            )
    
    # Para GESTOR_UNIDADE, só permite duplicar para sua unidade
    if usuario.papel_organizacional == "gestor_unidade":
        if unidade_id_destino is not None and unidade_id_destino != usuario.unidade_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Só pode duplicar templates para sua unidade"
            )
    
    # Verificar se já existe template com mesmo nome na unidade de destino
    query = db.query(ManutencaoTemplateOS).filter(
        ManutencaoTemplateOS.tenant_id == usuario.tenant_id,
        ManutencaoTemplateOS.nome == dados["nome"]
    )
    if unidade_id_destino is None:
        query = query.filter(ManutencaoTemplateOS.unidade_id.is_(None))
    else:
        query = query.filter(ManutencaoTemplateOS.unidade_id == unidade_id_destino)
    
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe template com nome '{dados['nome']}' para este escopo"
        )
    
    # Criar novo template (sempre inicia como rascunho)
    template_duplicado = ManutencaoTemplateOS(
        tenant_id=usuario.tenant_id,
        unidade_id=unidade_id_destino,
        nome=dados["nome"],
        tipo_os=template_original.tipo_os,  # Mantém o mesmo tipo_os
        descricao=template_original.descricao,  # Copia descrição
        status="rascunho",  # Sempre inicia como rascunho
        ativo=True,  # IMPORTANTE: Template deve estar ativo para aparecer na listagem
        criado_por=usuario.id
    )
    
    db.add(template_duplicado)
    db.flush()  # Para obter o ID do template duplicado
    
    # Copiar todas as versões do template original
    versoes_originais = db.query(ManutencaoVersaoTemplateOS).filter(
        ManutencaoVersaoTemplateOS.template_id == template_id
    ).order_by(ManutencaoVersaoTemplateOS.data_inicio_vigencia).all()
    
    for versao_original in versoes_originais:
        # Fazer cópia profunda do schema_json para evitar referências compartilhadas
        schema_json_copiado = None
        
        if versao_original.schema_json:
            try:
                if isinstance(versao_original.schema_json, dict):
                    # Se já é um dict, fazer deep copy
                    schema_json_copiado = copy.deepcopy(versao_original.schema_json)
                elif isinstance(versao_original.schema_json, str):
                    # Se é string, parsear e copiar
                    parsed = json.loads(versao_original.schema_json)
                    schema_json_copiado = copy.deepcopy(parsed)
                else:
                    # Tentar serializar e deserializar para garantir cópia
                    schema_json_copiado = json.loads(json.dumps(versao_original.schema_json, default=str))
                
                # Log detalhado da estrutura copiada
                num_campos = len(schema_json_copiado.get("campos", [])) if isinstance(schema_json_copiado, dict) else 0
                num_secoes = len(schema_json_copiado.get("secoes", [])) if isinstance(schema_json_copiado, dict) else 0
                num_blocos_repetiveis = len(schema_json_copiado.get("blocos_repetiveis", [])) if isinstance(schema_json_copiado, dict) else 0
                logger.info(f"Schema copiado - Campos: {num_campos}, Seções: {num_secoes}, Blocos Repetíveis: {num_blocos_repetiveis}")
                
                # Verificar se há campos ou blocos no schema
                if isinstance(schema_json_copiado, dict):
                    # Log dos primeiros campos para debug
                    if num_campos > 0:
                        primeiros_campos = schema_json_copiado.get("campos", [])[:3]
                        logger.info(f"Primeiros campos copiados: {[c.get('id', 'N/A') for c in primeiros_campos if isinstance(c, dict)]}")
                    if num_blocos_repetiveis > 0:
                        logger.info(f"Blocos repetíveis copiados: {num_blocos_repetiveis} blocos")
                        # Log dos IDs dos blocos repetíveis
                        blocos_ids = [b.get('id', 'N/A') for b in schema_json_copiado.get("blocos_repetiveis", []) if isinstance(b, dict)]
                        logger.info(f"IDs dos blocos repetíveis: {blocos_ids[:5]}")  # Primeiros 5
                
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Erro ao copiar schema_json da versão {versao_original.versao}: {e}")
                # Em caso de erro, usar o valor original (melhor que perder os dados)
                schema_json_copiado = versao_original.schema_json
        else:
            # Se schema_json é None ou vazio, usar um schema vazio padrão
            schema_json_copiado = {"layout": "column", "secoes": [], "campos": []}
            logger.warning(f"Versão {versao_original.versao} não possui schema_json, usando schema vazio")
        
        # Criar nova versão copiando dados da original
        nova_versao = ManutencaoVersaoTemplateOS(
            template_id=template_duplicado.id,
            versao=versao_original.versao,  # Mantém número de versão
            schema_json=schema_json_copiado,  # Copia profunda do schema JSON
            data_inicio_vigencia=versao_original.data_inicio_vigencia,
            data_fim_vigencia=versao_original.data_fim_vigencia,  # Copia datas de vigência
            publicado_por=versao_original.publicado_por,  # Preserva histórico
            publicado_em=versao_original.publicado_em,
            criado_por=usuario.id  # Novo criador é quem duplicou
        )
        
        db.add(nova_versao)
        
        # Log para debug
        schema_size = len(json.dumps(schema_json_copiado, default=str)) if schema_json_copiado else 0
        logger.info(f"Versão {versao_original.versao} copiada: schema_json tem {schema_size} caracteres, tipo={type(schema_json_copiado).__name__}")
    
    try:
        db.commit()
        db.refresh(template_duplicado)
        
        # Verificar quantas versões foram copiadas
        versoes_copiadas = db.query(ManutencaoVersaoTemplateOS).filter(
            ManutencaoVersaoTemplateOS.template_id == template_duplicado.id
        ).count()
        
        # Verificar se o template está ativo
        template_verificacao = db.query(ManutencaoTemplateOS).filter(
            ManutencaoTemplateOS.id == template_duplicado.id
        ).first()
        
        # Verificar unidades acessíveis do usuário para debug
        unidades_acessiveis = get_unidades_usuario(usuario, db, incluir_filhas=False)
        
        logger.info(f"Template duplicado: Original ID={template_id}, Novo ID={template_duplicado.id}, nome={template_duplicado.nome}, unidade_id={unidade_id_destino}, ativo={template_verificacao.ativo if template_verificacao else 'N/A'}, {versoes_copiadas} versões copiadas")
        logger.info(f"Usuário {usuario.id} ({usuario.papel_organizacional}): unidades acessíveis = {unidades_acessiveis}")
        if unidade_id_destino is not None:
            if unidade_id_destino in unidades_acessiveis:
                logger.info(f"✓ Unidade {unidade_id_destino} está acessível para o usuário - template aparecerá na listagem")
            else:
                logger.warning(f"⚠ Unidade {unidade_id_destino} NÃO está acessível para o usuário - template NÃO aparecerá na listagem!")
        else:
            logger.info("✓ Template corporativo (unidade_id=None) - aparecerá para todos")
        
        if not template_verificacao or not template_verificacao.ativo:
            logger.error(f"ERRO: Template duplicado {template_duplicado.id} não está ativo após commit!")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar template duplicado: template não está ativo"
            )
        
        # ============================================================================
        # AUTOMATIZAÇÃO: Garantir documento OS_CORRETIVA_IMPREVISTA para unidade destino
        # ============================================================================
        if unidade_id_destino is not None:
            from app.models.manutencao import ManutencaoDocumentoFormulario
            from app.services.documentos_formularios_service import (
                DEFAULT_TIPO_OBJETO_OS,
                criar_versao_documento_com_vigencia,
                obter_documento_por_chave,
            )
            from app.services.os_corretiva_blocos_contrato import DOCUMENTO_CHAVE
            
            try:
                # Verificar se documento já existe
                doc_existente = obter_documento_por_chave(
                    db, 
                    tenant_id=usuario.tenant_id,
                    unidade_id=unidade_id_destino,
                    chave=DOCUMENTO_CHAVE,  # "OS_CORRETIVA_IMPREVISTA"
                    tipo_objeto=DEFAULT_TIPO_OBJETO_OS,
                    somente_ativo=True
                )
                
                if not doc_existente:
                    # Obter versão atual do template duplicado (se existir)
                    versao_atual_duplicado = obter_versao_atual(db, template_duplicado.id)
                    template_id_doc = template_duplicado.id if versao_atual_duplicado else None
                    template_versao_id_doc = versao_atual_duplicado.id if versao_atual_duplicado else None
                    
                    logger.info(f"📄 Criando documento {DOCUMENTO_CHAVE} para unidade {unidade_id_destino}")
                    
                    # Criar documento
                    novo_doc = ManutencaoDocumentoFormulario(
                        tenant_id=usuario.tenant_id,
                        unidade_id=unidade_id_destino,
                        chave=DOCUMENTO_CHAVE,
                        tipo_objeto=DEFAULT_TIPO_OBJETO_OS,
                        titulo="Ordem de Serviço - Corretiva Imprevista",
                        codigo_documento="RSGM078/SIF2960",  # Padrão, pode ser configurável no futuro
                        descricao="Documento base para OS corretivas imprevistas",
                        ativo=True,
                        criado_por=usuario.id
                    )
                    
                    db.add(novo_doc)
                    db.flush()  # Para obter ID
                    
                    # Criar versão vigente
                    criar_versao_documento_com_vigencia(
                        db,
                        tenant_id=usuario.tenant_id,
                        documento_id=novo_doc.id,
                        versao_documento="01/2026",  # Padrão inicial (formato MM/YYYY)
                        data_revisao_documento=None,
                        numero_revisao=1,
                        vigencia_inicio=now_brasil_naive(),
                        vigencia_fim=None,  # Versão vigente (sem fim)
                        criado_por=usuario.id,
                        template_id=template_id_doc,
                        template_versao_id=template_versao_id_doc
                    )
                    
                    db.commit()  # Commit do documento e versão
                    
                    logger.info(f"✅ Documento {DOCUMENTO_CHAVE} criado para unidade {unidade_id_destino} com versão vigente (ID={novo_doc.id})")
                else:
                    logger.info(f"✓ Documento {DOCUMENTO_CHAVE} já existe para unidade {unidade_id_destino} (ID={doc_existente.id})")
                    
            except Exception as e:
                # Log erro mas não falhar a duplicação (documento pode ser criado depois manualmente)
                logger.warning(f"⚠ Não foi possível criar documento automaticamente para unidade {unidade_id_destino}: {e}")
                # Não fazer rollback - template já foi duplicado com sucesso
        
        return template_duplicado
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao fazer commit do template duplicado: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar template duplicado no banco de dados: {str(e)}"
        )
