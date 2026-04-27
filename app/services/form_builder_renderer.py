# -*- coding: utf-8 -*-
"""
PDV Ibix - Renderizador Centralizado de Form Builder
Serviço centralizado para renderização de formulários dinâmicos
Adaptado para o contexto do PDV Ibix (processos, aferições, certificados)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def render_form(
    template_schema: Dict[str, Any],
    dados: Optional[Dict[str, Any]] = None,
    contexto: Optional[Dict[str, Any]] = None,
    modo: str = "edicao"
) -> Dict[str, Any]:
    """
    Renderiza formulário completo a partir de template schema
    
    Args:
        template_schema: Schema JSON do template
        dados: Dados preenchidos do formulário (opcional)
        contexto: Contexto adicional (processo, aferição, certificado, usuario, etc.)
        modo: Modo de renderização (criacao, edicao, visualizacao)
        
    Returns:
        Dict com html, campos e validacoes
    """
    try:
        dados = dados or {}
        contexto = contexto or {}
        
        # Estrutura base do resultado
        resultado = {
            "html": "",
            "campos": [],
            "validacoes": {},
            "layout": template_schema.get("layout", "column"),
            "modo": modo
        }
        
        # Renderizar seções
        secoes = template_schema.get("secoes", [])
        campos_schema = template_schema.get("campos", [])
        
        # Criar mapa de campos por ID
        campos_map = {campo["id"]: campo for campo in campos_schema}
        
        html_parts = []
        campos_renderizados = []
        
        # Renderizar cada seção
        for secao in sorted(secoes, key=lambda s: s.get("ordem", 0)):
            secao_html, secao_campos = _render_secao(
                secao=secao,
                campos_map=campos_map,
                dados=dados,
                contexto=contexto,
                modo=modo
            )
            html_parts.append(secao_html)
            campos_renderizados.extend(secao_campos)
        
        resultado["html"] = "\n".join(html_parts)
        resultado["campos"] = campos_renderizados
        
        # Gerar validações
        resultado["validacoes"] = _gerar_validacoes(template_schema, dados, contexto)
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao renderizar formulário: {e}", exc_info=e)
        raise


def _render_secao(
    secao: Dict[str, Any],
    campos_map: Dict[str, Any],
    dados: Dict[str, Any],
    contexto: Dict[str, Any],
    modo: str
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Renderiza uma seção do formulário
    
    Returns:
        Tuple (html_secao, lista_campos_renderizados)
    """
    titulo = secao.get("titulo", "Sem título")
    secao_id = secao.get("id", "")
    campo_ids = secao.get("campos", [])
    
    html = f'<div class="form-builder-secao" data-secao-id="{secao_id}">'
    html += '<div class="form-builder-secao-header">'
    html += f'<h5 class="secao-titulo">{titulo}</h5>'
    html += '</div>'
    html += '<div class="form-builder-secao-body">'
    
    campos_renderizados = []
    
    # Renderizar campos da seção
    for campo_id in campo_ids:
        if campo_id in campos_map:
            campo_schema = campos_map[campo_id]
            campo_html, campo_data = render_field(
                campo_schema=campo_schema,
                valor=dados.get(campo_id),
                contexto=contexto,
                modo=modo
            )
            html += campo_html
            campos_renderizados.append(campo_data)
    
    html += '</div>'
    html += '</div>'
    
    return html, campos_renderizados


def render_field(
    campo_schema: Dict[str, Any],
    valor: Any = None,
    contexto: Optional[Dict[str, Any]] = None,
    modo: str = "edicao"
) -> tuple[str, Dict[str, Any]]:
    """
    Renderiza um campo individual
    
    Args:
        campo_schema: Schema do campo
        valor: Valor atual do campo
        contexto: Contexto adicional
        modo: Modo de renderização
        
    Returns:
        Tuple (html_campo, dados_campo)
    """
    contexto = contexto or {}
    
    campo_id = campo_schema.get("id", "")
    campo_tipo = campo_schema.get("tipo", "text")
    campo_label = campo_schema.get("label", "")
    obrigatorio = campo_schema.get("obrigatorio", False)
    config = campo_schema.get("config", {})
    
    # Resolver valor (pode vir de bindings)
    valor_resolvido = _resolver_valor_campo(campo_schema, valor, contexto)
    
    # Gerar HTML do campo
    html = f'<div class="form-builder-campo" data-campo-id="{campo_id}" data-tipo="{campo_tipo}">'
    
    # Label
    label_class = "form-label"
    if obrigatorio:
        label_class += " required"
    html += f'<label for="{campo_id}" class="{label_class}">{campo_label}'
    if obrigatorio:
        html += ' <span class="text-danger">*</span>'
    html += '</label>'
    
    # Input baseado no tipo
    html += _render_input_por_tipo(campo_schema, campo_id, valor_resolvido, modo)
    
    # Mensagem de ajuda
    ajuda = campo_schema.get("ajuda") or config.get("help")
    if ajuda:
        html += f'<small class="form-text text-muted">{ajuda}</small>'
    
    html += '</div>'
    
    # Dados do campo
    campo_data = {
        "id": campo_id,
        "tipo": campo_tipo,
        "label": campo_label,
        "valor": valor_resolvido,
        "obrigatorio": obrigatorio,
        "modo": modo
    }
    
    return html, campo_data


