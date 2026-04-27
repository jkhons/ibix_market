# PDV Ibix - Geração de PDF para Orçamento e Pedido
"""Gera PDF de orçamento ou pedido para download e anexo em e-mail/WhatsApp.
WeasyPrint é importado sob demanda para não bloquear o startup quando pango/GTK não estão instalados."""
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO


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


def gerar_pdf_orcamento(dados: dict) -> bytes:
    """
    Gera PDF do orçamento a partir de um dicionário com: numero_orcamento, data_validade, status,
    cliente_nome, destinatario_nome, subtotal, desconto, total, observacoes, condicoes_pagamento,
    itens: [ { codigo_produto, descricao_produto, quantidade, preco_unitario, total_item } ].
    """
    itens_html = ""
    for i in dados.get("itens") or []:
        itens_html += f"""
        <tr>
            <td>{i.get('codigo_produto') or ''}</td>
            <td>{i.get('descricao_produto') or ''}</td>
            <td>{i.get('quantidade') or ''}</td>
            <td>R$ {_fmt_dec(i.get('preco_unitario'))}</td>
            <td>R$ {_fmt_dec(i.get('total_item'))}</td>
        </tr>
        """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"/><title>Orçamento {dados.get('numero_orcamento') or ''}</title></head>
    <body style="font-family: sans-serif; padding: 20px;">
        <h1>Orçamento {dados.get('numero_orcamento') or ''}</h1>
        <p>Validade: {_fmt_date(dados.get('data_validade'))} | Status: {dados.get('status') or ''}</p>
        <p>Estabelecimento: {dados.get('cliente_nome') or ''}</p>
        <p>Destinatário: {dados.get('destinatario_nome') or '-'}</p>
        <table style="width:100%; border-collapse: collapse; margin-top: 16px;">
            <thead>
                <tr style="background: #eee;">
                    <th style="border:1px solid #999; padding:6px;">Código</th>
                    <th style="border:1px solid #999; padding:6px;">Descrição</th>
                    <th style="border:1px solid #999; padding:6px;">Qtd</th>
                    <th style="border:1px solid #999; padding:6px;">Preço unit.</th>
                    <th style="border:1px solid #999; padding:6px;">Total</th>
                </tr>
            </thead>
            <tbody>{itens_html}</tbody>
        </table>
        <p style="margin-top: 16px;">Subtotal: R$ {_fmt_dec(dados.get('subtotal'))} | Desconto: R$ {_fmt_dec(dados.get('desconto'))} | Total: R$ {_fmt_dec(dados.get('total'))}</p>
        <p>{dados.get('observacoes') or ''}</p>
        <p>{dados.get('condicoes_pagamento') or ''}</p>
    </body>
    </html>
    """
    return _html_to_pdf(html)


def gerar_pdf_pedido(dados: dict) -> bytes:
    """
    Gera PDF do pedido. dados: numero_pedido, data_pedido, data_prevista_entrega, status,
    cliente_nome, subtotal, total, observacoes, itens: [ { codigo_produto, descricao_produto, quantidade, quantidade_faturada, preco_unitario, total_item } ].
    """
    itens_html = ""
    for i in dados.get("itens") or []:
        itens_html += f"""
        <tr>
            <td>{i.get('codigo_produto') or ''}</td>
            <td>{i.get('descricao_produto') or ''}</td>
            <td>{i.get('quantidade') or ''}</td>
            <td>{i.get('quantidade_faturada') or '0'}</td>
            <td>R$ {_fmt_dec(i.get('preco_unitario'))}</td>
            <td>R$ {_fmt_dec(i.get('total_item'))}</td>
        </tr>
        """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"/><title>Pedido {dados.get('numero_pedido') or ''}</title></head>
    <body style="font-family: sans-serif; padding: 20px;">
        <h1>Pedido {dados.get('numero_pedido') or ''}</h1>
        <p>Data: {_fmt_date(dados.get('data_pedido'))} | Previsão entrega: {_fmt_date(dados.get('data_prevista_entrega'))} | Status: {dados.get('status') or ''}</p>
        <p>Estabelecimento: {dados.get('cliente_nome') or ''}</p>
        <table style="width:100%; border-collapse: collapse; margin-top: 16px;">
            <thead>
                <tr style="background: #eee;">
                    <th style="border:1px solid #999; padding:6px;">Código</th>
                    <th style="border:1px solid #999; padding:6px;">Descrição</th>
                    <th style="border:1px solid #999; padding:6px;">Qtd</th>
                    <th style="border:1px solid #999; padding:6px;">Qtd faturada</th>
                    <th style="border:1px solid #999; padding:6px;">Preço unit.</th>
                    <th style="border:1px solid #999; padding:6px;">Total</th>
                </tr>
            </thead>
            <tbody>{itens_html}</tbody>
        </table>
        <p style="margin-top: 16px;">Subtotal: R$ {_fmt_dec(dados.get('subtotal'))} | Total: R$ {_fmt_dec(dados.get('total'))}</p>
        <p>{dados.get('observacoes') or ''}</p>
    </body>
    </html>
    """
    return _html_to_pdf(html)


