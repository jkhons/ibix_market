# PDV Ibix — E-mails transacionais do marketplace (foco visual no comprador da vitrine)
from __future__ import annotations

import html
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.billing_config import get_app_url
from app.core.constants import (
    ACEITA,
    AGUARDANDO_PUBLICACAO,
    CANCELADA,
    DISPONIVEL,
    EM_RETIRADA,
    EM_ROTA,
    ENTREGUE,
    EXPIRADA,
    FALHA_ENTREGA,
    RETIRADA,
)
from app.models.configuracao import Configuracao
from app.models.loja_marketplace import LojaMarketplace
from app.models.marketplace_checkout_session import MarketplaceCheckoutSessionPedido
from app.models.payment_transaction import PaymentTransaction
from app.models.pedido_item_marketplace import PedidoItemMarketplace
from app.models.pedido_marketplace import PedidoMarketplace
from app.services.email_service import EmailService

_DIR_MARKETPLACE_EMAIL = Path(__file__).resolve().parent.parent / "templates" / "emails" / "marketplace"

CHAVE_LOGO_PLATAFORMA = "marketplace_email_logo_plataforma_url"
CHAVE_NOME_PLATAFORMA = "marketplace_email_nome_plataforma"
CHAVE_COR_VITRINE = "marketplace_email_cor_vitrine"
CHAVE_COR_VITRINE_ESCURA = "marketplace_email_cor_vitrine_escura"

# Logo largo do cabeçalho da vitrine (/loja) — mesmo asset de base_loja.html
VITRINE_HEADER_LOGO_PATH = "/static/img/ibix/cab.png"

# Paleta Ibix + fallback do CTA (botões / destaques do miolo)
COR_IBIX = "#C47A44"
COR_IBIX_ESCURA = "#9C5E33"


def _cfg(db: Session, chave: str) -> str:
    row = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    return (row.valor or "").strip() if row else ""


def _cfg_tenant(db: Session, tenant_id: Optional[int], chave: str) -> str:
    """Config por tenant: chave f\"{chave}:{tenant_id}\" (opcional)."""
    if tenant_id is None:
        return ""
    row = db.query(Configuracao).filter(Configuracao.chave == f"{chave}:{int(tenant_id)}").first()
    return (row.valor or "").strip() if row else ""


