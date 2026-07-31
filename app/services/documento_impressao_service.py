# Motor unificado de templates de impressão (Orçamento · OS)
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from jinja2 import Environment, StrictUndefined, select_autoescape
from sqlalchemy.orm import Session

from app.models.documento_impressao_template import DocumentoImpressaoTemplate
from app.models.orcamento import Orcamento
from app.models.ordem_servico import OrdemServico
from app.services.pdf_orcamento_pedido import gerar_pdf_orcamento

_jinja_env = Environment(
    autoescape=select_autoescape(["html", "xml"]),
    undefined=StrictUndefined,
)


def _fmt_dec(v) -> str:
    if v is None:
        return "0,00"
    if isinstance(v, Decimal):
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_date(d) -> str:
    if d is None:
        return ""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y %H:%M")
    return str(d)


def template_padrao_tenant(
    db: Session,
    tenant_id: int,
    tipo_documento: str,
) -> Optional[DocumentoImpressaoTemplate]:
    return (
        db.query(DocumentoImpressaoTemplate)
        .filter(
            DocumentoImpressaoTemplate.tenant_id == tenant_id,
            DocumentoImpressaoTemplate.tipo_documento == tipo_documento,
            DocumentoImpressaoTemplate.is_padrao.is_(True),
            DocumentoImpressaoTemplate.ativo.is_(True),
        )
        .first()
    )


def montar_contexto_orcamento(orcamento: Orcamento, brand: Optional[Any] = None) -> dict:
    itens = []
    for it in orcamento.itens or []:
        itens.append(
            {
                "codigo_produto": it.codigo_produto,
                "descricao_produto": it.descricao_produto,
                "quantidade": float(it.quantidade) if it.quantidade is not None else 0,
                "preco_unitario": _fmt_dec(it.preco_unitario),
                "total_item": _fmt_dec(it.total_item),
            }
        )
    return {
        "numero_orcamento": orcamento.numero_orcamento,
        "data_validade": _fmt_date(orcamento.data_validade),
        "status": orcamento.status,
        "cliente_nome": getattr(orcamento.cliente, "nome", None) if orcamento.cliente else None,
        "destinatario_nome": orcamento.destinatario_nome,
        "vendedor_nome": orcamento.vendedor.nome if getattr(orcamento, "vendedor", None) else None,
        "subtotal": _fmt_dec(orcamento.subtotal),
        "desconto": _fmt_dec(orcamento.desconto),
        "total": _fmt_dec(orcamento.total),
        "observacoes": orcamento.observacoes or "",
        "condicoes_pagamento": orcamento.condicoes_pagamento or "",
        "itens": itens,
        "brand_nome": getattr(brand, "nome_exibicao", None) if brand else None,
        "brand_logo_url": getattr(brand, "logo_url", None) if brand else None,
    }


def montar_contexto_ordem_servico(ordem: OrdemServico, brand: Optional[Any] = None) -> dict:
    itens = []
    subtotal = Decimal("0")
    desconto_total = Decimal("0")
    for it in ordem.itens or []:
        vt = Decimal(str(it.valor_total or 0))
        subtotal += vt
        desconto_total += Decimal(str(it.desconto or 0))
        itens.append(
            {
                "descricao": it.nome or "",
                "quantidade": float(it.quantidade) if it.quantidade is not None else 0,
                "valor_unitario": _fmt_dec(it.valor_unitario),
                "valor_total": _fmt_dec(it.valor_total),
            }
        )
    total = subtotal
    tipo = getattr(ordem, "tipo_rel", None)
    return {
        "codigo": ordem.codigo,
        "status": ordem.status,
        "cliente_nome": getattr(ordem.cliente, "nome", None) if ordem.cliente else None,
        "tipo_nome": tipo.nome if tipo else None,
        "data_abertura": _fmt_date(ordem.data_abertura),
        "observacoes": ordem.observacoes or "",
        "subtotal": _fmt_dec(subtotal),
        "desconto": _fmt_dec(desconto_total),
        "total": _fmt_dec(total),
        "itens": itens,
        "brand_nome": getattr(brand, "nome_exibicao", None) if brand else None,
        "brand_logo_url": getattr(brand, "logo_url", None) if brand else None,
    }


def contexto_mock(tipo_documento: str) -> dict:
    if tipo_documento == "ordem_servico":
        return {
            "codigo": "OS-0001",
            "status": "aberta",
            "cliente_nome": "Cliente exemplo",
            "tipo_nome": "Manutenção",
            "data_abertura": "18/06/2026",
            "observacoes": "Observação de exemplo",
            "subtotal": "100,00",
            "desconto": "0,00",
            "total": "100,00",
            "itens": [{"descricao": "Serviço", "quantidade": 1, "valor_unitario": "100,00", "valor_total": "100,00"}],
            "brand_nome": "Marca",
            "brand_logo_url": "/static/img/logo.png",
        }
    return {
        "numero_orcamento": "ORC-0001",
        "data_validade": "30/06/2026",
        "status": "emitido",
        "cliente_nome": "Unidade exemplo",
        "destinatario_nome": "Consumidor exemplo",
        "vendedor_nome": "Vendedor exemplo",
        "subtotal": "100,00",
        "desconto": "0,00",
        "total": "100,00",
        "observacoes": "",
        "condicoes_pagamento": "À vista",
        "itens": [{"codigo_produto": "P1", "descricao_produto": "Item", "quantidade": 1, "preco_unitario": 100, "total_item": 100}],
        "brand_nome": "Marca",
        "brand_logo_url": "/static/img/logo.png",
    }


def renderizar_html(conteudo_html: str, contexto: dict, css_extra: Optional[str] = None) -> str:
    tpl = _jinja_env.from_string(conteudo_html)
    body = tpl.render(**contexto)
    css = css_extra or ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><style>{css}</style></head><body>{body}</body></html>"""


def gerar_pdf_bytes(html: str) -> bytes:
    from app.services.pdf_orcamento_pedido import _html_to_pdf

    return _html_to_pdf(html)


def gerar_pdf_orcamento_com_template(
    orcamento: Orcamento,
    template: DocumentoImpressaoTemplate,
    brand: Optional[Any] = None,
) -> bytes:
    ctx = montar_contexto_orcamento(orcamento, brand)
    html = renderizar_html(template.conteudo_html, ctx, template.css_extra)
    return gerar_pdf_bytes(html)


def gerar_pdf_ordem_servico_com_template(
    ordem: OrdemServico,
    template: DocumentoImpressaoTemplate,
    brand: Optional[Any] = None,
) -> bytes:
    ctx = montar_contexto_ordem_servico(ordem, brand)
    html = renderizar_html(template.conteudo_html, ctx, template.css_extra)
    return gerar_pdf_bytes(html)


def gerar_pdf_orcamento_fallback(dados: dict) -> bytes:
    """Compatibilidade: PDF legado quando não há template configurado."""
    return gerar_pdf_orcamento(dados)
