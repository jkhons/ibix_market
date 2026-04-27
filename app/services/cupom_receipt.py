# PDV Ibix - Geração de conteúdo do cupom de venda (não fiscal)
import html as html_lib
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, Tuple


def _fmt_moeda(valor: Any) -> str:
    if valor is None:
        return "0,00"
    try:
        n = float(Decimal(str(valor)))
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "0,00"


def _truncar(texto: str, largura: int) -> str:
    if not texto:
        return ""
    s = str(texto).strip()
    return (s[: largura - 3] + "...") if len(s) > largura else s


def _centralizar(texto: str, largura: int) -> str:
    s = str(texto).strip()
    if len(s) >= largura:
        return s[:largura]
    pad = (largura - len(s)) // 2
    return " " * pad + s + " " * (largura - len(s) - pad)


def _linha_separadora(largura: int, char: str = "-") -> str:
    return char * min(largura, 48)


def gerar_cupom_nao_fiscal(
    estabelecimento_nome: str,
    numero_venda: str,
    data_venda: datetime,
    tipo_pagamento: Optional[str],
    valor_pago: Any,
    troco: Any,
    subtotal: Any,
    desconto: Any,
    acrescimo: Any,
    total: Any,
    itens: List[dict],
    largura: int = 48,
) -> tuple[List[str], str]:
    """
    Gera conteúdo do cupom não fiscal: (linhas para térmica, html para browser).
    itens: lista de dict com keys: nome (ou produto_nome), quantidade, valor_unitario, valor_total.
    """
    linhas: List[str] = []
    L = largura

    # Cabeçalho
    linhas.append(_centralizar(estabelecimento_nome or "Estabelecimento", L))
    linhas.append(_linha_separadora(L))
    linhas.append(f"Venda: {numero_venda or ''}")
    if data_venda:
        try:
            dt = data_venda if isinstance(data_venda, datetime) else datetime.fromisoformat(str(data_venda).replace("Z", "+00:00"))
            linhas.append(dt.strftime("%d/%m/%Y %H:%M"))
        except Exception:
            linhas.append(str(data_venda)[:19])
    linhas.append(_linha_separadora(L))

    # Itens
    for item in itens:
        nome = item.get("nome") or item.get("produto_nome") or "Item"
        qtd = item.get("quantidade", 0)
        v_unit = item.get("valor_unitario", 0)
        v_total = item.get("valor_total", 0)
        nome_curto = _truncar(nome, L - 14)
        linhas.append(nome_curto)
        linhas.append(f"  {float(qtd):.2f} x {_fmt_moeda(v_unit)} = R$ {_fmt_moeda(v_total)}")

    linhas.append(_linha_separadora(L))
    linhas.append(f"Subtotal:    R$ {_fmt_moeda(subtotal)}")
    if float(desconto or 0) > 0:
        linhas.append(f"Desconto:    R$ {_fmt_moeda(desconto)}")
    if float(acrescimo or 0) > 0:
        linhas.append(f"Acrescimo:   R$ {_fmt_moeda(acrescimo)}")
    linhas.append(f"TOTAL:       R$ {_fmt_moeda(total)}")
    linhas.append(f"Pagamento:   {(tipo_pagamento or 'N/I').upper()}")
    linhas.append(f"Valor pago:  R$ {_fmt_moeda(valor_pago)}")
    if float(troco or 0) > 0:
        linhas.append(f"Troco:       R$ {_fmt_moeda(troco)}")
    linhas.append(_linha_separadora(L))
    linhas.append(_centralizar("Obrigado pela preferencia!", L))
    linhas.append("")

    # HTML para window.print()
    html_parts = [
        '<div class="cupom-impressao" style="font-family: monospace; font-size: 12px; max-width: 280px; margin: 0 auto; padding: 12px;">',
        f'<div style="text-align: center; font-weight: bold; margin-bottom: 8px;">{estabelecimento_nome or "Estabelecimento"}</div>',
        '<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">',
        f'<div>Venda: {numero_venda or ""}</div>',
    ]
    if data_venda:
        try:
            dt = data_venda if isinstance(data_venda, datetime) else datetime.fromisoformat(str(data_venda).replace("Z", "+00:00"))
            html_parts.append(f'<div>{dt.strftime("%d/%m/%Y %H:%M")}</div>')
        except Exception:
            html_parts.append(f'<div>{data_venda}</div>')
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    for item in itens:
        nome = item.get("nome") or item.get("produto_nome") or "Item"
        qtd = item.get("quantidade", 0)
        v_unit = item.get("valor_unitario", 0)
        v_total = item.get("valor_total", 0)
        html_parts.append(f'<div>{nome[:50]}</div>')
        html_parts.append(f'<div style="margin-left: 12px;">{float(qtd):.2f} x R$ {_fmt_moeda(v_unit)} = R$ {_fmt_moeda(v_total)}</div>')
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    html_parts.append(f'<div>Subtotal: R$ {_fmt_moeda(subtotal)}</div>')
    if float(desconto or 0) > 0:
        html_parts.append(f'<div>Desconto: R$ {_fmt_moeda(desconto)}</div>')
    if float(acrescimo or 0) > 0:
        html_parts.append(f'<div>Acrescimo: R$ {_fmt_moeda(acrescimo)}</div>')
    html_parts.append(f'<div style="font-weight: bold;">TOTAL: R$ {_fmt_moeda(total)}</div>')
    html_parts.append(f'<div>Pagamento: {(tipo_pagamento or "N/I").upper()}</div>')
    html_parts.append(f'<div>Valor pago: R$ {_fmt_moeda(valor_pago)}</div>')
    if float(troco or 0) > 0:
        html_parts.append(f'<div>Troco: R$ {_fmt_moeda(troco)}</div>')
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    html_parts.append('<div style="text-align: center;">Obrigado pela preferencia!</div>')
    html_parts.append("</div>")
    html = "\n".join(html_parts)

    return linhas, html


