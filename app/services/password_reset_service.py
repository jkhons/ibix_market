# PDV Ibix - Serviço de redefinição de senha (Esqueci minha senha)
"""Fluxo seguro: token de uso único, hash armazenado, mensagem genérica na solicitação."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import AuthConfig
from app.models import ConsumidorMarketplace, PasswordResetToken, Usuario
from app.services.email_service import EmailService

TOKEN_EXPIRE_MINUTES = 60
TOKEN_BYTES = 32


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _base_url_from_request_or_config(base_url: Optional[str], db: Optional[Session]) -> str:
    if base_url:
        return str(base_url).strip().rstrip("/")
    try:
        from app.core.billing_config import get_app_url
        return (get_app_url(db) or "").strip().rstrip("/")
    except Exception:
        pass
    import os
    return (os.getenv("APP_URL") or "").strip().rstrip("/")


def request_reset_pdv(
    db: Session,
    email: str,
    base_url: Optional[str] = None,
) -> bool:
    """
    Solicita redefinição de senha para usuário PDV (Usuario).
    Se o e-mail existir e estiver ativo, gera token, persiste e envia e-mail.
    Retorna True sempre (não revelar se o e-mail existe).
    """
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return True

    user = db.query(Usuario).filter(
        func.lower(Usuario.email) == email_norm,
        Usuario.ativo == True,
    ).first()

    if not user:
        return True

    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

    rec = PasswordResetToken(
        tipo="pdv",
        entidade_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(rec)
    db.commit()

    url_base = _base_url_from_request_or_config(base_url, db)
    link = f"{url_base}/auth/redefinir-senha?token={raw_token}" if url_base else ""

    try:
        email_svc = EmailService(db)
        subject = "Redefinição de senha - Ibix"
        body_text = (
            "Você solicitou a redefinição de senha.\n\n"
            f"Clique no link abaixo para definir uma nova senha (válido por {TOKEN_EXPIRE_MINUTES} minutos):\n{link}\n\n"
            "Se não foi você, ignore este e-mail."
        )
        html = (
            f"<p>Você solicitou a redefinição de senha.</p>"
            f"<p><a href=\"{link}\">Redefinir senha</a> (válido por {TOKEN_EXPIRE_MINUTES} minutos)</p>"
            f"<p>Se não foi você, ignore este e-mail.</p>"
        )
        email_svc.send_email(
            to=[user.email],
            subject=subject,
            body=body_text,
            html=html,
            funcao="sistema",
        )
    except Exception:
        pass

    return True


def reset_password_pdv(
    db: Session,
    token: str,
    new_password: str,
    confirm_password: str,
) -> Tuple[bool, Optional[str]]:
    """
    Redefine a senha do usuário PDV usando o token.
    Retorna (True, None) em sucesso; (False, mensagem_erro) em falha.
    """
    if not token or not new_password or not confirm_password:
        return False, "Preencha todos os campos."
    if new_password != confirm_password:
        return False, "As senhas não coincidem."
    if len(new_password) < 6:
        return False, "A senha deve ter no mínimo 6 caracteres."

    token_hash = _hash_token(token.strip())
    now = datetime.now(timezone.utc)

    rec = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.tipo == "pdv",
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )

    if not rec:
        return False, "Link inválido ou expirado. Solicite uma nova redefinição."

    user = db.query(Usuario).filter(Usuario.id == rec.entidade_id).first()
    if not user or not user.ativo:
        return False, "Usuário não encontrado ou inativo."

    user.senha_hash = AuthConfig.get_password_hash(new_password)
    rec.used_at = now
    db.commit()
    return True, None


def validate_token_pdv(db: Session, token: str) -> bool:
    """Verifica se o token é válido (existe, não usado, não expirado)."""
    if not token or not token.strip():
        return False
    token_hash = _hash_token(token.strip())
    now = datetime.now(timezone.utc)
    rec = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.tipo == "pdv",
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    return rec is not None


def request_reset_loja(
    db: Session,
    email: str,
    base_url: Optional[str] = None,
    loja_id: Optional[int] = None,
) -> bool:
    """
    Solicita redefinição de senha para consumidor da Loja (ConsumidorMarketplace).
    Se loja_id informado, busca consumidor no tenant da loja; senão busca por email global.
    Retorna True sempre.
    """
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return True

    if loja_id:
        from app.models import LojaMarketplace
        loja_ent = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
        if loja_ent:
            consumidor = (
                db.query(ConsumidorMarketplace)
                .filter(
                    ConsumidorMarketplace.tenant_id == loja_ent.cliente_id,
                    func.lower(ConsumidorMarketplace.email) == email_norm,
                    ConsumidorMarketplace.deleted_at.is_(None),
                )
                .first()
            )
        else:
            consumidor = None
    else:
        consumidor = (
            db.query(ConsumidorMarketplace)
            .filter(
                func.lower(ConsumidorMarketplace.email) == email_norm,
                ConsumidorMarketplace.deleted_at.is_(None),
            )
            .first()
        )

    if not consumidor or not consumidor.ativo:
        return True

    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

    rec = PasswordResetToken(
        tipo="loja",
        entidade_id=consumidor.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(rec)
    db.commit()

    url_base = _base_url_from_request_or_config(base_url, db)
    link = f"{url_base}/loja/redefinir-senha?token={raw_token}" if url_base else ""

    try:
        email_svc = EmailService(db)
        subject = "Redefinição de senha - Ibix Loja"
        body_text = (
            "Você solicitou a redefinição de senha da sua conta na loja.\n\n"
            f"Clique no link abaixo para definir uma nova senha (válido por {TOKEN_EXPIRE_MINUTES} minutos):\n{link}\n\n"
            "Se não foi você, ignore este e-mail."
        )
        html = (
            f"<p>Você solicitou a redefinição de senha da sua conta na loja.</p>"
            f"<p><a href=\"{link}\">Redefinir senha</a> (válido por {TOKEN_EXPIRE_MINUTES} minutos)</p>"
            f"<p>Se não foi você, ignore este e-mail.</p>"
        )
        email_svc.send_email(
            to=[consumidor.email],
            subject=subject,
            body=body_text,
            html=html,
            funcao="sistema",
        )
    except Exception:
        pass

    return True


def reset_password_loja(
    db: Session,
    token: str,
    new_password: str,
    confirm_password: str,
) -> Tuple[bool, Optional[str]]:
    """Redefine a senha do consumidor Loja usando o token."""
    if not token or not new_password or not confirm_password:
        return False, "Preencha todos os campos."
    if new_password != confirm_password:
        return False, "As senhas não coincidem."
    if len(new_password) < 6:
        return False, "A senha deve ter no mínimo 6 caracteres."

    token_hash = _hash_token(token.strip())
    now = datetime.now(timezone.utc)

    rec = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.tipo == "loja",
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )

    if not rec:
        return False, "Link inválido ou expirado. Solicite uma nova redefinição."

    consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == rec.entidade_id).first()
    if not consumidor or not consumidor.ativo or consumidor.deleted_at:
        return False, "Conta não encontrada ou inativa."

    consumidor.senha_hash = AuthConfig.get_password_hash(new_password)
    rec.used_at = now
    db.commit()
    return True, None


def validate_token_loja(db: Session, token: str) -> bool:
    """Verifica se o token de redefinição Loja é válido."""
    if not token or not token.strip():
        return False
    token_hash = _hash_token(token.strip())
    now = datetime.now(timezone.utc)
    rec = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.tipo == "loja",
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    return rec is not None
