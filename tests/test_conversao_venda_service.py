"""Testes do rastreio de origem comercial (Orçamento · OS · Venda)."""
from datetime import datetime
from unittest.mock import MagicMock

from app.services.conversao_venda_service import (
    OrigemDocumento,
    montar_origem_cadeia_resposta,
    registrar_origem_manual,
    registrar_origem_orcamento,
    registrar_origem_ordem_servico,
    registrar_origem_venda,
)


def _mock_db_usuario_tenant(tenant_id=7):
    db = MagicMock()
    usuario = MagicMock(tenant_id=tenant_id)

    def query_side(model):
        q = MagicMock()
        if getattr(model, "__name__", "") == "Usuario":
            q.filter.return_value.first.return_value = usuario
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query_side
    return db, usuario


def test_montar_origem_cadeia_com_linhas_venda_origens():
    vo_raiz = MagicMock(
        tipo_origem="orcamento",
        documento_ref="ORC-26-1",
        documento_id=1,
        papel="raiz",
        created_at=datetime(2026, 6, 18, 10, 0),
    )
    vo_imediata = MagicMock(
        tipo_origem="ordem_servico",
        documento_ref="OS-26-1",
        documento_id=2,
        papel="imediata",
        created_at=datetime(2026, 6, 18, 11, 0),
    )
    cadeia = montar_origem_cadeia_resposta(
        99,
        {"numero_venda": "V-26-99", "created_at": datetime(2026, 6, 18, 12, 0)},
        [vo_raiz, vo_imediata],
    )
    assert len(cadeia) == 3
    assert cadeia[0]["tipo"] == "orcamento" and cadeia[0]["papel"] == "raiz"
    assert cadeia[1]["tipo"] == "ordem_servico"
    assert cadeia[2]["tipo"] == "venda" and cadeia[2]["papel"] == "destino"
    assert cadeia[2]["documento_id"] == 99


def test_montar_origem_cadeia_fallback_fk_legacy():
    cadeia = montar_origem_cadeia_resposta(
        10,
        {
            "numero_orcamento": "ORC-26-2",
            "orcamento_id": 5,
            "ordem_servico_codigo": "OS-26-9",
            "ordem_servico_id": 9,
            "numero_venda": "V-26-10",
            "created_at": None,
        },
        [],
    )
    assert [n["tipo"] for n in cadeia] == ["orcamento", "ordem_servico", "venda"]


def test_registrar_origem_manual_grava_linha():
    db, _ = _mock_db_usuario_tenant()
    venda = MagicMock(id=1, vendedor_id=5)
    registrar_origem_manual(db, venda, 5)
    assert db.add.call_count == 1
    row = db.add.call_args[0][0]
    assert row.tipo_origem == "manual"
    assert row.papel == "imediata"


def test_registrar_origem_orcamento_grava_linha_orcamento():
    db, _ = _mock_db_usuario_tenant()
    venda = MagicMock(id=2, vendedor_id=3)
    orcamento = MagicMock(id=11, numero_orcamento="ORC-26-11")
    registrar_origem_orcamento(db, venda, orcamento, 3)
    assert db.add.call_count == 1
    row = db.add.call_args[0][0]
    assert row.tipo_origem == "orcamento" and row.papel == "imediata"


def test_registrar_origem_os_com_orcamento_raiz():
    db, _ = _mock_db_usuario_tenant()
    venda = MagicMock(id=3, vendedor_id=8)
    ordem = MagicMock(id=20, codigo="OS-26-20")
    orc = MagicMock(id=4, numero_orcamento="ORC-26-4")
    registrar_origem_ordem_servico(db, venda, ordem, 8, orcamento_raiz=orc)
    assert db.add.call_count == 2
    tipos = {db.add.call_args_list[i][0][0].tipo_origem for i in range(2)}
    assert tipos == {"ordem_servico", "orcamento"}


def test_registrar_origem_venda_idempotente():
    db = MagicMock()
    usuario = MagicMock(tenant_id=1)
    existente = MagicMock()

    call_count = {"n": 0}

    def query_side(model):
        q = MagicMock()
        if getattr(model, "__name__", "") == "Usuario":
            q.filter.return_value.first.return_value = usuario
        else:
            if call_count["n"] == 0:
                q.filter.return_value.first.return_value = existente
            else:
                q.filter.return_value.first.return_value = None
            call_count["n"] += 1
        return q

    db.query.side_effect = query_side
    venda = MagicMock(id=4, vendedor_id=1)
    origem = OrigemDocumento(tipo="orcamento", documento_id=1, documento_ref="ORC-1")
    registrar_origem_venda(db, venda=venda, usuario_id=1, imediata=origem, raiz=origem)
    db.add.assert_not_called()


def test_calcular_total_orcamento_desconto_acrescimo():
    """Espelha a fórmula de converter_orcamento_em_venda_pendente (subtotal - desconto + acrescimo)."""
    from decimal import Decimal

    class Item:
        def __init__(self, q, p, d):
            self.quantidade = q
            self.preco_unitario = p
            self.desconto_valor = d

    itens = [Item(2, 100, 10), Item(1, 50, 0)]
    acrescimo_val = 5
    subtotal = sum(Decimal(str(i.quantidade)) * Decimal(str(i.preco_unitario)) for i in itens)
    desconto = sum(Decimal(str(i.desconto_valor or 0)) for i in itens)
    acrescimo = Decimal(str(acrescimo_val))
    total = subtotal - desconto + acrescimo
    assert subtotal == Decimal("250")
    assert desconto == Decimal("10")
    assert total == Decimal("245")