def _absolute_url(db: Session, url_or_path: Optional[str]) -> str:
    raw = (url_or_path or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    base = get_app_url(db).rstrip("/")
    if raw.startswith("/"):
        return f"{base}{raw}"
    return f"{base}/{raw}"


def _primeiro_nome(nome_completo: Optional[str]) -> str:
    partes = (nome_completo or "").strip().split()
    return partes[0] if partes else "Cliente"


def _slug_loja(loja: LojaMarketplace) -> str:
    return (loja.slug or "").strip()


def _substituir(html: str, ctx: Dict[str, Any]) -> str:
    out = html
    for key, val in ctx.items():
        if val is None:
            val = ""
        out = out.replace(f"{{{{{key}}}}}", str(val))
    return out


def _html_para_texto_simples(html: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", html)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _bloco_logo_img(url: str, alt: str, width: int) -> str:
    if not url:
        return ""
    esc = alt.replace('"', "&quot;")
    return (
        f'<img src="{url}" alt="{esc}" width="{width}" '
        'style="display:block;margin:0 auto;max-width:100%;height:auto;border:0;border-radius:10px;">'
    )


def _fmt_moeda_br(val: Union[Decimal, float, int, str, None]) -> str:
    try:
        v = float(val or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _bloco_itens_pedido_html(db: Session, pedido_id: int) -> str:
    """Lista HTML dos itens do pedido (nome snapshot, qtd, subtotal)."""
    itens = (
        db.query(PedidoItemMarketplace)
        .filter(PedidoItemMarketplace.pedido_id == pedido_id)
        .order_by(PedidoItemMarketplace.id.asc())
        .all()
    )
    if not itens:
        return (
            '<p style="margin:16px 0 0;font-size:13px;color:#64748b;line-height:1.45;">'
            "Não foi possível listar os produtos deste pedido neste e-mail.</p>"
        )

    linhas: list[str] = []
    for it in itens:
        nome_raw = (it.nome_produto_snapshot or "").strip() or "Produto"
        nome = html.escape(nome_raw)
        qtd = int(it.quantidade or 0)
        unit = _fmt_moeda_br(it.preco_unitario)
        sub = _fmt_moeda_br(it.preco_total)
        linhas.append(
            "<tr>"
            '<td style="padding:10px 8px 10px 0;border-bottom:1px solid #e2e8f0;font-size:14px;color:#334155;line-height:1.45;">'
            f"<strong>{nome}</strong><br>"
            f'<span style="font-size:12px;color:#64748b;">Quantidade: {qtd} · Unitário: R$ {unit}</span>'
            "</td>"
            '<td style="padding:10px 0;border-bottom:1px solid #e2e8f0;text-align:right;vertical-align:top;white-space:nowrap;'
            'font-size:14px;font-weight:600;color:#0f172a;">'
            f"R$ {sub}"
            "</td>"
            "</tr>"
        )

    corpo = "".join(linhas)
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        'style="margin:16px 0 0;border-collapse:collapse;">'
        '<tr><td colspan="2" style="padding:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;color:#64748b;">'
        "Produtos comprados</td></tr>"
        f"{corpo}"
        "</table>"
    )


def _bloco_logo_vitrine_email(url: str, alt: str, max_width_px: int) -> str:
    """Logo horizontal da vitrine (cab.png): limite de largura para clientes de e-mail."""
    if not url:
        return ""
    esc = alt.replace('"', "&quot;")
    mw = int(max_width_px)
    return (
        f'<img src="{url}" alt="{esc}" width="{mw}" '
        f'style="display:block;margin:0 auto;max-width:{mw}px;width:100%;height:auto;border:0;">'
    )


def build_context_comprador(db: Session, pedido: PedidoMarketplace, loja: LojaMarketplace) -> Dict[str, Any]:
    """Contexto comum para layouts focados no comprador."""
    app_base = get_app_url(db).rstrip("/")
    num = pedido.numero_pedido or str(pedido.id)
    nome_v = (loja.nome_fantasia or loja.nome_loja or "Loja").strip()
    slug = _slug_loja(loja)
    link_vitrine = f"{app_base}/loja/{slug}" if slug else app_base
    link_pedido = f"{app_base}/loja/acompanhar-pedido?numero_pedido={quote(num)}"

    nome_plataforma = (_cfg(db, CHAVE_NOME_PLATAFORMA) or "Ibix").strip()

    # Cores do CTA / destaques do miolo: tenant da loja (botão Buscar da vitrine usa --loja-action #5C6E4A como referência)
    cor_vitrine = _cfg_tenant(db, loja.cliente_id, CHAVE_COR_VITRINE) or "#5C6E4A"
    cor_vitrine_escura = _cfg_tenant(db, loja.cliente_id, CHAVE_COR_VITRINE_ESCURA) or "#4E5F40"

    # Cabeçalho/roda-pé: mesmo strip da vitrine (cab.png). Opcional: marketplace_email_logo_plataforma_url substitui o asset (logo largo da marca).
    logo_cfg = (_cfg(db, CHAVE_LOGO_PLATAFORMA) or "").strip()
    logo_vitrine_cab_abs = _absolute_url(db, logo_cfg) if logo_cfg else _absolute_url(db, VITRINE_HEADER_LOGO_PATH)
    bloco_logo_vitrine_header = _bloco_logo_vitrine_email(logo_vitrine_cab_abs, nome_plataforma, 280)
    bloco_logo_vitrine_rodape = _bloco_logo_vitrine_email(logo_vitrine_cab_abs, nome_plataforma, 168)

    total_fmt = f"{float(pedido.total or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    bloco_itens_pedido = _bloco_itens_pedido_html(db, pedido.id)

    tipo = (pedido.tipo_entrega or "").strip().lower()
    if tipo == "retirada":
        bloco_tipo = '<p style="margin:12px 0 0;font-size:13px;color:#64748b;">Modalidade: <strong>Retirada na loja</strong></p>'
    elif tipo in ("entrega", "delivery", "envio"):
        bloco_tipo = '<p style="margin:12px 0 0;font-size:13px;color:#64748b;">Modalidade: <strong>Entrega</strong></p>'
    else:
        bloco_tipo = f'<p style="margin:12px 0 0;font-size:13px;color:#64748b;">Modalidade: <strong>{tipo or "—"}</strong></p>'

    preheader = f"Pedido {num} — {nome_v}. Confira os detalhes da sua compra."

    link_vitrine_central = f"{app_base}/loja"

    return {
        "titulo_email": f"Pedido {num}",
        "preheader": preheader,
        "nome_vitrine": nome_v,
        "nome_loja": nome_v,
        "nome_plataforma": nome_plataforma,
        "numero_pedido": num,
        "total_pedido": total_fmt,
        "comprador_primeiro_nome": _primeiro_nome(pedido.comprador_nome),
        "link_acompanhar_pedido": link_pedido,
        "link_vitrine": link_vitrine,
        "link_vitrine_central": link_vitrine_central,
        "cor_vitrine": cor_vitrine,
        "cor_vitrine_escura": cor_vitrine_escura,
        "bloco_logo_vitrine_header": bloco_logo_vitrine_header,
        "bloco_logo_vitrine_rodape": bloco_logo_vitrine_rodape,
        "bloco_itens_pedido": bloco_itens_pedido,
        "texto_rodape_plataforma": (
            f"Mensagem automática sobre o seu pedido na vitrine {nome_plataforma}. "
            "Este e-mail foi enviado pelo sistema; não responda a esta mensagem."
        ),
        "bloco_tipo_entrega": bloco_tipo,
    }


def _ler_fragmento(nome_arquivo: str) -> str:
    path = _DIR_MARKETPLACE_EMAIL / nome_arquivo
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def render_email_comprador(content_inner_html: str, ctx: Dict[str, Any]) -> str:
    layout = _ler_fragmento("layout_comprador.html")
    if not layout:
        return _substituir(content_inner_html, ctx)
    merged = layout.replace("{{CONTENT_BLOCK}}", content_inner_html)
    return _substituir(merged, ctx)


def _assunto_template(db: Session, chave_template_root: str, default_subject: str, ctx_para_default: Dict[str, Any]) -> str:
    """Usa Configuracao template_{root}_assunto se existir."""
    row = db.query(Configuracao).filter(Configuracao.chave == f"template_{chave_template_root}_assunto").first()
    if row and (row.valor or "").strip():
        subj = (row.valor or "").strip()
        try:
            return subj.format(**ctx_para_default)
        except Exception:
            return subj
    try:
        return default_subject.format(**ctx_para_default)
    except Exception:
        return default_subject


PAYMENT_METHOD_LABELS = {
    "pix": "PIX",
    "credit": "Cartão de crédito",
    "debit": "Cartão de débito",
    "boleto": "Boleto",
    "cash": "Dinheiro",
    "transfer": "Transferência",
}


def _resolver_forma_pagamento_label(db: Session, pedido: PedidoMarketplace) -> str:
    """Localiza a PaymentTransaction ativa do pedido (direta ou via checkout unificado)
    e retorna o rótulo amigável da forma de pagamento. Sem fallback silencioso:
    retorna 'Não informado' apenas quando realmente não houver registro de transação."""
    tx = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.pedido_id == pedido.id,
            PaymentTransaction.is_active.is_(True),
        )
        .order_by(PaymentTransaction.id.desc())
        .first()
    )
    if tx is None:
        link = (
            db.query(MarketplaceCheckoutSessionPedido)
            .filter(MarketplaceCheckoutSessionPedido.pedido_id == pedido.id)
            .order_by(MarketplaceCheckoutSessionPedido.id.desc())
            .first()
        )
        if link is not None:
            tx = (
                db.query(PaymentTransaction)
                .filter(
                    PaymentTransaction.checkout_session_id == link.session_id,
                    PaymentTransaction.is_active.is_(True),
                )
                .order_by(PaymentTransaction.id.desc())
                .first()
            )
    if tx is None or not (tx.payment_method or "").strip():
        return "Não informado"
    raw = (tx.payment_method or "").strip().lower()
    return PAYMENT_METHOD_LABELS.get(raw, tx.payment_method or "Não informado")


