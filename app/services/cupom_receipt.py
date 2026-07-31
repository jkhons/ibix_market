from app.core.document_ref import compact_doc_ref
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
    return char * largura


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


def _label_forma_pagamento(forma: Optional[str]) -> str:
    chave = (forma or "").strip().lower()
    labels = {
        "dinheiro": "Dinheiro",
        "cartao_credito": "Cartao Credito",
        "cartao_debito": "Cartao Debito",
        "pix": "PIX",
        "boleto": "Boleto",
        "transferencia": "Transferencia",
        "vale": "Vale",
        "crediario": "Crediario",
    }
    return labels.get(chave, chave.upper() if chave else "N/I")


def _html_estilo_cupom_caixa(largura_mm: int = 80) -> str:
    """Estilo do wrapper HTML — bobina 80 mm (referência visual do cupom de pedidos)."""
    w = largura_mm - 8
    return (
        f"font-family:monospace;font-size:11px;line-height:1.35;"
        f"width:{w}mm;max-width:{w}mm;margin:0 auto;padding:2mm 3mm;color:#000;background:#fff;"
    )


def _hr_cupom() -> str:
    return '<hr style="border:none;border-top:1px dashed #333;margin:8px 0;">'


def gerar_cupom_resumo_venda_caixa(
    estabelecimento_nome: str,
    numero_venda: str,
    data_referencia: Any,
    subtotal: Any,
    desconto: Any,
    acrescimo: Any,
    total: Any,
    tipo_pagamento: Optional[str],
    valor_pago: Any,
    troco: Any,
    itens: List[dict],
    observacoes: Optional[str] = None,
    cliente_nome: Optional[str] = None,
    vendedor_nome: Optional[str] = None,
    pagamentos: Optional[List[dict]] = None,
    empresa_fiscal: Optional[dict] = None,
    largura: int = 48,
    largura_mm: int = 80,
) -> Tuple[List[str], str]:
    """
    Cupom não fiscal do caixa (PDV / vendas).
    Mesmo padrão de gerar_cupom_resumo_pedido_negocio, com bloco de pagamento e largura em mm para térmica.
    """
    L = largura if largura else 48
    numero_exibicao = compact_doc_ref(numero_venda, fallback="")
    linhas: List[str] = []
    estilo = _html_estilo_cupom_caixa(largura_mm)
    html_parts: List[str] = [
        f'<div class="cupom-impressao cupom-caixa" data-largura-mm="{largura_mm}" style="{estilo}">',
    ]

    nome_topo = (estabelecimento_nome or "Estabelecimento").strip() or "Estabelecimento"
    if empresa_fiscal:
        fantasia = (empresa_fiscal.get("nome_fantasia") or "").strip()
        razao = (empresa_fiscal.get("razao_social") or "").strip()
        if fantasia:
            nome_topo = fantasia
            linhas.append(_centralizar(_truncar(fantasia, L), L))
            html_parts.append(f'<div style="text-align:center;font-weight:bold;">{html_lib.escape(fantasia[:80])}</div>')
            if razao and razao.lower() != fantasia.lower():
                linhas.append(_centralizar(_truncar(razao, L), L))
                html_parts.append(f'<div style="text-align:center;font-size:10px;">{html_lib.escape(razao[:80])}</div>')
        elif razao:
            nome_topo = razao
            linhas.append(_centralizar(_truncar(razao, L), L))
            html_parts.append(f'<div style="text-align:center;font-weight:bold;">{html_lib.escape(razao[:80])}</div>')
        cnpj = (empresa_fiscal.get("cnpj") or "").strip()
        if cnpj:
            linhas.append(_centralizar(f"CNPJ {cnpj}", L))
            html_parts.append(f'<div style="text-align:center;font-size:10px;">CNPJ {html_lib.escape(cnpj)}</div>')
        ie = (empresa_fiscal.get("ie") or "").strip()
        if ie:
            linhas.append(_centralizar(f"IE {ie}", L))
            html_parts.append(f'<div style="text-align:center;font-size:10px;">IE {html_lib.escape(ie)}</div>')
        for end in empresa_fiscal.get("endereco_linhas") or []:
            end_s = str(end).strip()
            if end_s:
                linhas.append(_centralizar(_truncar(end_s, L), L))
                html_parts.append(f'<div style="text-align:center;font-size:10px;">{html_lib.escape(end_s[:100])}</div>')
        tel = (empresa_fiscal.get("telefone") or "").strip()
        if tel:
            linhas.append(_centralizar(f"Tel {tel}", L))
            html_parts.append(f'<div style="text-align:center;font-size:10px;">Tel {html_lib.escape(tel)}</div>')
    else:
        linhas.append(_centralizar(_truncar(nome_topo, L), L))
        html_parts.append(f'<div style="text-align:center;font-weight:bold;">{html_lib.escape(nome_topo[:80])}</div>')

    linhas.append(_centralizar("VENDA", L))
    linhas.append(_linha_separadora(L))
    html_parts.append('<div style="text-align:center;font-weight:600;">VENDA</div>')
    html_parts.append(_hr_cupom())

    linhas.append(f"Venda: {numero_exibicao}")
    html_parts.append(f'<div>Venda: {html_lib.escape(numero_exibicao)}</div>')
    dh_txt, dh_html = _data_hora_cupom(data_referencia)
    if dh_txt:
        linhas.append(dh_txt)
        html_parts.append(dh_html)
    if (cliente_nome or "").strip():
        linhas.append(_truncar(f"Cliente: {cliente_nome.strip()}", L))
        html_parts.append(f'<div>Cliente: {html_lib.escape(cliente_nome.strip()[:120])}</div>')
    if (vendedor_nome or "").strip():
        linhas.append(_truncar(f"Vendedor: {vendedor_nome.strip()}", L))
        html_parts.append(f'<div>Vendedor: {html_lib.escape(vendedor_nome.strip()[:120])}</div>')

    linhas.append(_linha_separadora(L))
    html_parts.append(_hr_cupom())

    for item in itens:
        nome = (item.get("nome") or item.get("produto_nome") or item.get("descricao_produto") or "Item").strip()
        cod = (item.get("codigo") or item.get("codigo_produto") or "").strip()
        if cod:
            nome = f"{cod} {nome}".strip()
        qtd = item.get("quantidade", 0)
        v_unit = item.get("valor_unitario", item.get("preco_unitario", 0))
        v_total = item.get("valor_total", item.get("total_item", 0))
        linhas.append(_truncar(nome, L - 14))
        linhas.append(f"  {float(qtd):.2f} x {_fmt_moeda(v_unit)} = R$ {_fmt_moeda(v_total)}")
        html_parts.append(f'<div>{html_lib.escape(nome[:80])}</div>')
        html_parts.append(
            f'<div style="margin-left:12px;">{float(qtd):.2f} x R$ {_fmt_moeda(v_unit)} = R$ {_fmt_moeda(v_total)}</div>'
        )

    linhas.append(_linha_separadora(L))
    linhas.append(f"Subtotal:    R$ {_fmt_moeda(subtotal)}")
    html_parts.append(_hr_cupom())
    html_parts.append(f'<div>Subtotal: R$ {_fmt_moeda(subtotal)}</div>')
    if float(desconto or 0) > 0:
        linhas.append(f"Desconto:    R$ {_fmt_moeda(desconto)}")
        html_parts.append(f'<div>Desconto: R$ {_fmt_moeda(desconto)}</div>')
    if float(acrescimo or 0) > 0:
        linhas.append(f"Acrescimo:   R$ {_fmt_moeda(acrescimo)}")
        html_parts.append(f'<div>Acrescimo: R$ {_fmt_moeda(acrescimo)}</div>')
    linhas.append(f"TOTAL:       R$ {_fmt_moeda(total)}")
    html_parts.append(f'<div style="font-weight:bold;">TOTAL: R$ {_fmt_moeda(total)}</div>')

    linhas.append(_linha_separadora(L))
    html_parts.append(_hr_cupom())

    if pagamentos:
        linhas.append("Pagamentos:")
        html_parts.append("<div>Pagamentos:</div>")
        for pg in pagamentos:
            forma_lbl = _label_forma_pagamento(pg.get("forma"))
            val = float(pg.get("valor") or 0)
            linhas.append(f"  {forma_lbl}: R$ {_fmt_moeda(val)}")
            html_parts.append(f'<div style="margin-left:12px;">{html_lib.escape(forma_lbl)}: R$ {_fmt_moeda(val)}</div>')
    else:
        forma_lbl = _label_forma_pagamento(tipo_pagamento)
        linhas.append(f"Pagamento:   {forma_lbl}")
        html_parts.append(f"<div>Pagamento: {html_lib.escape(forma_lbl)}</div>")

    linhas.append(f"Valor pago:  R$ {_fmt_moeda(valor_pago)}")
    html_parts.append(f"<div>Valor pago: R$ {_fmt_moeda(valor_pago)}</div>")
    if float(troco or 0) > 0:
        linhas.append(f"Troco:       R$ {_fmt_moeda(troco)}")
        html_parts.append(f"<div>Troco: R$ {_fmt_moeda(troco)}</div>")

    otxt, ohtml = _linhas_observacao(observacoes, L)
    linhas.extend(otxt)
    html_parts.extend(ohtml)

    linhas.append(_linha_separadora(L))
    linhas.append(_centralizar("Documento sem valor fiscal", L))
    linhas.append("")
    html_parts.append(_hr_cupom())
    html_parts.append('<div style="text-align:center;font-size:11px;">Documento sem valor fiscal</div>')
    html_parts.append("</div>")
    return linhas, "\n".join(html_parts)


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
    **kwargs: Any,
) -> tuple[List[str], str]:
    """Alias legado → cupom de caixa."""
    return gerar_cupom_resumo_venda_caixa(
        estabelecimento_nome=estabelecimento_nome,
        numero_venda=numero_venda,
        data_referencia=data_venda,
        subtotal=subtotal,
        desconto=desconto,
        acrescimo=acrescimo,
        total=total,
        tipo_pagamento=tipo_pagamento,
        valor_pago=valor_pago,
        troco=troco,
        itens=itens,
        largura=largura,
        **{k: v for k, v in kwargs.items() if k in (
            "observacoes", "cliente_nome", "vendedor_nome", "pagamentos", "empresa_fiscal", "largura_mm"
        )},
    )


