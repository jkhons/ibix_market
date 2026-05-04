# PDV Ibix — Resolução e cálculo de taxas marketplace
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Literal, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.marketplace_taxa_regra import MarketplaceTaxaRegra
from app.schemas.marketplace_taxa import (
    GatewayItem,
    MarketplaceTaxaPayload,
    MarketplaceTaxaPreviewResponse,
    payload_from_db_str,
)

if TYPE_CHECKING:
    pass


def _q2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def preco_referencia_anuncio(preco_original: Decimal, preco_promocional: Optional[Decimal]) -> Decimal:
    if preco_promocional is not None and preco_promocional > 0:
        return preco_promocional
    return preco_original


def custo_plataforma_por_preco(payload: MarketplaceTaxaPayload, preco: Decimal) -> Decimal:
    if not payload.faixas_plataforma:
        raise ValueError(
            "Nenhuma faixa de taxa da plataforma configurada para esta regra. Configure faixas em Admin Billing."
        )
    for faixa in sorted(payload.faixas_plataforma, key=lambda f: f.preco_min):
        if preco < faixa.preco_min:
            continue
        if faixa.preco_max is not None and preco > faixa.preco_max:
            continue
        if faixa.modo == "fixo":
            return _q2(faixa.valor)
        return _q2(preco * faixa.valor / Decimal("100"))
    raise ValueError(
        "O preço informado não se encaixa em nenhuma faixa configurada. Ajuste as faixas em Admin Billing ou o preço do produto."
    )


def gateway_aplicar(item: GatewayItem, preco: Decimal) -> Decimal:
    if item.modo == "fixo":
        return _q2(item.valor)
    return _q2(preco * item.valor / Decimal("100"))


def montar_preview(payload: MarketplaceTaxaPayload, preco: Decimal) -> MarketplaceTaxaPreviewResponse:
    return MarketplaceTaxaPreviewResponse(
        preco_referencia=preco,
        custo_plataforma_estimado=custo_plataforma_por_preco(payload, preco),
        gateway_pix_valor_estimado=gateway_aplicar(payload.gateway_pix, preco),
        gateway_credito_valor_estimado=gateway_aplicar(payload.gateway_credito, preco),
        gateway_debito_valor_estimado=gateway_aplicar(payload.gateway_debito, preco),
    )


def resolver_regra_e_payload(
    db: Session, tenant_id: int
) -> Tuple[MarketplaceTaxaRegra, Literal["tenant", "geral"], MarketplaceTaxaPayload]:
    row_t = (
        db.query(MarketplaceTaxaRegra)
        .filter(
            MarketplaceTaxaRegra.escopo == "tenant",
            MarketplaceTaxaRegra.tenant_id == tenant_id,
            MarketplaceTaxaRegra.ativo.is_(True),
        )
        .first()
    )
    if row_t:
        return row_t, "tenant", payload_from_db_str(row_t.payload)

    row_g = (
        db.query(MarketplaceTaxaRegra)
        .filter(
            MarketplaceTaxaRegra.escopo == "geral",
            MarketplaceTaxaRegra.ativo.is_(True),
        )
        .first()
    )
    if not row_g:
        raise ValueError(
            "Nenhuma regra de taxas marketplace ativa (Geral). O Super Administrador deve cadastrar uma regra Geral em Admin Billing > Preço > Taxas marketplace."
        )
    return row_g, "geral", payload_from_db_str(row_g.payload)


def validar_unica_geral_ativa(
    db: Session, escopo: str, ativo: bool, exclude_id: Optional[int] = None
) -> None:
    if not ativo or escopo != "geral":
        return
    q = db.query(MarketplaceTaxaRegra).filter(
        MarketplaceTaxaRegra.escopo == "geral",
        MarketplaceTaxaRegra.ativo.is_(True),
    )
    if exclude_id is not None:
        q = q.filter(MarketplaceTaxaRegra.id != exclude_id)
    if q.first() is not None:
        raise ValueError("Já existe uma regra Geral ativa. Desative a outra antes de ativar esta.")


def validar_unico_tenant_ativo(
    db: Session, escopo: str, tenant_id: Optional[int], ativo: bool, exclude_id: Optional[int] = None
) -> None:
    if not ativo or escopo != "tenant" or tenant_id is None:
        return
    q = db.query(MarketplaceTaxaRegra).filter(
        MarketplaceTaxaRegra.escopo == "tenant",
        MarketplaceTaxaRegra.tenant_id == tenant_id,
        MarketplaceTaxaRegra.ativo.is_(True),
    )
    if exclude_id is not None:
        q = q.filter(MarketplaceTaxaRegra.id != exclude_id)
    if q.first() is not None:
        raise ValueError(
            f"Já existe regra ativa para o tenant {tenant_id}. Desative a outra antes de ativar esta."
        )