def _bloco_endereco_entrega_loja_html(pedido: PedidoMarketplace) -> str:
    """Retorna o bloco HTML do endereço de entrega para o e-mail da loja.
    Suprime quando a modalidade é retirada ou o endereço não foi informado."""
    tipo = (pedido.tipo_entrega or "").strip().lower()
    if tipo == "retirada":
        return (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="border:1px solid #e2e8f0;border-radius:12px;margin:0 0 18px;">'
            "<tr><td style=\"padding:16px 20px;\">"
            '<p style="margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;color:#64748b;">Entrega</p>'
            '<p style="margin:0;font-size:14px;color:#334155;">'
            "Modalidade: <strong style=\"color:#0f172a;\">Retirada na loja</strong>"
            "</p>"
            "</td></tr></table>"
        )
    endereco = (pedido.endereco_entrega or "").strip()
    if not endereco:
        return ""
    endereco_esc = html.escape(endereco)
    destinatario_raw = (pedido.destinatario_nome or "").strip()
    destinatario_html = ""
    if destinatario_raw:
        destinatario_html = (
            f'<p style="margin:0 0 6px;font-size:14px;color:#334155;">'
            f'Destinatário: <strong style="color:#0f172a;">{html.escape(destinatario_raw)}</strong>'
            "</p>"
        )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        'style="border:1px solid #e2e8f0;border-radius:12px;margin:0 0 18px;">'
        "<tr><td style=\"padding:16px 20px;\">"
        '<p style="margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;color:#64748b;">Endereço de entrega</p>'
        f"{destinatario_html}"
        f'<p style="margin:0;font-size:14px;color:#334155;line-height:1.5;">{endereco_esc}</p>'
        "</td></tr></table>"
    )


