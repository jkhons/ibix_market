# PDV Ibix — Notificações de plataforma ao cadastrar novo CA (e-mail + inbox Superadmin)
from typing import List, Optional
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.billing_config import get_app_url
from app.core.convite_lojista_email_template import (
    get_convite_lojista_template_effective_html,
    normalize_convite_template_logo_for_send,
)
from app.core.vitrine_brand import build_vitrine_logo_email_html
from app.core.logging import log_error
from app.core.platform_novo_ca_config import (
    get_novo_ca_email_enabled,
    get_novo_ca_in_app_enabled,
)
from app.models import Role, Usuario
from app.models.usuario_notificacao import UsuarioNotificacao

TIPO_NOTIF_NOVO_CA = "platform_novo_cadastro_ca"


def _superadmin_ids(db: Session) -> List[int]:
    role = db.query(Role).filter(Role.nome == "Superadministrador").first()
    if not role:
        return []
    rows = (
        db.query(Usuario.id)
        .filter(Usuario.role_id == role.id, Usuario.ativo.is_(True))
        .all()
    )
    return [r[0] for r in rows]


def _superadmin_emails(db: Session) -> List[str]:
    ids = _superadmin_ids(db)
    if not ids:
        return []
    out: List[str] = []
    for (em,) in (
        db.query(Usuario.email)
        .filter(Usuario.id.in_(ids), Usuario.email.isnot(None), Usuario.email != "")
        .all()
    ):
        e = (em or "").strip()
        if e and e not in out:
            out.append(e)
    return out


def build_cadastro_public_url(db: Session, codigo_promocional: Optional[str] = None) -> str:
    base = (get_app_url(db) or "").strip().rstrip("/")
    if not base:
        return "/cadastro"
    path = f"{base}/cadastro"
    if codigo_promocional:
        c = quote(codigo_promocional.strip().upper(), safe="")
        return f"{path}?codigo_promocional={c}"
    return path


def after_register_public_success(
    db: Session,
    *,
    ca_user_id: int,
    tenant_id: int,
    nome_empresa: str,
    cnpj: str,
    email_responsavel: str,
) -> None:
    """
    Pós-commit do cadastro público de CA: e-mail e/ou inbox conforme flags.
    Não propaga exceções (falhas só em log).
    """
    try:
        email_on = get_novo_ca_email_enabled(db)
        inbox_on = get_novo_ca_in_app_enabled(db)
        if not email_on and not inbox_on:
            return

        base_url = (get_app_url(db) or "").strip().rstrip("/")
        admin_link = f"{base_url}/admin/billing/tenant/{tenant_id}" if base_url else f"/admin/billing/tenant/{tenant_id}"

        if email_on:
            dest = _superadmin_emails(db)
            if dest:
                try:
                    from app.services.email_service import EmailService

                    svc = EmailService(db=db)
                    ctx = {
                        "nome_empresa": nome_empresa or "—",
                        "cnpj": cnpj or "—",
                        "email_responsavel": email_responsavel or "—",
                        "tenant_id": str(tenant_id),
                        "usuario_ca_id": str(ca_user_id),
                        "admin_link": admin_link,
                        "ano": "",  # preenchido abaixo
                    }
                    from datetime import datetime

                    ctx["ano"] = str(datetime.now().year)
                    ok = svc.send_template_email(
                        to=dest,
                        template_name="platform_superadmin_novo_cadastro_ca",
                        context=ctx,
                        subject=f"Novo cadastro de lojista — {nome_empresa or 'CA'}",
                        funcao="sistema",
                    )
                    if not ok:
                        log_error(
                            "platform_novo_ca: send_template_email retornou false (superadmin novo CA)",
                        )
                except Exception as e:
                    log_error("platform_novo_ca: falha e-mail superadmin", exc_info=e)

        if inbox_on:
            sa_ids = _superadmin_ids(db)
            titulo = "Novo cadastro de lojista"
            mensagem = (
                f"{nome_empresa or 'Empresa'} · CNPJ {cnpj or '—'} · Responsável: {email_responsavel or '—'} "
                f"(tenant #{tenant_id})."
            )
            for uid in sa_ids:
                try:
                    existe = (
                        db.query(UsuarioNotificacao)
                        .filter(
                            UsuarioNotificacao.usuario_id == uid,
                            UsuarioNotificacao.tipo == TIPO_NOTIF_NOVO_CA,
                            UsuarioNotificacao.ref_id == ca_user_id,
                        )
                        .first()
                    )
                    if existe:
                        continue
                    db.add(
                        UsuarioNotificacao(
                            usuario_id=uid,
                            tenant_id=None,
                            tipo=TIPO_NOTIF_NOVO_CA,
                            ref_id=ca_user_id,
                            titulo=titulo,
                            mensagem=mensagem,
                            link=admin_link,
                            icone="user-plus",
                            cor="primary",
                            lida=False,
                            dados_json={
                                "tenant_id": tenant_id,
                                "usuario_ca_id": ca_user_id,
                                "nome_empresa": nome_empresa,
                                "cnpj": cnpj,
                            },
                        )
                    )
                except Exception as e:
                    log_error(f"platform_novo_ca: falha inbox uid={uid}", exc_info=e)
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                log_error("platform_novo_ca: commit inbox falhou", exc_info=e)
    except Exception as e:
        log_error("platform_novo_ca_notify_service.after_register_public_success", exc_info=e)