def _data_hora_cupom(dt: Any) -> Tuple[str, str]:
    """Retorna (linha_texto, fragmento_html_div) para data/hora."""
    if not dt:
        return "", ""
    try:
        d = dt if isinstance(dt, datetime) else datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
        s = d.strftime("%d/%m/%Y %H:%M")
        return s, f'<div>{html_lib.escape(s)}</div>'
    except Exception:
        s = str(dt)[:19]
        return s, f'<div>{html_lib.escape(s)}</div>'


def _linhas_observacao(obs: Optional[str], L: int, max_lines: int = 5) -> Tuple[List[str], List[str]]:
    """Texto multilinha truncado para cupom térmico e HTML."""
    if not (obs or "").strip():
        return [], []
    linhas_txt: List[str] = []
    linhas_html: List[str] = []
    linhas_txt.append(_truncar("Observacoes:", L))
    for raw in str(obs).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = (raw or "").strip()
        if not line:
            continue
        linhas_txt.append("  " + _truncar(line, L - 2))
        linhas_html.append(f'<div style="white-space: pre-wrap;">{html_lib.escape(_truncar(line, 200))}</div>')
        if len(linhas_txt) >= max_lines + 1:
            linhas_txt.append("  ...")
            linhas_html.append("<div>...</div>")
            break
    return linhas_txt, linhas_html