def _modalidade_label(pedido: PedidoMarketplace) -> str:
    tipo = (pedido.tipo_entrega or "").strip().lower()
    if tipo == "retirada":
        return "Retirada na loja"
    if tipo in ("entrega", "delivery", "envio"):
        return "Entrega"
    return tipo or "Não informada"


def build_context_loja(
    db: Session,
    pedido: PedidoMarketplace,
    loja: LojaMarketplace,
) -> Dict[str, Any]:
    """Contexto do e-mail HTML enviado à loja após pagamento confirmado."""
    app_base = get_app_url(db).rstrip("/")
    num = pedido.numero_pedido or str(pedido.id)
    nome_v = (loja.nome_fantasia or loja.nome_loja or "Loja").strip()
    nome_plataforma = (_cfg(db, CHAVE_NOME_PLATAFORMA) or "Ibix").strip()

    total_fmt = _fmt_moeda_br(pedido.total)
    subtotal_fmt = _fmt_moeda_br(pedido.subtotal)
    taxa_fmt = _fmt_moeda_br(pedido.taxa_entrega)

    data_pedido = ""
    paid = getattr(pedido, "updated_at", None) or getattr(pedido, "created_at", None)
    if paid is not None and hasattr(paid, "strftime"):
        try:
            data_pedido = paid.strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_pedido = ""

    forma_pagamento_label = _resolver_forma_pagamento_label(db, pedido)
    bloco_itens_pedido = _bloco_itens_pedido_html(db, pedido.id)
    bloco_endereco_entrega = _bloco_endereco_entrega_loja_html(pedido)

    link_painel_pedido = f"{app_base}/negocio/pedidos"

    preheader = (
        f"Pedido {num} pago — {pedido.comprador_nome or 'Comprador'} · R$ {total_fmt}. "
        "Confira itens, endereço e forma de pagamento."
    )

    comprador_nome = html.escape((pedido.comprador_nome or "").strip() or "—")
    comprador_email_raw = (pedido.comprador_email or "").strip()
    comprador_email = html.escape(comprador_email_raw) if comprador_email_raw else "—"
    comprador_telefone = html.escape((pedido.comprador_telefone or "").strip() or "—")
    comprador_documento = html.escape((pedido.comprador_documento or "").strip() or "—")

    return {
        "titulo_email": f"Pedido {num} — pagamento confirmado",
        "preheader": preheader,
        "nome_loja": html.escape(nome_v),
        "nome_plataforma": html.escape(nome_plataforma),
        "numero_pedido": html.escape(num),
        "data_pedido": data_pedido or "—",
        "forma_pagamento_label": html.escape(forma_pagamento_label),
        "modalidade_label": html.escape(_modalidade_label(pedido)),
        "subtotal_pedido": subtotal_fmt,
        "taxa_entrega_pedido": taxa_fmt,
        "total_pedido": total_fmt,
        "comprador_nome": comprador_nome,
        "comprador_email": comprador_email,
        "comprador_telefone": comprador_telefone,
        "comprador_documento": comprador_documento,
        "bloco_itens_pedido": bloco_itens_pedido,
        "bloco_endereco_entrega": bloco_endereco_entrega,
        "link_painel_pedido": link_painel_pedido,
        "texto_rodape_loja": (
            f"Mensagem automática do {nome_plataforma}. "
            "Você está recebendo porque é responsável por esta loja no painel."
        ),
    }


