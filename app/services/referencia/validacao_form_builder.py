# -*- coding: utf-8 -*-
"""
REFERÊNCIA DO CERTILOG - Serviço de Validação do Form Builder
Este arquivo é uma cópia de referência do sistema Certilog.
Não deve ser usado diretamente no PDV Ibix.
Adaptar conforme necessário para implementação futura.

Serviço de Validação do Form Builder
Valida campos obrigatórios, regras condicionais e transições de status
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.models.manutencao import ManutencaoOrdemServico, ManutencaoVersaoTemplateOS
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def validar_campos_obrigatorios(
    os: ManutencaoOrdemServico,
    status: str,
    db: Session
) -> List[str]:
    """
    Valida campos obrigatórios do template conforme status atual
    
    Args:
        os: Ordem de Serviço
        status: Status atual da OS
        db: Sessão do banco de dados
        
    Returns:
        List[str]: Lista de IDs de campos obrigatórios não preenchidos
    """
    campos_faltantes = []
    
    # Se não tem template, não há validação de campos do formulário
    if not os.template_id or not os.template_versao_id:
        return campos_faltantes
    
    # Obter schema do template
    versao = db.query(ManutencaoVersaoTemplateOS).filter(
        ManutencaoVersaoTemplateOS.id == os.template_versao_id
    ).first()
    
    if not versao:
        logger.warning(f"Versão de template não encontrada: {os.template_versao_id}")
        return campos_faltantes
    
    schema = versao.get_schema()
    dados_formulario = os.get_dados_formulario()
    
    # Obter regras por status se existirem
    regras_por_status = schema.get("regras_por_status", {})
    regras_status_atual = regras_por_status.get(status, {})
    campos_obrigatorios_por_status = regras_status_atual.get("campos_obrigatorios", [])
    
    # Validar campos obrigatórios
    campos = schema.get("campos", [])
    for campo in campos:
        campo_id = campo.get("id")
        obrigatorio = campo.get("obrigatorio", False)
        obrigatorio_por_status = campo.get("obrigatorio_por_status", [])
        
        # Verificar se é obrigatório (geral, por status no campo, ou por regras_por_status)
        is_obrigatorio = (
            obrigatorio or 
            status in obrigatorio_por_status or 
            campo_id in campos_obrigatorios_por_status
        )
        
        if is_obrigatorio:
            # Verificar se campo está preenchido
            valor = dados_formulario.get(campo_id)
            if valor is None or valor == "":
                campos_faltantes.append(campo_id)
    
    return campos_faltantes


def obter_regras_por_status(
    schema: Dict[str, Any],
    status: str
) -> Dict[str, Any]:
    """
    Obtém regras por status do schema
    
    Args:
        schema: Schema do template
        status: Status atual da OS
        
    Returns:
        Dict[str, Any]: Regras para o status (campos_obrigatorios, campos_visiveis, campos_editaveis)
    """
    regras_por_status = schema.get("regras_por_status", {})
    return regras_por_status.get(status, {})


def validar_visibilidade_campo(
    campo_id: str,
    status: str,
    schema: Dict[str, Any],
    perfil_usuario: Optional[str] = None
) -> bool:
    """
    Valida se campo deve ser visível conforme status e perfil
    
    Args:
        campo_id: ID do campo
        status: Status atual da OS
        schema: Schema do template
        perfil_usuario: Perfil RBAC do usuário
        
    Returns:
        bool: True se campo deve ser visível
    """
    campos = schema.get("campos", [])
    campo = next((c for c in campos if c.get("id") == campo_id), None)
    
    if not campo:
        return False
    
    # Verificar visibilidade por perfil
    visivel_por_perfil = campo.get("visivel_por_perfil", [])
    if visivel_por_perfil and perfil_usuario:
        if perfil_usuario not in visivel_por_perfil:
            return False
    
    # Verificar regras por status
    regras_status = obter_regras_por_status(schema, status)
    campos_visiveis = regras_status.get("campos_visiveis", [])
    
    # Se há lista de campos visíveis por status, verificar se campo está na lista
    if campos_visiveis:
        return campo_id in campos_visiveis
    
    # Se não há regras específicas, campo é visível
    return True


def validar_editabilidade_campo(
    campo_id: str,
    status: str,
    schema: Dict[str, Any],
    perfil_usuario: Optional[str] = None
) -> bool:
    """
    Valida se campo pode ser editado conforme status e perfil
    
    Args:
        campo_id: ID do campo
        status: Status atual da OS
        schema: Schema do template
        perfil_usuario: Perfil RBAC do usuário
        
    Returns:
        bool: True se campo pode ser editado
    """
    campos = schema.get("campos", [])
    campo = next((c for c in campos if c.get("id") == campo_id), None)
    
    if not campo:
        return False
    
    # Campos read-only nunca são editáveis
    if campo.get("tipo") == "texto_informativo" or campo.get("readonly", False):
        return False
    
    # Verificar editabilidade por perfil
    editavel_por_perfil = campo.get("editavel_por_perfil", [])
    if editavel_por_perfil and perfil_usuario:
        if perfil_usuario not in editavel_por_perfil:
            return False
    
    # Verificar regras por status
    regras_status = obter_regras_por_status(schema, status)
    campos_editaveis = regras_status.get("campos_editaveis", [])
    campos_readonly = regras_status.get("campos_readonly", [])
    
    # Se campo está na lista de readonly por status, não é editável
    if campos_readonly and campo_id in campos_readonly:
        return False
    
    # Se há lista de campos editáveis por status, verificar se campo está na lista
    if campos_editaveis:
        return campo_id in campos_editaveis
    
    # Se não há regras específicas, campo é editável
    return True


def validar_regras_condicionais(
    dados: Dict[str, Any],
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Aplica regras condicionais e retorna dados filtrados
    
    Args:
        dados: Dados do formulário
        schema: Schema do template
        
    Returns:
        Dict[str, Any]: Dados filtrados conforme regras condicionais
    """
    # Aplicar regras condicionais de cada campo
    campos = schema.get("campos", [])
    campos_visiveis = []
    
    for campo in campos:
        campo_id = campo.get("id")
        regras_condicionais = campo.get("regras_condicionais", [])
        
        # Se não há regras condicionais, campo é visível
        if not regras_condicionais:
            campos_visiveis.append(campo_id)
            continue
        
        # Avaliar cada regra condicional
        campo_deve_aparecer = True
        for regra in regras_condicionais:
            tipo = regra.get("tipo", "if")
            campo_ref = regra.get("campo")
            operador = regra.get("operador", "equals")
            valor_esperado = regra.get("valor")
            
            if campo_ref:
                valor_campo_ref = dados.get(campo_ref)
                
                if tipo == "if":
                    # Se condição não for atendida, campo não aparece
                    if operador == "equals":
                        if valor_campo_ref != valor_esperado:
                            campo_deve_aparecer = False
                            break
                    elif operador == "not_equals":
                        if valor_campo_ref == valor_esperado:
                            campo_deve_aparecer = False
                            break
                    elif operador == "in":
                        if valor_campo_ref not in valor_esperado:
                            campo_deve_aparecer = False
                            break
        
        if campo_deve_aparecer:
            campos_visiveis.append(campo_id)
    
    # Retornar apenas dados de campos visíveis
    return {k: v for k, v in dados.items() if k in campos_visiveis}


