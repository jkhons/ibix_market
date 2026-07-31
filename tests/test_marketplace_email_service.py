# PDV Ibix — Testes do builder de e-mail marketplace (comprador)
from unittest.mock import MagicMock

from app.services import marketplace_email_service as mes


def test_substituir():
    assert mes._substituir("Olá {{nome}}", {"nome": "Ana"}) == "Olá Ana"


def test_primeiro_nome():
    assert mes._primeiro_nome("Igor Henrique Oliveira") == "Igor"
    assert mes._primeiro_nome("") == "Cliente"


def test_build_context_comprador_keys(monkeypatch):
    db = MagicMock()

    monkeypatch.setattr(mes, "get_app_url", lambda _db: "https://exemplo.com")

    def fake_cfg(_db, _chave):
        return ""

    monkeypatch.setattr(mes, "_cfg", fake_cfg)
    monkeypatch.setattr(mes, "_cfg_tenant", lambda *_a, **_k: "")
    monkeypatch.setattr(
        mes,
        "_bloco_itens_pedido_html",
        lambda _db, _pid: "<!-- itens test -->",
    )
    monkeypatch.setattr(
        mes,
        "resolve_vitrine_header_logo_url",
        lambda _db, brand=None: "https://exemplo.com/static/img/ibix/cab.png",
    )

    pedido = MagicMock()
    pedido.numero_pedido = "58-999"
    pedido.id = 999
    pedido.total = 38.00
    pedido.comprador_nome = "Maria Silva"
    pedido.tipo_entrega = "retirada"
    pedido.comprador_email = "m@exemplo.com"

    loja = MagicMock()
    loja.nome_fantasia = "Minha Vitrine"
    loja.nome_loja = "Minha Vitrine"
    loja.slug = "minha-vitrine"
    loja.logo_url = None
    loja.cliente_id = 1

    ctx = mes.build_context_comprador(db, pedido, loja)
    assert ctx["nome_vitrine"] == "Minha Vitrine"
    assert ctx["nome_loja"] == "Minha Vitrine"
    assert ctx["nome_plataforma"] == "Ibix"
    assert ctx["numero_pedido"] == "58-999"
    assert ctx["link_vitrine"] == "https://exemplo.com/loja/minha-vitrine"
    assert ctx["link_vitrine_central"] == "https://exemplo.com/loja"
    assert "/static/img/ibix/cab.png" in ctx["bloco_logo_vitrine_header"]
    assert "acompanhar-pedido" in ctx["link_acompanhar_pedido"]
    assert ctx["comprador_primeiro_nome"] == "Maria"
    assert ctx["bloco_itens_pedido"] == "<!-- itens test -->"


def test_bloco_itens_pedido_html_escapes_and_rows():
    db = MagicMock()
    item_a = MagicMock()
    item_a.nome_produto_snapshot = 'Nobreak <alert>'
    item_a.quantidade = 2
    item_a.preco_unitario = 10.5
    item_a.preco_total = 21.0
    item_b = MagicMock()
    item_b.nome_produto_snapshot = "Cab USB-C"
    item_b.quantidade = 1
    item_b.preco_unitario = 39.9
    item_b.preco_total = 39.9
    chain = MagicMock()
    chain.filter.return_value.order_by.return_value.all.return_value = [item_a, item_b]
    db.query.return_value = chain

    html_out = mes._bloco_itens_pedido_html(db, 42)
    db.query.assert_called_once()
    assert "Produtos comprados" in html_out
    assert "Nobreak &lt;alert&gt;" in html_out
    assert "Cab USB-C" in html_out
    assert "Quantidade: 2" in html_out
    assert "R$ 21,00" in html_out or "21,00" in html_out
    assert "39,90" in html_out


def test_label_entrega():
    from app.core.constants import EM_ROTA

    assert "Saiu" in mes._label_entrega(EM_ROTA)