def gerar_pdf_danfe(dados: dict) -> bytes:
    """
    Gera PDF do DANFE (Documento Auxiliar da NF-e) para nota emitida.
    dados: numero, serie, data_emissao, chave_acesso, empresa_nome, cliente_nome,
           valor_total, itens: [ { item_numero, descricao, quantidade, valor_unitario, valor_total } ].
    Usado quando a nota foi autorizada mas o provedor não retornou pdf_path (ex.: stub).
    """
    def _esc(s):
        if s is None:
            return ""
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    itens_html = ""
    for i in dados.get("itens") or []:
        itens_html += f"""
        <tr>
            <td style="border:1px solid #999; padding:4px;">{_esc(i.get('item_numero'))}</td>
            <td style="border:1px solid #999; padding:4px;">{_esc(i.get('descricao'))}</td>
            <td style="border:1px solid #999; padding:4px;">{_fmt_dec(i.get('quantidade'))}</td>
            <td style="border:1px solid #999; padding:4px;">R$ {_fmt_dec(i.get('valor_unitario'))}</td>
            <td style="border:1px solid #999; padding:4px;">R$ {_fmt_dec(i.get('valor_total'))}</td>
        </tr>
        """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"/><title>DANFE - NF-e {_esc(dados.get('numero'))}</title></head>
    <body style="font-family: sans-serif; padding: 16px; font-size: 11px;">
        <h2 style="margin:0 0 12px 0;">Documento Auxiliar da Nota Fiscal Eletrônica</h2>
        <p><strong>Nº</strong> {_esc(dados.get('numero'))} | <strong>Série</strong> {_esc(dados.get('serie'))} | <strong>Emissão</strong> {_fmt_date(dados.get('data_emissao'))}</p>
        <p><strong>Chave de acesso:</strong> {_esc(dados.get('chave_acesso') or '-')}</p>
        <p><strong>Emitente:</strong> {_esc(dados.get('empresa_nome'))}</p>
        <p><strong>Destinatário:</strong> {_esc(dados.get('cliente_nome') or 'Consumidor final')}</p>
        <table style="width:100%; border-collapse: collapse; margin-top: 12px;">
            <thead>
                <tr style="background: #eee;">
                    <th style="border:1px solid #999; padding:4px;">Item</th>
                    <th style="border:1px solid #999; padding:4px;">Descrição</th>
                    <th style="border:1px solid #999; padding:4px;">Qtd</th>
                    <th style="border:1px solid #999; padding:4px;">Valor unit.</th>
                    <th style="border:1px solid #999; padding:4px;">Total</th>
                </tr>
            </thead>
            <tbody>{itens_html}</tbody>
        </table>
        <p style="margin-top: 12px;"><strong>Valor total da nota: R$ {_fmt_dec(dados.get('valor_total'))}</strong></p>
    </body>
    </html>
    """
    return _html_to_pdf(html)


def _html_to_pdf(html: str) -> bytes:
    """Converte HTML em PDF usando WeasyPrint. Retorna bytes. Import lazy para não falhar no startup."""
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise RuntimeError("WeasyPrint não instalado; não é possível gerar PDF") from e
    except OSError as e:
        raise RuntimeError(
            "WeasyPrint requer bibliotecas de sistema (pango, etc.). "
            "Instale conforme https://doc.courtbouillon.org/weasyprint/stable/first_steps.html"
        ) from e
    buf = BytesIO()
    doc = HTML(string=html)
    doc.write_pdf(buf)
    return buf.getvalue()