def _render_input_por_tipo(
    campo_schema: Dict[str, Any],
    campo_id: str,
    valor: Any,
    modo: str
) -> str:
    """Renderiza input HTML baseado no tipo do campo"""
    campo_tipo = campo_schema.get("tipo", "text")
    config = campo_schema.get("config", {})
    readonly = modo == "visualizacao" or campo_schema.get("readonly", False)
    
    input_class = "form-control"
    if readonly:
        input_class += " form-control-plaintext"
    
    if campo_tipo == "text":
        return f'<input type="text" id="{campo_id}" name="{campo_id}" class="{input_class}" value="{valor or ""}" {"readonly" if readonly else ""}>'
    
    elif campo_tipo == "number":
        min_val = config.get("min")
        max_val = config.get("max")
        min_attr = f' min="{min_val}"' if min_val is not None else ""
        max_attr = f' max="{max_val}"' if max_val is not None else ""
        return f'<input type="number" id="{campo_id}" name="{campo_id}" class="{input_class}" value="{valor or ""}"{min_attr}{max_attr} {"readonly" if readonly else ""}>'
    
    elif campo_tipo == "date":
        valor_date = valor.strftime("%Y-%m-%d") if isinstance(valor, datetime) else (valor or "")
        return f'<input type="date" id="{campo_id}" name="{campo_id}" class="{input_class}" value="{valor_date}" {"readonly" if readonly else ""}>'
    
    elif campo_tipo == "textarea":
        rows = config.get("rows", 3)
        return f'<textarea id="{campo_id}" name="{campo_id}" class="{input_class}" rows="{rows}" {"readonly" if readonly else ""}>{valor or ""}</textarea>'
    
    elif campo_tipo == "select":
        opcoes = config.get("options", [])
        html = f'<select id="{campo_id}" name="{campo_id}" class="form-select" {"disabled" if readonly else ""}>'
        html += '<option value="">Selecione...</option>'
        for opcao in opcoes:
            opcao_val = opcao.get("value", opcao) if isinstance(opcao, dict) else opcao
            opcao_label = opcao.get("label", opcao_val) if isinstance(opcao, dict) else opcao
            selected = "selected" if str(opcao_val) == str(valor) else ""
            html += f'<option value="{opcao_val}" {selected}>{opcao_label}</option>'
        html += '</select>'
        return html
    
    elif campo_tipo == "boolean":
        checked = "checked" if valor else ""
        disabled = "disabled" if readonly else ""
        return f'<div class="form-check"><input type="checkbox" id="{campo_id}" name="{campo_id}" class="form-check-input" {checked} {disabled}><label class="form-check-label" for="{campo_id}">{campo_schema.get("label", "")}</label></div>'
    
    else:
        # Tipo padrão: text
        return f'<input type="text" id="{campo_id}" name="{campo_id}" class="{input_class}" value="{valor or ""}" {"readonly" if readonly else ""}>'


def _resolver_valor_campo(
    campo_schema: Dict[str, Any],
    valor: Any,
    contexto: Dict[str, Any]
) -> Any:
    """
    Resolve valor do campo, incluindo bindings dinâmicos
    
    Args:
        campo_schema: Schema do campo
        valor: Valor fornecido
        contexto: Contexto para resolução de bindings
        
    Returns:
        Valor resolvido
    """
    # Se já tem valor, usar ele
    if valor is not None:
        return valor
    
    # Tentar resolver binding
    binding = campo_schema.get("binding") or campo_schema.get("config", {}).get("binding")
    if binding:
        return resolve_bindings({campo_schema.get("id"): binding}, contexto).get(campo_schema.get("id"))
    
    # Valor padrão
    return campo_schema.get("default") or campo_schema.get("config", {}).get("default")