def render_email_loja(content_inner_html: str, ctx: Dict[str, Any]) -> str:
    layout = _ler_fragmento("layout_loja.html")
    if not layout:
        return _substituir(content_inner_html, ctx)
    merged = layout.replace("{{CONTENT_BLOCK}}", content_inner_html)
    return _substituir(merged, ctx)


def enviar_pedido_pago_loja(
    db: Session,
    pedido: PedidoMarketplace,
    loja: LojaMarketplace,
    ca_emails: list[str],
) -> int:
    """Envia o e-mail HTML rico aos responsáveis da loja após confirmação de pagamento.
    Retorna 1 em sucesso, 0 caso contrário."""
    destinatarios = [e for e in (ca_emails or []) if (e or "").strip()]
    if not destinatarios:
        return 0
    inner = _ler_fragmento("inner_pedido_pago_loja.html")
    if not inner:
        return 0
    ctx = build_context_loja(db, pedido, loja)
    inner_render = _substituir(inner, ctx)
    html_final = render_email_loja(inner_render, ctx)
    plain = _html_para_texto_simples(html_final)
    subj_ctx = {
        "numero_pedido": pedido.numero_pedido or str(pedido.id),
        "nome_vitrine": ctx["nome_loja"],
        "comprador": (pedido.comprador_nome or "Comprador").strip(),
    }
    subject = _assunto_template(
        db,
        "marketplace_pedido_pago_loja",
        "Pagamento confirmado — Pedido {numero_pedido} — {comprador}",
        subj_ctx,
    )
    svc = EmailService(db)
    ok = svc.send_email(
        to=destinatarios,
        subject=subject,
        body=plain or subject,
        html=html_final,
        funcao="marketplace",
        cliente_id=loja.cliente_id,
    )
    return 1 if ok else 0


