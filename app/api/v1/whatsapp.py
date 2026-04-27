# PDV Ibix - API WhatsApp (webhook Meta + envio com identificação usuário/empresa)
import hashlib
import hmac
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.middleware import AuthMiddleware, get_current_user_cliente
from app.database.connection import get_db
from app.models.configuracao import Configuracao
from app.models.usuario import Usuario
from app.models.whatsapp_webhook_event import WhatsappWebhookEvent
from app.services.whatsapp_service import enviar_mensagem_whatsapp

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _get_verify_token(db: Session) -> Optional[str]:
    c = db.query(Configuracao).filter(Configuracao.chave == "whatsapp.verify_token").first()
    return (c.valor or "").strip() or None if c else None


def _get_app_secret(db: Session) -> Optional[str]:
    c = db.query(Configuracao).filter(Configuracao.chave == "whatsapp.app_secret").first()
    return (c.valor or "").strip() or None if c else None


def _verify_hub_signature(payload_body: bytes, signature: Optional[str], secret: Optional[str]) -> bool:
    """Valida X-Hub-Signature-256 (Meta: HMAC-SHA256 do body com App Secret)."""
    if not secret:
        return True
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature) or hmac.compare_digest(expected, signature)


def _extract_meta_event_info(data: dict) -> tuple:
    """Extrai tipo_evento e from_phone do payload Meta (entry.changes.value.messages/statuses)."""
    tipo, from_phone = None, None
    try:
        for entry in data.get("entry", []) or []:
            for change in (entry.get("changes") or []) or []:
                val = change.get("value") or {}
                if "messages" in val:
                    msg = (val["messages"] or [None])[0]
                    if msg:
                        tipo = msg.get("type") or "message"
                        from_phone = (msg.get("from") or "")
                elif "statuses" in val:
                    tipo = "status"
                    st = (val["statuses"] or [None])[0]
                    if st:
                        from_phone = (st.get("recipient_id") or "")
                if tipo or from_phone:
                    return (tipo, from_phone)
    except Exception:
        pass
    return (tipo, from_phone)


@router.get("/webhook", response_class=PlainTextResponse)
def webhook_verify(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    """Validação do webhook pelo Meta. Retorna hub.challenge se verify_token coincidir."""
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Modo inválido")
    expected = _get_verify_token(db)
    if not expected or hub_verify_token != expected:
        raise HTTPException(status_code=403, detail="Verify token inválido")
    return hub_challenge or ""


@router.post("/webhook")
async def webhook_receive(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """Recebe eventos do WhatsApp (mensagens, status). Valida X-Hub-Signature-256 e persiste em histórico."""
    body = await request.body()
    secret = _get_app_secret(db)
    if not _verify_hub_signature(body, x_hub_signature_256, secret):
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {}

    tipo_evento, from_phone = _extract_meta_event_info(data)
    payload_str = body.decode("utf-8", errors="replace")[:10000] if body else None
    event = WhatsappWebhookEvent(
        payload=payload_str,
        tipo_evento=tipo_evento,
        from_phone=from_phone,
    )
    db.add(event)
    db.commit()

    return {"ok": True}


class EnviarWhatsAppRequest(BaseModel):
    numero_destino: str
    texto: str
    incluir_prefixo: bool = True


@router.post("/enviar")
def enviar_whatsapp(
    body: EnviarWhatsAppRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    cliente_id_token: Optional[int] = Depends(get_current_user_cliente),
):
    """Envia mensagem WhatsApp com identificação do usuário e empresa. Requer autenticação."""
    role_nome = current_user.role.nome if current_user.role else None
    result = enviar_mensagem_whatsapp(
        db=db,
        numero_destino=body.numero_destino,
        texto=body.texto,
        usuario_id=current_user.id,
        role_nome=role_nome,
        cliente_id_token=cliente_id_token,
        incluir_prefixo=body.incluir_prefixo,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Falha ao enviar"))
    return result
