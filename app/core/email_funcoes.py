# PDV Ibix - Funções de e-mail para configuração por remetente
from typing import List, Tuple

# Flag global: ativar e-mail separado por cliente (Super Admin)
CHAVE_EMAIL_SEPARADO_POR_CLIENTE_ATIVO = "email_separado_por_cliente_ativo"


def chave_email_cliente_from(cliente_id: int) -> str:
    """Chave Configuracao para from_email do cliente."""
    return f"email_cliente.{cliente_id}.from"


def chave_email_cliente_from_name(cliente_id: int) -> str:
    """Chave Configuracao para from_name do cliente."""
    return f"email_cliente.{cliente_id}.from_name"


# Códigos das funções (chave em configuracoes: email_funcao_{codigo}_from, email_funcao_{codigo}_from_name)
FUNCOES_EMAIL: List[Tuple[str, str, str]] = [
    ("nota_fiscal", "Nota fiscal", "Envio de NF-e/NFC-e por e-mail"),
    ("nota_servico", "Nota de serviço", "Envio de NFS-e por e-mail"),
    ("ordem_servico", "Ordem de serviço", "Envio de OS/PDF por e-mail"),
    ("orcamento", "Orçamentos", "Envio de orçamento/documento por e-mail"),
    ("notificacoes", "Notificações", "Alertas de agendamento e contrato vencendo"),
    ("novidades", "Novidades", "Campanhas ou comunicados"),
    ("help_center", "Help Center", "Formulário de contato"),
    ("sistema", "Sistema/Admin", "Alertas de sistema, relatório mensal, e-mail de teste"),
]

def get_funcoes_email() -> List[Tuple[str, str, str]]:
    """Retorna lista de (codigo, label, descricao)."""
    return list(FUNCOES_EMAIL)

def get_codigos_funcoes_email() -> List[str]:
    """Retorna lista de códigos válidos."""
    return [f[0] for f in FUNCOES_EMAIL]

def chave_from(codigo: str) -> str:
    """Chave de configuração para e-mail remetente da função."""
    return f"email_funcao_{codigo}_from"

def chave_from_name(codigo: str) -> str:
    """Chave de configuração para nome do remetente da função."""
    return f"email_funcao_{codigo}_from_name"
