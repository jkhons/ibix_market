"""Testes do motor de templates de impressão (Orçamento · OS)."""
from decimal import Decimal
from unittest.mock import MagicMock

from app.services.documento_impressao_service import (
    contexto_mock,
    montar_contexto_ordem_servico,
    renderizar_html,
)


def test_renderizar_html_interpolacao_jinja():
    out = renderizar_html(
        "<h1>{{ codigo }}</h1><p>Total: {{ total }}</p>",
        {"codigo": "OS-0001", "total": "99,90"},
        css_extra="body{font-family:sans-serif}",
    )
    assert "OS-0001" in out
    assert "99,90" in out
    assert "font-family:sans-serif" in out
    assert out.startswith("<!DOCTYPE html>")


def test_contexto_mock_orcamento():
    ctx = contexto_mock("orcamento")
    assert ctx["numero_orcamento"] == "ORC-0001"
    assert ctx["itens"][0]["descricao_produto"] == "Item"
    assert ctx["brand_nome"] == "Marca"


def test_contexto_mock_ordem_servico():
    ctx = contexto_mock("ordem_servico")
    assert ctx["codigo"] == "OS-0001"
    assert ctx["itens"][0]["descricao"] == "Serviço"


def test_montar_contexto_ordem_servico_soma_itens():
    item1 = MagicMock(
        nome="Peça A",
        quantidade=2,
        valor_unitario=Decimal("10"),
        valor_total=Decimal("20"),
        desconto=Decimal("2"),
    )
    item2 = MagicMock(
        nome="Serviço B",
        quantidade=1,
        valor_unitario=Decimal("80"),
        valor_total=Decimal("80"),
        desconto=Decimal("0"),
    )
    ordem = MagicMock(
        codigo="OS-99",
        status="concluida",
        cliente=MagicMock(nome="Cliente Teste"),
        tipo_rel=MagicMock(nome="Manutenção"),
        data_abertura=None,
        observacoes="Obs",
        itens=[item1, item2],
    )
    ctx = montar_contexto_ordem_servico(ordem, brand=MagicMock(nome_exibicao="Marca X", logo_url="/logo.png"))
    assert ctx["cliente_nome"] == "Cliente Teste"
    assert ctx["tipo_nome"] == "Manutenção"
    assert ctx["subtotal"] == "100,00"
    assert ctx["desconto"] == "2,00"
    assert ctx["total"] == "100,00"
    assert ctx["brand_nome"] == "Marca X"
    assert len(ctx["itens"]) == 2
