# PDV Ibix - Serviço de envio WhatsApp (Cloud API)
"""Envio de mensagens via WhatsApp Business Cloud API com identificação usuário/empresa."""

from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.chat_context import get_chat_context
from app.models.configuracao import Configuracao

META_GRAPH_URL = "https://graph.facebook.com/v18.0"


def _get_config(db: Session, chave: str) -> Optional[str]:
    c = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    return (c.valor or "").strip() or None if c else None


def is_whatsapp_ativo(db: Session) -> bool:
    v = _get_config(db, "whatsapp.ativo")
    return (v or "").lower() in ("1", "true", "sim", "yes")


def enviar_mensagem_whatsapp(
    db: Session,
    numero_destino: str,
    texto: str,
    usuario_id: int,
    role_nome: Optional[str] = None,
    cliente_id_token: Optional[int] = None,
    incluir_prefixo: bool = True,
    formato_prefixo: str = "curto",
) -> dict:
    """
    Envia mensagem de texto via WhatsApp Cloud API.
    Adiciona prefixo com identificação usuário/empresa se incluir_prefixo=True.
    numero_destino: número com DDI, sem + (ex.: 5511999999999).
    Retorna dict com success, message_id ou error.
    """
    if not is_whatsapp_ativo(db):
        return {"success": False, "error": "Integração WhatsApp desativada"}
    phone_number_id = _get_config(db, "whatsapp.phone_number_id")
    token = _get_config(db, "whatsapp.token")
    if not phone_number_id or not token:
        return {"success": False, "error": "Phone Number ID ou token não configurados"}
    # Normalizar destino: remover espaços e + ; garantir DDI
    to = (numero_destino or "").strip().replace("+", "").replace(" ", "")
    if not to or not to.isdigit():
        return {"success": False, "error": "Número de destino inválido"}
    if incluir_prefixo:
        ctx = get_chat_context(db, usuario_id, role_nome, cliente_id_token)
        prefixo = ctx.prefixo_mensagem(formato=formato_prefixo)
        texto_final = (prefixo + (texto or "").strip()).strip()
    else:
        texto_final = (texto or "").strip()
    if not texto_final:
        return {"success": False, "error": "Texto da mensagem vazio"}
    url = f"{META_GRAPH_URL}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": texto_final},
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=body, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            mid = (data.get("messages") or [{}])[0].get("id")
            return {"success": True, "message_id": mid}
        return {"success": False, "error": resp.text or f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