def gerar_cupom_resumo_venda_negocio(*args: Any, **kwargs: Any) -> Tuple[List[str], str]:
    """Alias de compatibilidade."""
    return gerar_cupom_resumo_venda_caixa(*args, **kwargs)


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
    numero_exibicao = compact_doc_ref(numero_pedido, fallback="")
    linhas.append(_centralizar((estabelecimento_nome or "Estabelecimento").strip() or "Estabelecimento", L))
    linhas.append(_centralizar("PEDIDO", L))
    linhas.append(_linha_separadora(L))
    linhas.append(f"Pedido: {numero_exibicao}")
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
        f'<div>Pedido: {html_lib.escape(numero_exibicao)}</div>',
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


# Cabeçalho fixo do cupom de pedido marketplace (não usar Tenant.nome — costuma ser pessoa física/jurídica do assinante).
CUPOM_IBIX_MARKET_TITULO = "PEDIDO IBIX MARKET"
CUPOM_IBIX_MARKET_SITE = "www.ibix.com.br"


def _linhas_wrap_cupom(texto: str, largura: int) -> List[str]:
    s = " ".join((texto or "").split())
    if not s:
        return []
    out: List[str] = []
    i = 0
    while i < len(s):
        out.append(s[i : i + largura])
        i += largura
    return out


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
    loja_endereco_resumo: Optional[str] = None,
    loja_documento: Optional[str] = None,
) -> Tuple[List[str], str]:
    """
    Cupom não fiscal de pedido marketplace (gestão loja).
    itens: nome, quantidade, valor_unitario (preco_unitario), valor_total (preco_total).
    """
    linhas: List[str] = []
    L = largura
    nome_loja_linha = (loja_exibicao or "Loja").strip() or "Loja"
    linhas.append(_centralizar(CUPOM_IBIX_MARKET_TITULO, L))
    linhas.append(_centralizar(CUPOM_IBIX_MARKET_SITE, L))
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
    linhas.append(_centralizar("LOJA VENDEDORA", L))
    linhas.append(_truncar(f"Loja: {nome_loja_linha}", L))
    for ln in _linhas_wrap_cupom((loja_endereco_resumo or "").strip(), L):
        linhas.append(ln)
    doc_rod = (loja_documento or "").strip()
    if doc_rod:
        for ln in _linhas_wrap_cupom(doc_rod, L):
            linhas.append(ln)
    linhas.append(_linha_separadora(L))
    linhas.append(_centralizar("Documento sem valor fiscal", L))
    linhas.append("")

    _, dh_html = _data_hora_cupom(data_referencia)
    html_parts: List[str] = [
        '<div class="cupom-impressao" style="font-family: monospace; font-size: 12px; max-width: 280px; margin: 0 auto; padding: 12px;">',
        f'<div style="text-align: center; font-weight: bold; font-size: 13px;">{html_lib.escape(CUPOM_IBIX_MARKET_TITULO)}</div>',
        f'<div style="text-align: center; font-size: 11px;">{html_lib.escape(CUPOM_IBIX_MARKET_SITE)}</div>',
        '<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">',
        f'<div>Pedido: {html_lib.escape(numero_exibicao)}</div>',
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
    html_parts.append('<div style="text-align: center; font-weight: 600; font-size: 11px;">LOJA VENDEDORA</div>')
    html_parts.append(
        f'<div style="font-size: 11px;">Loja: {html_lib.escape(nome_loja_linha)}</div>'
    )
    addr_h = (loja_endereco_resumo or "").strip()
    if addr_h:
        html_parts.append(
            f'<div style="font-size: 11px; white-space: pre-wrap;">{html_lib.escape(addr_h[:500])}</div>'
        )
    doc_h = (loja_documento or "").strip()
    if doc_h:
        html_parts.append(f'<div style="font-size: 11px;">{html_lib.escape(doc_h[:80])}</div>')
    html_parts.append('<hr style="border: none; border-top: 1px dashed #333; margin: 8px 0;">')
    html_parts.append('<div style="text-align: center; font-size: 11px;">Documento sem valor fiscal</div>')
    html_parts.append("</div>")
    return linhas, "\n".join(html_parts)