def validar_transicao_status(
    os: ManutencaoOrdemServico,
    novo_status: str,
    db: Session
) -> Tuple[bool, List[str]]:
    """
    Valida se pode transicionar para novo status
    
    Args:
        os: Ordem de Serviço
        novo_status: Novo status desejado
        db: Sessão do banco de dados
        
    Returns:
        Tuple[bool, List[str]]: (pode_transicionar, lista_de_campos_faltantes)
    """
    erros = []
    
    # Validar campos obrigatórios do template
    campos_faltantes = validar_campos_obrigatorios(os, novo_status, db)
    if campos_faltantes:
        erros.extend(campos_faltantes)
    
    # Validar checklist NC se houver template
    if os.template_id and os.template_versao_id:
        from app.models.manutencao import ManutencaoVersaoTemplateOS
        versao = db.query(ManutencaoVersaoTemplateOS).filter(
            ManutencaoVersaoTemplateOS.id == os.template_versao_id
        ).first()
        
        if versao:
            schema = versao.get_schema()
            dados_formulario = os.get_dados_formulario()
            
            # Validar checklist NC
            valido_nc, erros_nc = validar_checklist_nc(dados_formulario, schema)
            if not valido_nc:
                erros.extend(erros_nc)
            
            # Validar medida paliativa se status final for paliativo
            if novo_status == "encerrada":
                # Verificar se status final do serviço é medida paliativa
                status_final_campo = dados_formulario.get("status_final_servico", "")
                if status_final_campo == "medida_paliativa":
                    valido_paliativa, erros_paliativa = validar_medida_paliativa(dados_formulario, schema, status_final_campo)
                    if not valido_paliativa:
                        erros.extend(erros_paliativa)
    
    return len(erros) == 0, erros