def gerar_cupom_resumo_pedido_negocio(
    estabelecimento_nome: str,
    numero_pedido: str,
    data_referencia: Any,
    status: str,
    subtotal: Any,
    desconto: Any,
    acrescimo: Any,
    total: Any,
    observacoes: Optional[str],
    itens: List[dict],
    largura: int = 48,
) -> Tuple[List[str], str]:
    """
    Cupom não fiscal de pedido interno (módulo Orçamento/Pedido): sem bloco de pagamento PDV.
    itens: dicts com nome (ou descricao_produto), quantidade, valor_unitario, valor_total (ou total_item).
    """
    linhas: List[str] = []
    L = largura
    linhas.append(_centralizar((estabelecimento_nome or "Estabelecimento").strip() or "Estabelecimento", L))
    linhas.append(_centralizar("PEDIDO", L))
    linhas.append(_linha_separadora(L))
    linhas.append(f"Pedido: {numero_pedido or ''}")
    dh_txt, _ = _data_hora_cupom(data_referencia)
    if dh_txt:
        linhas.append(dh_txt)
    linhas.append(f"Status: {(status or '').strip()}")
    linhas.append(_linha_separadora(L))

    for item in itens:
        nome = (item.get("nome") or item.get("descricao_produto") or item.get("produto_nome") or "Item").strip()
        cod = (item.get("codigo_produto") or "").strip()
        if cod:
            nome = f"{cod} {nome}".strip()
        qtd = item.get("quantidade", 0)
        v_unit = item.get("valor_unitario", item.get("preco_unitario", 0))
        v_total = item.get("valor_total", item.get("total_item", 0))
        nome_curto = _truncar(nome, L - 14)
        linhas.append(nome_curto)
        linhas.append(f"  {float(qtd):.2f} x {_fmt_moeda(v_unit)} = R$ {_fmt_moeda(v_total)}")

    linhas.append(_linha_separadora(L))
    linhas.append(f"Subtotal:    R$ {_fmt_moeda(subtotal)}")
    if float(desconto or 0) > 0:
        linhas.append(f"Desconto:    R$ {_fmt_moeda(desconto)}")
    if float(acrescimo or 0) > 0:
        linhas.append(f"Acrescimo:   R$ {_fmt_moeda(acrescimo)}")
    linhas.append(f"TOTAL:       R$ {_fmt_moeda(total)}")
    otxt, _ = _linhas_observacao(observacoes, L)
    linhas.extend(otxt)
    linhas.append(_linha_separadora(L))
    linhas.append(_centralizar("Documento sem valor fiscal", L))
    linhas.append("")

    _, dh_html = _data_hora_cupom(data_referencia)
    html_parts: List[str] = [
        '<div class="cupom-impressao" style="font-family: monospace; font-size: 12px; max-width: 280px; margin: 0 auto; padding: 12px;">',
        f'<div style="text-align: center; font-weight: bold;">{html_lib.escape((estabelecimento_nome or "Estabelecimento").strip() or "Estabelecimento")}</div>',
        '<div style="text-align: center; font-weight: 600;">PEDIDO</div>',
        '<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">',
        f'<div>Pedido: {html_lib.escape(numero_pedido or "")}</div>',
    ]
    if dh_html:
        html_parts.append(dh_html)
    html_parts.append(f'<div>Status: {html_lib.escape((status or "").strip())}</div>')
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    for item in itens:
        nome = (item.get("nome") or item.get("descricao_produto") or item.get("produto_nome") or "Item").strip()
        cod = (item.get("codigo_produto") or "").strip()
        if cod:
            nome = f"{cod} {nome}".strip()
        qtd = item.get("quantidade", 0)
        v_unit = item.get("valor_unitario", item.get("preco_unitario", 0))
        v_total = item.get("valor_total", item.get("total_item", 0))
        html_parts.append(f'<div>{html_lib.escape(nome[:80])}</div>')
        html_parts.append(
            f'<div style="margin-left: 12px;">{float(qtd):.2f} x R$ {_fmt_moeda(v_unit)} = R$ {_fmt_moeda(v_total)}</div>'
        )
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    html_parts.append(f'<div>Subtotal: R$ {_fmt_moeda(subtotal)}</div>')
    if float(desconto or 0) > 0:
        html_parts.append(f'<div>Desconto: R$ {_fmt_moeda(desconto)}</div>')
    if float(acrescimo or 0) > 0:
        html_parts.append(f'<div>Acrescimo: R$ {_fmt_moeda(acrescimo)}</div>')
    html_parts.append(f'<div style="font-weight: bold;">TOTAL: R$ {_fmt_moeda(total)}</div>')
    _, ohtml = _linhas_observacao(observacoes, L)
    html_parts.extend(ohtml)
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    html_parts.append('<div style="text-align: center; font-size: 11px;">Documento sem valor fiscal</div>')
    html_parts.append("</div>")
    return linhas, "\n".join(html_parts)