def validate_form(
    template_schema: Dict[str, Any],
    dados: Dict[str, Any],
    contexto: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Valida dados do formulário
    
    Args:
        template_schema: Schema JSON do template
        dados: Dados a validar
        contexto: Contexto adicional
        
    Returns:
        Dict com valido (bool) e erros (lista)
    """
    try:
        contexto = contexto or {}
        erros = []
        campos_schema = template_schema.get("campos", [])
        
        # Validar campos obrigatórios
        for campo in campos_schema:
            campo_id = campo.get("id")
            obrigatorio = campo.get("obrigatorio", False)
            
            if obrigatorio:
                valor = dados.get(campo_id)
                if valor is None or valor == "":
                    erros.append({
                        "campo": campo_id,
                        "mensagem": f"Campo '{campo.get('label', campo_id)}' é obrigatório"
                    })
        
        # Validar regras condicionais
        for campo in campos_schema:
            campo_id = campo.get("id")
            regras = campo.get("regras", [])
            
            for regra in regras:
                if not _validar_regra(regra, dados, contexto):
                    erros.append({
                        "campo": campo_id,
                        "mensagem": regra.get("mensagem", "Validação falhou")
                    })
        
        return {
            "valido": len(erros) == 0,
            "erros": erros
        }
        
    except Exception as e:
        logger.error(f"Erro ao validar formulário: {e}", exc_info=e)
        return {
            "valido": False,
            "erros": [{"campo": "geral", "mensagem": f"Erro na validação: {str(e)}"}]
        }


def _validar_regra(
    regra: Dict[str, Any],
    dados: Dict[str, Any],
    contexto: Dict[str, Any]
) -> bool:
    """Valida uma regra condicional"""
    tipo = regra.get("tipo")
    
    if tipo == "required_when":
        # Campo obrigatório quando outro campo tem valor
        campo_dependente = regra.get("campo")
        valor_condicao = dados.get(campo_dependente)
        if valor_condicao:
            campo_atual = regra.get("campo_atual")
            valor_atual = dados.get(campo_atual)
            return valor_atual is not None and valor_atual != ""
    
    elif tipo == "min":
        campo = regra.get("campo")
        valor = dados.get(campo)
        min_val = regra.get("valor")
        if valor is not None:
            try:
                return float(valor) >= float(min_val)
            except (ValueError, TypeError):
                return False
    
    elif tipo == "max":
        campo = regra.get("campo")
        valor = dados.get(campo)
        max_val = regra.get("valor")
        if valor is not None:
            try:
                return float(valor) <= float(max_val)
            except (ValueError, TypeError):
                return False
    
    # Regra não reconhecida, considerar válida
    return True


def _gerar_validacoes(
    template_schema: Dict[str, Any],
    dados: Dict[str, Any],
    contexto: Dict[str, Any]
) -> Dict[str, Any]:
    """Gera estrutura de validações para o formulário"""
    validacoes = {}
    campos_schema = template_schema.get("campos", [])
    
    for campo in campos_schema:
        campo_id = campo.get("id")
        validacoes[campo_id] = {
            "obrigatorio": campo.get("obrigatorio", False),
            "regras": campo.get("regras", [])
        }
    
    return validacoes


def resolve_bindings(
    bindings: Dict[str, str],
    contexto: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Resolve bindings dinâmicos (ex: processo.numero, usuario.nome)
    
    Args:
        bindings: Dict com campo_id -> expressao_binding
        contexto: Contexto para resolução
        
    Returns:
        Dict com campo_id -> valor_resolvido
    """
    resultados = {}
    
    for campo_id, expressao in bindings.items():
        try:
            # Resolver expressão simples (ex: "processo.numero")
            partes = expressao.split(".")
            if len(partes) == 2:
                objeto, propriedade = partes
                valor = contexto.get(objeto, {}).get(propriedade) if isinstance(contexto.get(objeto), dict) else getattr(contexto.get(objeto), propriedade, None)
                resultados[campo_id] = valor
            else:
                # Expressão direta
                resultados[campo_id] = contexto.get(expressao)
        except Exception as e:
            logger.warning(f"Erro ao resolver binding {expressao}: {e}")
            resultados[campo_id] = None
    
    return resultados