def enviar_pedido_pago_comprador(db: Session, pedido: PedidoMarketplace, loja: LojaMarketplace) -> bool:
    email_to = (pedido.comprador_email or "").strip()
    if not email_to:
        return False
    inner = _ler_fragmento("inner_pedido_pago.html")
    if not inner:
        return False
    ctx = build_context_comprador(db, pedido, loja)
    inner_render = _substituir(inner, ctx)
    html_final = render_email_comprador(inner_render, ctx)
    plain = _html_para_texto_simples(html_final)
    subj_ctx = {"numero_pedido": ctx["numero_pedido"], "nome_vitrine": ctx["nome_vitrine"]}
    subject = _assunto_template(
        db,
        "marketplace_pedido_pago_comprador",
        "Pagamento confirmado — Pedido {numero_pedido}",
        subj_ctx,
    )
    svc = EmailService(db)
    return svc.send_email(
        to=[email_to],
        subject=subject,
        body=plain or subject,
        html=html_final,
        funcao="marketplace",
        cliente_id=loja.cliente_id,
    )


def _copy_status_pedido(codigo: str, status_label: str, nome_vitrine: str) -> Tuple[str, str, str]:
    c = (codigo or "").strip().lower()
    label = status_label or codigo
    if c == "confirmado":
        return (
            "Pedido confirmado",
            f"a loja {nome_vitrine} confirmou sua compra após o pagamento.",
            "Em breve você pode ver próximas atualizações (preparação e envio ou retirada) por aqui.",
        )
    if c == "preparando":
        return (
            "Estamos preparando seu pedido",
            f"a equipe da {nome_vitrine} está separando seus itens.",
            "Quando o status mudar novamente, avisaremos você por e-mail.",
        )
    if c in ("enviado", "despachado"):
        return (
            "Pedido enviado",
            "seu pedido foi despachado ou está a caminho, conforme a forma de entrega escolhida.",
            "Acompanhe o andamento pelo link abaixo.",
        )
    if c == "entregue":
        return (
            "Pedido entregue",
            "registramos a entrega ou disponibilização do seu pedido.",
            "Obrigado por comprar na vitrine. Qualquer dúvida, fale com a loja.",
        )
    if c == "cancelado":
        return (
            "Pedido cancelado",
            "o pedido foi marcado como cancelado.",
            "Se você já havia pago e não reconhece este cancelamento, entre em contato com a loja ou com o suporte da plataforma.",
        )
    if c == "aguardando_pagamento":
        return (
            "Aguardando pagamento",
            "ainda estamos aguardando a confirmação do pagamento.",
            "Assim que o pagamento for confirmado, você receberá outra mensagem.",
        )
    return (
        "Atualização do seu pedido",
        f"o status do seu pedido foi atualizado para {label}.",
        f"A vitrine {nome_vitrine} pode entrar em contato para mais detalhes.",
    )


def enviar_pedido_status_comprador(
    db: Session,
    pedido: PedidoMarketplace,
    loja: LojaMarketplace,
    status_codigo: str,
    status_label: str,
) -> bool:
    email_to = (pedido.comprador_email or "").strip()
    if not email_to:
        return False
    inner = _ler_fragmento("inner_pedido_status.html")
    if not inner:
        return False
    ctx = build_context_comprador(db, pedido, loja)
    nome_v = ctx["nome_vitrine"]
    headline, lead, detail = _copy_status_pedido(status_codigo, status_label, nome_v)
    ctx.update(
        {
            "headline": headline,
            "lead": lead,
            "detail": detail,
            "status_label": status_label or status_codigo,
            "preheader": f"{headline} — pedido {ctx['numero_pedido']}",
            "titulo_email": headline,
        }
    )
    inner_render = _substituir(inner, ctx)
    html_final = render_email_comprador(inner_render, ctx)
    plain = _html_para_texto_simples(html_final)
    subject = _assunto_template(
        db,
        "marketplace_pedido_status_comprador",
        "{headline} — pedido {numero_pedido}",
        {"headline": headline, "numero_pedido": ctx["numero_pedido"], "nome_vitrine": nome_v},
    )
    svc = EmailService(db)
    return svc.send_email(
        to=[email_to],
        subject=subject,
        body=plain or subject,
        html=html_final,
        funcao="marketplace",
        cliente_id=loja.cliente_id,
    )