def enviar_convite_cadastro_lojista(
    db: Session,
    *,
    destinatario_email: str,
    nome_destinatario: Optional[str],
    mensagem_personalizada: Optional[str],
    codigo_promocional: Optional[str],
) -> tuple[bool, str, str]:
    """
    Envia e-mail de convite. Retorna (ok, cadastro_url, erro_msg).
    """
    email_norm = destinatario_email.strip().lower()
    cadastro_url = build_cadastro_public_url(db, codigo_promocional)

    try:
        from app.services.email_service import EmailService

        svc = EmailService(db=db)
        nome = (nome_destinatario or "").strip() or "Olá"
        html_src, _ = get_convite_lojista_template_effective_html(db)
        if not (html_src or "").strip():
            return False, cadastro_url, "Template de convite não encontrado no servidor."

        base = (get_app_url(db) or "").strip().rstrip("/")
        logo_link_href = base or None
        vitrine_href = f"{base}/loja" if base else None
        logo_html = build_vitrine_logo_email_html(
            db,
            alt="Ibix",
            max_width_px=280,
            link_href=logo_link_href,
        )
        if base:
            vitrine_link_html = (
                f'<p style="margin:18px 0 0;font-size:13px;color:#4A627A;line-height:1.55;text-align:center;">'
                f'Veja a vitrine Ibix: <a href="{vitrine_href}" target="_blank" rel="noopener noreferrer" '
                f'style="color:#C47A44;font-weight:600;text-decoration:none;">abrir marketplace</a></p>'
            )
        else:
            vitrine_link_html = ""

        ctx = {
            "nome_destinatario": nome,
            "mensagem_personalizada_html": "",
            "cadastro_url": cadastro_url,
            "codigo_linha": "",
            "ano": "",
            "logo_html": logo_html,
            "vitrine_link_html": vitrine_link_html,
        }
        from datetime import datetime

        ctx["ano"] = str(datetime.now().year)
        if mensagem_personalizada and mensagem_personalizada.strip():
            # parágrafos simples (escapar HTML básico)
            import html

            safe = html.escape(mensagem_personalizada.strip()).replace("\n", "<br/>")
            ctx["mensagem_personalizada_html"] = f'<p class="msg-personalizada">{safe}</p>'
        if codigo_promocional and codigo_promocional.strip():
            c = html.escape(codigo_promocional.strip().upper())
            ctx["codigo_linha"] = f"<p><strong>Código promocional:</strong> {c}</p>"

        html_src = normalize_convite_template_logo_for_send(html_src, logo_html)

        ok = svc.send_template_html_string(
            to=[email_norm],
            html_template=html_src,
            context=ctx,
            subject="Ibix · Convite para cadastrar sua empresa",
            funcao="sistema",
        )
        return ok, cadastro_url, "" if ok else "Falha ao enviar e-mail (SMTP ou template)."
    except ValueError as e:
        return False, cadastro_url, str(e)
    except Exception as e:
        log_error("enviar_convite_cadastro_lojista", exc_info=e)
        return False, cadastro_url, "Erro ao enviar convite."


__all__ = [
    "TIPO_NOTIF_NOVO_CA",
    "after_register_public_success",
    "build_cadastro_public_url",
    "enviar_convite_cadastro_lojista",
]
