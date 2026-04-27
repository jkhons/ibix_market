# -*- coding: utf-8 -*-
"""
REFERÊNCIA DO CERTILOG - Serviço de Renderização do Form Builder
Este arquivo é uma cópia de referência do sistema Certilog.
Não deve ser usado diretamente no PDV Ibix.
Adaptar conforme necessário para implementação futura.

Serviço de Renderização do Form Builder
Renderiza formulários dinâmicos a partir de schemas
"""

import logging
from typing import Any, Dict

from app.models.comum import ComumUsuario
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def renderizar_formulario(
    schema: Dict[str, Any],
    dados: Dict[str, Any],
    modo: str = "edicao"
) -> Dict[str, Any]:
    """
    Renderiza formulário a partir do schema
    
    Args:
        schema: Schema JSON do template
        dados: Dados preenchidos (opcional)
        modo: Modo de renderização (criacao, edicao, visualizacao)
        
    Returns:
        Dict[str, Any]: Estrutura renderizada do formulário
    """
    resultado = {
        "layout": schema.get("layout", "column"),
        "secoes": [],
        "modo": modo
    }
    
    # Renderizar seções
    secoes = schema.get("secoes", [])
    campos = schema.get("campos", [])
    
    # Criar mapa de campos por ID
    campos_map = {campo["id"]: campo for campo in campos}
    
    for secao in secoes:
        secao_renderizada = {
            "id": secao.get("id"),
            "titulo": secao.get("titulo"),
            "ordem": secao.get("ordem", 0),
            "campos": []
        }
        
        # Renderizar campos da seção
        campo_ids = secao.get("campos", [])
        for campo_id in campo_ids:
            if campo_id in campos_map:
                campo = campos_map[campo_id]
                campo_renderizado = renderizar_campo(campo, dados.get(campo_id), modo)
                secao_renderizada["campos"].append(campo_renderizado)
        
        resultado["secoes"].append(secao_renderizada)
    
    return resultado


def renderizar_campo(
    campo_schema: Dict[str, Any],
    valor: Any,
    modo: str = "edicao"
) -> Dict[str, Any]:
    """
    Renderiza um campo individual
    
    Args:
        campo_schema: Schema do campo
        valor: Valor atual do campo
        modo: Modo de renderização
        
    Returns:
        Dict[str, Any]: Campo renderizado
    """
    campo_renderizado = {
        "id": campo_schema.get("id"),
        "tipo": campo_schema.get("tipo"),
        "label": campo_schema.get("label"),
        "valor": valor,
        "obrigatorio": campo_schema.get("obrigatorio", False),
        "modo": modo
    }
    
    # Adicionar propriedades específicas por tipo
    if campo_schema.get("tipo") in ["select", "radio"]:
        # Buscar opções de config.options (Form Builder) ou opcoes direto (legado)
        config = campo_schema.get("config", {})
        opcoes = config.get("options", campo_schema.get("opcoes", []))
        campo_renderizado["opcoes"] = opcoes
    
    return campo_renderizado


def renderizar_bloco(
    bloco_schema: Dict[str, Any],
    dados: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Renderiza um bloco individual
    
    Args:
        bloco_schema: Schema do bloco
        dados: Dados do bloco
        
    Returns:
        Dict[str, Any]: Bloco renderizado
    """
    return {
        "tipo": bloco_schema.get("tipo"),
        "dados": dados,
        "schema": bloco_schema
    }


def aplicar_permissoes_rbac(
    schema: Dict[str, Any],
    usuario: ComumUsuario,
    db: Session
) -> Dict[str, Any]:
    """
    Filtra campos do schema por permissões RBAC do usuário
    
    Args:
        schema: Schema JSON do template
        usuario: Usuário atual
        db: Sessão do banco de dados
        
    Returns:
        Dict[str, Any]: Schema filtrado
    """
    # Por enquanto, retorna schema sem filtro
    # Implementação completa será feita conforme necessidade de permissões por campo
    return schema


def gerar_preview_template(schema: Dict[str, Any]) -> str:
    """
    Gera HTML de preview do template
    
    Args:
        schema: Schema JSON do template
        
    Returns:
        str: HTML de preview
    """
    html = "<div class='form-builder-preview'>"
    html += "<h3>Preview do Template</h3>"
    
    secoes = schema.get("secoes", [])
    for secao in secoes:
        html += f"<div class='secao'><h4>{secao.get('titulo', 'Sem título')}</h4>"
        html += "<div class='campos'>"
        html += f"<p>{len(secao.get('campos', []))} campos</p>"
        html += "</div></div>"
    
    html += "</div>"
    return html


def filtrar_templates_por_escopo(
    db: Session,
    usuario: ComumUsuario,
    filtros: Dict[str, Any]
):
    """
    Aplica filtros hierárquicos de unidades em queries de templates
    
    Args:
        db: Sessão do banco de dados
        usuario: Usuário para filtrar
        filtros: Filtros adicionais
        
    Returns:
        Query filtrada
    """
    from app.models.manutencao import ManutencaoTemplateOS
    from app.services.rbac_corporativo_service import get_unidades_usuario
    from sqlalchemy import or_
    
    query = db.query(ManutencaoTemplateOS).filter(
        ManutencaoTemplateOS.tenant_id == usuario.tenant_id,
        ManutencaoTemplateOS.ativo == True
    )
    
    # Aplicar filtro hierárquico
    if usuario.papel_organizacional == "gerente_corporativo":
        # GERENTE_CORPORATIVO vê todos
        pass
    else:
        # Outros perfis: vê corporativos + suas unidades
        unidades_acessiveis = get_unidades_usuario(usuario, db, incluir_filhas=False)
        query = query.filter(
            or_(
                ManutencaoTemplateOS.unidade_id.is_(None),
                ManutencaoTemplateOS.unidade_id.in_(unidades_acessiveis)
            )
        )
    
    return query
