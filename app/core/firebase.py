# PDV Ibix - Firebase Admin SDK (lazy init para push notifications)
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_app = None


def get_firebase_app():
    global _app
    if _app is not None:
        return _app

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        raise RuntimeError("firebase-admin não instalado. Instale com: pip install firebase-admin")

    from .config import settings
    cred_path = getattr(settings, "FIREBASE_CREDENTIALS_JSON", None)
    if not cred_path:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS_JSON não configurado. "
            "Defina o caminho para o arquivo de credenciais do Firebase nas variáveis de ambiente."
        )

    cred = credentials.Certificate(cred_path)
    _app = firebase_admin.initialize_app(cred)
    return _app


def send_push_notification(token: str, titulo: str, mensagem: str, dados: Optional[dict] = None) -> bool:
    """Envia push via FCM. Retorna True se aceito pelo FCM."""
    try:
        from firebase_admin import messaging
        get_firebase_app()

        message = messaging.Message(
            notification=messaging.Notification(title=titulo, body=mensagem),
            data={k: str(v) for k, v in (dados or {}).items()},
            token=token,
        )
        messaging.send(message)
        return True
    except ImportError:
        logger.error("firebase-admin não disponível para envio de push")
        return False
    except Exception as exc:
        exc_name = type(exc).__name__
        if "Unregistered" in str(exc) or "InvalidRegistration" in str(exc):
            logger.info("FCM token inválido/expirado: %s", token[:20])
        else:
            logger.exception("Falha ao enviar push via FCM (%s): %s", exc_name, exc)
        return False