def validar_checklist_nc(
    dados_formulario: Dict[str, Any],
    schema: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Valida se itens NC do checklist têm observação obrigatória
    
    Args:
        dados_formulario: Dados preenchidos no formulário
        schema: Schema do template
        
    Returns:
        Tuple[bool, List[str]]: (valido, lista_de_erros)
    """
    erros = []
    
    # Buscar blocos de checklist no schema
    campos = schema.get("campos", [])
    for campo in campos:
        if campo.get("tipo") == "checklist":
            campo_id = campo.get("id")
            checklist_data = dados_formulario.get(campo_id, {})
            
            # Se checklist_data é um dict com itens
            if isinstance(checklist_data, dict):
                itens = checklist_data.get("itens", [])
                for item in itens:
                    resposta = item.get("resposta")
                    observacao = item.get("observacao", "")
                    
                    # Se resposta é NC e não tem observação
                    if resposta == "NC" and not observacao:
                        item_id = item.get("id", "desconhecido")
                        erros.append(f"Item {item_id} do checklist {campo_id} marcado como NC exige observação")
    
    return len(erros) == 0, erros


def validar_medida_paliativa(
    dados_formulario: Dict[str, Any],
    schema: Dict[str, Any],
    status_final: str
) -> Tuple[bool, List[str]]:
    """
    Valida se medida paliativa tem justificativa obrigatória
    
    Args:
        dados_formulario: Dados preenchidos no formulário
        schema: Schema do template
        status_final: Status final do serviço
        
    Returns:
        Tuple[bool, List[str]]: (valido, lista_de_erros)
    """
    erros = []
    
    if status_final == "medida_paliativa":
        # Buscar campo de status final do serviço
        campos = schema.get("campos", [])
        for campo in campos:
            if campo.get("tipo") == "select" and "status_final" in campo.get("id", "").lower():
                campo.get("id")
                justificativa_id = campo.get("justificativa_campo_id")  # Campo de justificativa associado
                
                if justificativa_id:
                    justificativa = dados_formulario.get(justificativa_id, "")
                    if not justificativa:
                        erros.append(f"Medida paliativa exige justificativa no campo {justificativa_id}")
    
    return len(erros) == 0, erros


def _avaliar_expressao_simples(expressao: str, contexto: Dict[str, Any]) -> bool:
    """
    Avalia expressão simples (status, role) sem JavaScript
    
    Suporta apenas:
    - ctx.status == 'aberta'
    - ctx.status != 'aberta'
    - ctx.user.role == 'solicitante'
    - ctx.user.role != 'solicitante'
    
    Args:
        expressao: Expressão a avaliar (ex: "ctx.status == 'aberta'")
        contexto: Contexto com status e user.role
        
    Returns:
        bool: Resultado da avaliação
    """
    try:
        # Extrair status e role do contexto
        status = contexto.get("status", "")
        user = contexto.get("user", {})
        role = user.get("role", "") if isinstance(user, dict) else ""
        
        # Normalizar expressão (remover espaços extras)
        expr = expressao.strip()
        
        # Avaliar comparações simples de status
        if "ctx.status" in expr or ("status" in expr and "ctx." not in expr and "user" not in expr):
            if "==" in expr:
                partes = expr.split("==")
                if len(partes) == 2:
                    valor_esperado = partes[1].strip().strip("'\"")
                    return status == valor_esperado
            elif "!=" in expr:
                partes = expr.split("!=")
                if len(partes) == 2:
                    valor_esperado = partes[1].strip().strip("'\"")
                    return status != valor_esperado
        
        # Avaliar comparações simples de role
        if "ctx.user.role" in expr or ("user.role" in expr):
            if "==" in expr:
                partes = expr.split("==")
                if len(partes) == 2:
                    valor_esperado = partes[1].strip().strip("'\"")
                    return role == valor_esperado
            elif "!=" in expr:
                partes = expr.split("!=")
                if len(partes) == 2:
                    valor_esperado = partes[1].strip().strip("'\"")
                    return role != valor_esperado
        
        # Se não conseguir avaliar, retornar False (mais seguro)
        logger.warning(f"Expressão não suportada: {expressao}")
        return False
        
    except Exception as e:
        logger.error(f"Erro ao avaliar expressão {expressao}: {e}")
        return False


def _verificar_visibilidade_simples(campo: Dict[str, Any], contexto: Dict[str, Any]) -> bool:
    """
    Verifica se campo deve ser visível (avalia showWhen simples)
    
    Args:
        campo: Definição do campo
        contexto: Contexto com status e user.role
        
    Returns:
        bool: True se campo deve ser visível
    """
    # Se não tem render.showWhen, campo é visível
    render = campo.get("render", {})
    show_when = render.get("showWhen")
    
    if not show_when:
        return True
    
    # Se showWhen é array, verificar se alguma condição é verdadeira
    condicoes = show_when if isinstance(show_when, list) else [show_when]
    
    for condicao in condicoes:
        if isinstance(condicao, dict):
            expr_if = condicao.get("if", "")
            if expr_if and _avaliar_expressao_simples(expr_if, contexto):
                return True
        elif isinstance(condicao, str):
            if _avaliar_expressao_simples(condicao, contexto):
                return True
    
    return False


def _campo_vazio(campo: Dict[str, Any], valor: Any) -> bool:
    """
    Verifica se campo está vazio conforme tipo
    
    Args:
        campo: Definição do campo
        valor: Valor do campo
        
    Returns:
        bool: True se campo está vazio
    """
    tipo = campo.get("tipo", "")
    
    # Campo texto/number/select: null ou string vazia
    if tipo in ["text", "number", "select", "textarea", "date", "datetime", "hora"]:
        return valor is None or valor == "" or (isinstance(valor, list) and len(valor) == 0)
    
    # Campo tabela repetível: array vazio
    if tipo == "tabela":
        return valor is None or (isinstance(valor, list) and len(valor) == 0)
    
    # Campo checklist: sem resposta em itens obrigatórios
    if tipo == "checklist":
        if valor is None:
            return True
        if isinstance(valor, dict):
            itens = valor.get("itens", [])
            # Verificar se há pelo menos uma resposta
            for item in itens:
                if item.get("resposta"):
                    return False
            return True
        return False
    
    # Campo boolean: sempre considerado preenchido se existe
    if tipo == "boolean":
        return False
    
    # Padrão: null ou string vazia
    return valor is None or valor == ""


def validar_estrutura_basica(
    dados_formulario: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None
) -> None:
    """
    Valida apenas estrutura básica dos dados do formulário.
    
    ❌ NÃO valida requiredWhen de encerramento.
    Permite salvamento parcial durante execução.
    
    Valida:
    - Tipos de dados básicos
    - Estrutura de campos
    - Coerência básica
    
    Args:
        dados_formulario: Dados do formulário a validar
        schema: Schema do template (opcional, para validação de tipos)
        
    Raises:
        ValueError: Se estrutura básica estiver incorreta
    """
    if not isinstance(dados_formulario, dict):
        raise ValueError("dados_formulario deve ser um dicionário")
    
    # Validações básicas de estrutura
    # Se houver schema, validar tipos básicos
    if schema:
        campos = schema.get("campos", [])
        for campo in campos:
            campo_id = campo.get("id")
            if campo_id and campo_id in dados_formulario:
                valor = dados_formulario[campo_id]
                tipo_campo = campo.get("tipo", "")
                
                # Validações básicas de tipo
                if tipo_campo == "number" and valor is not None:
                    try:
                        float(valor)
                    except (ValueError, TypeError):
                        raise ValueError(f"Campo {campo_id} deve ser numérico")
                
                if tipo_campo == "boolean" and valor is not None:
                    if not isinstance(valor, bool):
                        raise ValueError(f"Campo {campo_id} deve ser booleano")
    
    # Estrutura básica válida
    return


def validar_campos_obrigatorios_por_status(
    os: ManutencaoOrdemServico,
    status: str,
    dados_formulario: Dict[str, Any],
    db: Session
) -> List[str]:
    """
    Valida campos obrigatórios por status usando requiredWhen.
    
    Valida TODOS os requiredWhen aplicáveis ao status atual.
    Usado no encerramento para garantir que todos os campos obrigatórios estão preenchidos.
    
    ⚠️ IMPORTANTE: Respeita showWhen - não valida campos ocultos.
    
    Args:
        os: Ordem de Serviço
        status: Status atual da OS (lowercase)
        dados_formulario: Dados do formulário
        db: Sessão do banco de dados
        
    Returns:
        List[str]: Lista de IDs de campos obrigatórios não preenchidos
    """
    campos_faltantes = []
    
    # ⚠️ REGRA DE OURO: Sempre usar schema_snapshot, nunca template ao vivo
    if not os.schema_snapshot_json:
        return campos_faltantes
    
    # Obter schema do snapshot (não template ao vivo)
    schema_snapshot = os.schema_snapshot_json
    if isinstance(schema_snapshot, str):
        import json
        schema_snapshot = json.loads(schema_snapshot)
    
    if not isinstance(schema_snapshot, dict):
        logger.warning(f"schema_snapshot da OS {os.id} não é um dict válido")
        return campos_faltantes
    
    # Criar contexto para validação (status sempre lowercase)
    contexto = {
        "status": status.lower() if status else "",
        "os": {"id": os.id},
        "user": {"role": "tecnico"}  # Contexto básico
    }
    
    # Validar usando requiredWhen (já respeita showWhen internamente)
    erros = validar_required_when(schema_snapshot, dados_formulario, contexto)
    
    # Converter erros em lista de campos faltantes
    campos_faltantes = list(erros.keys())
    
    return campos_faltantes


def validar_required_when(
    schema: Dict[str, Any],
    dados_formulario: Dict[str, Any],
    contexto: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Valida campos obrigatórios usando requiredWhen
    
    ⚠️ REGRA: Valida apenas campos visíveis (respeita showWhen primeiro).
    ⚠️ REGRA: Tipos complexos têm validação específica (tabela=[], checklist=nenhuma resposta).
    
    Suporta apenas regras simples (status, role, valor vazio).
    
    Args:
        schema: Schema do template
        dados_formulario: Dados preenchidos no formulário
        contexto: Contexto com status e user.role (ex: {"status": "aberta", "user": {"role": "solicitante"}})
        
    Returns:
        Dict[str, List[str]]: Erros por campo_id (ex: {"campo_id": ["mensagem de erro"]})
    """
    erros = {}
    
    campos = schema.get("campos", [])
    
    for campo in campos:
        campo_id = campo.get("id")
        if not campo_id:
            continue
        
        # ⚠️ REGRA: 1. Verificar se campo está visível (showWhen)
        # Campo invisível não é validado como obrigatório
        if not _verificar_visibilidade_simples(campo, contexto):
            continue  # Campo não visível, não validar
        
        # 2. Verificar se campo é obrigatório (required ou requiredWhen)
        validation = campo.get("validation", {})
        required = validation.get("required", False)
        required_when = validation.get("requiredWhen", [])
        
        # Compatibilidade com campo.obrigatorio legado
        if not required and not required_when:
            required = campo.get("obrigatorio", False)
        
        # Se não tem required nem requiredWhen, pular
        if not required and not required_when:
            continue
        
        # Verificar required básico
        is_obrigatorio = required
        
        # Verificar requiredWhen
        if required_when:
            condicoes = required_when if isinstance(required_when, list) else [required_when]
            for condicao in condicoes:
                if isinstance(condicao, dict):
                    expr_if = condicao.get("if", "")
                    if expr_if and _avaliar_expressao_simples(expr_if, contexto):
                        is_obrigatorio = True
                        break
                elif isinstance(condicao, str):
                    if _avaliar_expressao_simples(condicao, contexto):
                        is_obrigatorio = True
                        break
        
        # 3. Se obrigatório, verificar se está preenchido
        if is_obrigatorio:
            valor = dados_formulario.get(campo_id)
            
            # ⚠️ REGRA: Tipos complexos têm validação específica
            tipo_campo = campo.get("tipo", "")
            campo_vazio = False
            
            if tipo_campo == "tabela":
                # Tabela vazia = []
                campo_vazio = valor is None or (isinstance(valor, list) and len(valor) == 0)
            elif tipo_campo == "checklist":
                # Checklist vazio = nenhuma resposta marcada
                if valor is None:
                    campo_vazio = True
                elif isinstance(valor, dict):
                    itens = valor.get("itens", [])
                    campo_vazio = len(itens) == 0 or not any(item.get("resposta") for item in itens)
                else:
                    campo_vazio = True
            else:
                # Outros tipos usam validação padrão
                campo_vazio = _campo_vazio(campo, valor)
            
            if campo_vazio:
                # Obter mensagem de erro (customizada de requiredWhen se disponível)
                mensagem = "Este campo é obrigatório"
                if required_when:
                    condicoes = required_when if isinstance(required_when, list) else [required_when]
                    for condicao in condicoes:
                        if isinstance(condicao, dict):
                            expr_if = condicao.get("if", "")
                            if expr_if and _avaliar_expressao_simples(expr_if, contexto):
                                mensagem = condicao.get("message", mensagem)
                                break
                
                if campo_id not in erros:
                    erros[campo_id] = []
                erros[campo_id].append(mensagem)
    
    return erros