def gerar_cupom_resumo_pedido_marketplace(
    loja_exibicao: str,
    numero_pedido: str,
    data_referencia: Any,
    comprador_nome: str,
    comprador_telefone: Optional[str],
    destinatario_nome: Optional[str],
    tipo_entrega: str,
    endereco_entrega: Optional[str],
    status_pedido: str,
    status_pagamento: str,
    subtotal: Any,
    desconto: Any,
    taxa_entrega: Any,
    total: Any,
    itens: List[dict],
    largura: int = 48,
) -> Tuple[List[str], str]:
    """
    Cupom não fiscal de pedido marketplace (gestão loja).
    itens: nome, quantidade, valor_unitario (preco_unitario), valor_total (preco_total).
    """
    linhas: List[str] = []
    L = largura
    linhas.append(_centralizar((loja_exibicao or "Loja").strip() or "Loja", L))
    linhas.append(_centralizar("PEDIDO MARKETPLACE", L))
    linhas.append(_linha_separadora(L))
    linhas.append(f"Pedido: {numero_pedido or ''}")
    dh_txt, _ = _data_hora_cupom(data_referencia)
    if dh_txt:
        linhas.append(dh_txt)
    linhas.append(_truncar(f"Cliente: {comprador_nome or ''}", L))
    if (comprador_telefone or "").strip():
        linhas.append(_truncar(f"Tel: {comprador_telefone}", L))
    if (destinatario_nome or "").strip():
        linhas.append(_truncar(f"Dest: {destinatario_nome}", L))
    linhas.append(f"Entrega: {(tipo_entrega or '').strip()}")
    if (endereco_entrega or "").strip():
        addr = " ".join((endereco_entrega or "").split())
        linhas.append(_truncar(addr, L))
        if len(addr) > L:
            linhas.append(_truncar(addr[L:], L))
    linhas.append(f"Status pedido: {(status_pedido or '').strip()}")
    linhas.append(f"Status pagto: {(status_pagamento or '').strip()}")
    linhas.append(_linha_separadora(L))

    for item in itens:
        nome = (item.get("nome") or item.get("nome_produto_snapshot") or "Item").strip()
        qtd = item.get("quantidade", 0)
        v_unit = item.get("valor_unitario", item.get("preco_unitario", 0))
        v_total = item.get("valor_total", item.get("preco_total", 0))
        nome_curto = _truncar(nome, L - 14)
        linhas.append(nome_curto)
        linhas.append(f"  {float(qtd):.2f} x {_fmt_moeda(v_unit)} = R$ {_fmt_moeda(v_total)}")

    linhas.append(_linha_separadora(L))
    linhas.append(f"Subtotal:    R$ {_fmt_moeda(subtotal)}")
    if float(desconto or 0) > 0:
        linhas.append(f"Desconto:    R$ {_fmt_moeda(desconto)}")
    if float(taxa_entrega or 0) > 0:
        linhas.append(f"Entrega:     R$ {_fmt_moeda(taxa_entrega)}")
    linhas.append(f"TOTAL:       R$ {_fmt_moeda(total)}")
    linhas.append(_linha_separadora(L))
    linhas.append(_centralizar("Documento sem valor fiscal", L))
    linhas.append("")

    _, dh_html = _data_hora_cupom(data_referencia)
    html_parts: List[str] = [
        '<div class="cupom-impressao" style="font-family: monospace; font-size: 12px; max-width: 280px; margin: 0 auto; padding: 12px;">',
        f'<div style="text-align: center; font-weight: bold;">{html_lib.escape((loja_exibicao or "Loja").strip() or "Loja")}</div>',
        '<div style="text-align: center; font-weight: 600;">PEDIDO MARKETPLACE</div>',
        '<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">',
        f'<div>Pedido: {html_lib.escape(numero_pedido or "")}</div>',
    ]
    if dh_html:
        html_parts.append(dh_html)
    html_parts.append(f'<div>Cliente: {html_lib.escape((comprador_nome or "").strip()[:120])}</div>')
    if (comprador_telefone or "").strip():
        html_parts.append(f'<div>Tel: {html_lib.escape(str(comprador_telefone).strip()[:40])}</div>')
    if (destinatario_nome or "").strip():
        html_parts.append(f'<div>Dest: {html_lib.escape(str(destinatario_nome).strip()[:120])}</div>')
    html_parts.append(f'<div>Entrega: {html_lib.escape((tipo_entrega or "").strip()[:40])}</div>')
    if (endereco_entrega or "").strip():
        html_parts.append(
            f'<div style="white-space: pre-wrap; font-size: 11px;">{html_lib.escape(_truncar(str(endereco_entrega).strip(), 400))}</div>'
        )
    html_parts.append(f'<div>Status pedido: {html_lib.escape((status_pedido or "").strip()[:60])}</div>')
    html_parts.append(f'<div>Status pagto: {html_lib.escape((status_pagamento or "").strip()[:60])}</div>')
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    for item in itens:
        nome = (item.get("nome") or item.get("nome_produto_snapshot") or "Item").strip()
        qtd = item.get("quantidade", 0)
        v_unit = item.get("valor_unitario", item.get("preco_unitario", 0))
        v_total = item.get("valor_total", item.get("preco_total", 0))
        html_parts.append(f'<div>{html_lib.escape(nome[:80])}</div>')
        html_parts.append(
            f'<div style="margin-left: 12px;">{float(qtd):.2f} x R$ {_fmt_moeda(v_unit)} = R$ {_fmt_moeda(v_total)}</div>'
        )
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    html_parts.append(f'<div>Subtotal: R$ {_fmt_moeda(subtotal)}</div>')
    if float(desconto or 0) > 0:
        html_parts.append(f'<div>Desconto: R$ {_fmt_moeda(desconto)}</div>')
    if float(taxa_entrega or 0) > 0:
        html_parts.append(f'<div>Entrega: R$ {_fmt_moeda(taxa_entrega)}</div>')
    html_parts.append(f'<div style="font-weight: bold;">TOTAL: R$ {_fmt_moeda(total)}</div>')
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    html_parts.append('<div style="text-align: center; font-size: 11px;">Documento sem valor fiscal</div>')
    html_parts.append("</div>")
    return linhas, "\n".join(html_parts)