def _label_entrega(codigo: str) -> str:
    m = {
        ACEITA: "Entrega aceita pelo entregador",
        EM_RETIRADA: "Entregador a caminho da retirada",
        RETIRADA: "Retirada na loja concluída",
        EM_ROTA: "Saiu para entrega",
        ENTREGUE: "Pedido entregue",
        FALHA_ENTREGA: "Problema na entrega",
        CANCELADA: "Entrega cancelada",
        EXPIRADA: "Entrega expirada",
        DISPONIVEL: "Entrega disponível para motoristas",
        AGUARDANDO_PUBLICACAO: "Aguardando publicação da entrega",
    }
    return m.get((codigo or "").strip(), codigo or "Atualização da entrega")


def _copy_entrega(codigo: str, nome_vitrine: str) -> Tuple[str, str, str]:
    cl = (codigo or "").strip()
    label = _label_entrega(cl)
    if cl == EM_ROTA:
        return (
            "Saiu para entrega",
            "seu pedido está a caminho do endereço informado.",
            "Mantenha seu telefone disponível para o entregador.",
        )
    if cl == ENTREGUE:
        return (
            "Entrega concluída",
            "registramos a entrega do seu pedido.",
            "Se algo não estiver correto, fale com a loja.",
        )
    if cl == FALHA_ENTREGA:
        return (
            "Atenção: entrega",
            "houve um problema na tentativa de entrega.",
            "Entre em contato com a vitrine para combinar os próximos passos.",
        )
    if cl == RETIRADA:
        return (
            "Retirada realizada",
            "o entregador retirou seu pedido na loja.",
            "Em seguida ele seguirá para a entrega no seu endereço, se aplicável.",
        )
    if cl == CANCELADA:
        return (
            "Entrega cancelada",
            "a entrega foi cancelada no sistema.",
            f"Em caso de dúvida, contate a loja **{nome_vitrine}**.".replace("**", ""),
        )
    return (
        "Atualização da entrega",
        f"o status da logística foi atualizado para: {label}.",
        "Acompanhe pelo link do seu pedido.",
    )


def enviar_entrega_status_comprador(
    db: Session,
    pedido: PedidoMarketplace,
    loja: LojaMarketplace,
    novo_status: str,
) -> bool:
    email_to = (pedido.comprador_email or "").strip()
    if not email_to:
        return False
    inner = _ler_fragmento("inner_entrega_status.html")
    if not inner:
        return False
    ctx = build_context_comprador(db, pedido, loja)
    nome_v = ctx["nome_vitrine"]
    headline, lead, detail = _copy_entrega(novo_status, nome_v)
    label = _label_entrega(novo_status)
    ctx.update(
        {
            "headline": headline,
            "lead": lead,
            "detail": detail,
            "status_entrega_label": label,
            "preheader": f"{headline} — {ctx['numero_pedido']}",
            "titulo_email": headline,
        }
    )
    inner_render = _substituir(inner, ctx)
    html_final = render_email_comprador(inner_render, ctx)
    plain = _html_para_texto_simples(html_final)
    subject = _assunto_template(
        db,
        "marketplace_entrega_status_comprador",
        "{headline} — pedido {numero_pedido}",
        {"headline": headline, "numero_pedido": ctx["numero_pedido"]},
    )
    svc = EmailService(db)
    return svc.send_email(
        to=[email_to],
        subject=subject,
        body=plain or subject,
        html=html_final,
        funcao="marketplace",
        cliente_id=loja.cliente_id,
    )
