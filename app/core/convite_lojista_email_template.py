# PDV Ibix — Template HTML do e-mail «Convidar comércio» (cadastro lojista)
"""Override opcional na tabela configuracoes; fallback: arquivo em app/templates/emails/."""
import re
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Configuracao

# Logo legado (PDV/landing) — convite deve usar cab.png da vitrine ({{logo_html}} no envio)
_LOGO_SFUNDO_IMG_RE = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*[\"'][^\"']*logoSfundo\.png[^\"']*[\"'][^>]*>",
    re.IGNORECASE,
)

CHAVE_EMAIL_TEMPLATE_PLATFORM_CONVITE_LOJISTA = "email_template_platform_convite_cadastro_lojista"
_CONVITE_TEMPLATE_FILENAME = "platform_convite_cadastro_lojista.html"
_MAX_HTML_BYTES = 500_000


def _default_template_path() -> Path:
    return Path(__file__).resolve().parent.parent / "templates" / "emails" / _CONVITE_TEMPLATE_FILENAME


def read_default_convite_lojista_template_html() -> str:
    p = _default_template_path()
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


def get_convite_lojista_template_effective_html(db: Session) -> Tuple[str, bool]:
    """
    Retorna (html, is_custom).
    is_custom=True quando há override gravado em configuracoes (não vazio).
    """
    row = db.query(Configuracao).filter(Configuracao.chave == CHAVE_EMAIL_TEMPLATE_PLATFORM_CONVITE_LOJISTA).first()
    if row and (row.valor or "").strip():
        return (row.valor or "").strip(), True
    return read_default_convite_lojista_template_html(), False


def normalize_convite_template_logo_for_send(html: str, logo_html: str) -> str:
    """
    Templates salvos antes da vitrine (logoSfundo embutido) passam a usar o bloco logo_html (cab.png).
    Não altera templates que já usam apenas {{logo_html}}.
    """
    if not (html or "").strip():
        return html or ""
    return _LOGO_SFUNDO_IMG_RE.sub(logo_html, html)


def set_convite_lojista_template_html(db: Session, html: Optional[str]) -> None:
    """html None ou só espaços: remove override (volta ao arquivo padrão)."""
    raw = (html or "").strip() if html is not None else ""
    if not raw:
        db.query(Configuracao).filter(Configuracao.chave == CHAVE_EMAIL_TEMPLATE_PLATFORM_CONVITE_LOJISTA).delete()
        return
    if len(raw.encode("utf-8")) > _MAX_HTML_BYTES:
        raise ValueError(f"Template excede o tamanho máximo permitido ({_MAX_HTML_BYTES // 1000} KB).")
    if "{{cadastro_url}}" not in raw:
        raise ValueError("O template deve conter o placeholder {{cadastro_url}} (link de cadastro).")
    raw = normalize_convite_template_logo_for_send(raw, "{{logo_html}}")
    row = db.query(Configuracao).filter(Configuracao.chave == CHAVE_EMAIL_TEMPLATE_PLATFORM_CONVITE_LOJISTA).first()
    desc = "HTML do e-mail de convite a lojista (aba Convidar comércio /clientes). Placeholders: {{nome_destinatario}}, {{mensagem_personalizada_html}}, {{cadastro_url}}, {{codigo_linha}}, {{ano}}, {{logo_html}}, {{vitrine_link_html}}"
    if row:
        row.valor = raw
        row.descricao = desc
    else:
        db.add(Configuracao(chave=CHAVE_EMAIL_TEMPLATE_PLATFORM_CONVITE_LOJISTA, valor=raw, descricao=desc))


__all__ = [
    "CHAVE_EMAIL_TEMPLATE_PLATFORM_CONVITE_LOJISTA",
    "get_convite_lojista_template_effective_html",
    "normalize_convite_template_logo_for_send",
    "read_default_convite_lojista_template_html",
    "set_convite_lojista_template_html",
]
