# PDV Ibix - Criptografia de credenciais de provedores (Fase 3.3)
"""Credenciais em repouso: encrypt/decrypt com chave em variável de ambiente (Fernet)."""
import base64
import json
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Chave em env: PAYMENT_CREDENTIALS_SECRET (32 bytes url-safe base64) ou PAYMENT_CREDENTIALS_PASSWORD (derivamos key)
_ENCODING = "utf-8"


def _get_fernet() -> Optional[Fernet]:
    """Obtém instância Fernet a partir de PAYMENT_CREDENTIALS_SECRET ou PAYMENT_CREDENTIALS_PASSWORD."""
    secret = os.environ.get("PAYMENT_CREDENTIALS_SECRET")
    if secret:
        try:
            return Fernet(secret.encode(_ENCODING) if isinstance(secret, str) else secret)
        except Exception:
            pass
    password = os.environ.get("PAYMENT_CREDENTIALS_PASSWORD")
    if password:
        # Derivar chave 32 bytes e codificar em base64 url-safe (Fernet exige 44 chars)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"pdv_payment_credentials_v1",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode(_ENCODING)))
        return Fernet(key)
    return None


def encrypt_credentials(credentials_dict: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Criptografa credenciais (dict) para armazenamento. Retorna None se credenciais vazias.
    Se PAYMENT_CREDENTIALS_* não estiver definido, retorna JSON em texto (não recomendado em produção).
    """
    if not credentials_dict:
        return None
    payload = json.dumps(credentials_dict, default=str).encode(_ENCODING)
    fernet = _get_fernet()
    if fernet:
        return fernet.encrypt(payload).decode(_ENCODING)
    # Fallback sem criptografia (dev)
    return payload.decode(_ENCODING)


def decrypt_text(encrypted: Optional[str]) -> Optional[str]:
    """Descriptografa um valor textual (ex.: webhook_secret). Usa o mesmo Fernet das credenciais."""
    if not encrypted:
        return None
    fernet = _get_fernet()
    if fernet:
        try:
            raw = fernet.decrypt(encrypted.encode(_ENCODING))
            return raw.decode(_ENCODING)
        except (InvalidToken, ValueError):
            pass
    return encrypted if isinstance(encrypted, str) else None


def decrypt_credentials(encrypted: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Descriptografa credenciais. Retorna dict ou None. Se valor não estiver cifrado (dev),
    tenta interpretar como JSON.
    """
    if not encrypted:
        return None
    fernet = _get_fernet()
    if fernet:
        try:
            raw = fernet.decrypt(encrypted.encode(_ENCODING))
            return json.loads(raw.decode(_ENCODING))
        except (InvalidToken, ValueError):
            # Pode ser texto plano (migração)
            try:
                return json.loads(encrypted)
            except ValueError:
                return None
    try:
        return json.loads(encrypted)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Senha do certificado A1 (fiscal) – chave separada (FISCAL_CERT_*)
# ---------------------------------------------------------------------------

def _get_fernet_fiscal() -> Optional[Fernet]:
    """Obtém Fernet para senha do certificado A1 (FISCAL_CERT_PASSWORD_SECRET ou FISCAL_CERT_PASSWORD_PASSWORD)."""
    secret = os.environ.get("FISCAL_CERT_PASSWORD_SECRET")
    if secret:
        try:
            return Fernet(secret.encode(_ENCODING) if isinstance(secret, str) else secret)
        except Exception:
            pass
    password = os.environ.get("FISCAL_CERT_PASSWORD_PASSWORD")
    if password:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"pdv_fiscal_cert_password_v1",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode(_ENCODING)))
        return Fernet(key)
    return None


def encrypt_cert_password(plain: Optional[str]) -> Optional[str]:
    """Criptografa a senha do certificado A1 para armazenamento. Se FISCAL_CERT_* não estiver definido, retorna em texto (dev)."""
    if not plain or not (plain if isinstance(plain, str) else "").strip():
        return None
    payload = (plain if isinstance(plain, str) else str(plain)).encode(_ENCODING)
    fernet = _get_fernet_fiscal()
    if fernet:
        return fernet.encrypt(payload).decode(_ENCODING)
    return plain if isinstance(plain, str) else plain.decode(_ENCODING)


def decrypt_cert_password(encrypted: Optional[str], raise_on_failure: bool = False) -> Optional[str]:
    """Descriptografa a senha do certificado A1. Se não estiver cifrada (dev/migração), retorna o valor em texto.
    Se raise_on_failure=True e a descriptografia falhar, levanta ValueError em vez de retornar o valor bruto."""
    if not encrypted:
        return None
    fernet = _get_fernet_fiscal()
    if fernet:
        try:
            raw = fernet.decrypt(encrypted.encode(_ENCODING))
            return raw.decode(_ENCODING)
        except (InvalidToken, ValueError) as e:
            if raise_on_failure:
                raise ValueError("Token CSC inválido ou não pôde ser descriptografado.") from e
            pass
    return encrypted if isinstance(encrypted, str) else (encrypted.decode(_ENCODING) if isinstance(encrypted, bytes) else str(encrypted))
