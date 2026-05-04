# PDV Ibix — testes unitários taxas marketplace (sem DB)
from decimal import Decimal

import pytest

from app.schemas.marketplace_taxa import FaixaPlataformaItem, GatewayItem, MarketplaceTaxaPayload
from app.services.marketplace_taxa_service import custo_plataforma_por_preco, gateway_aplicar


def _payload_simples():
    return MarketplaceTaxaPayload(
        faixas_plataforma=[
            FaixaPlataformaItem(preco_min=Decimal("0"), preco_max=Decimal("100"), modo="percent", valor=Decimal("10")),
            FaixaPlataformaItem(preco_min=Decimal("100"), preco_max=None, modo="fixo", valor=Decimal("5")),
        ],
        gateway_pix=GatewayItem(modo="percent", valor=Decimal("1")),
        gateway_credito=GatewayItem(modo="percent", valor=Decimal("3")),
        gateway_debito=GatewayItem(modo="fixo", valor=Decimal("2")),
    )


def test_faixa_percent():
    p = _payload_simples()
    assert custo_plataforma_por_preco(p, Decimal("50")) == Decimal("5.00")


def test_faixa_fixo_sem_teto():
    p = _payload_simples()
    assert custo_plataforma_por_preco(p, Decimal("150")) == Decimal("5.00")


def test_gateway_credito_percent():
    p = _payload_simples()
    assert gateway_aplicar(p.gateway_credito, Decimal("100")) == Decimal("3.00")


def test_fora_faixa_erro():
    p = MarketplaceTaxaPayload(
        faixas_plataforma=[
            FaixaPlataformaItem(preco_min=Decimal("50"), preco_max=Decimal("60"), modo="fixo", valor=Decimal("1")),
        ],
        gateway_pix=GatewayItem(modo="percent", valor=Decimal("1")),
        gateway_credito=GatewayItem(modo="percent", valor=Decimal("3")),
        gateway_debito=GatewayItem(modo="fixo", valor=Decimal("2")),
    )
    with pytest.raises(ValueError):
        custo_plataforma_por_preco(p, Decimal("10"))
