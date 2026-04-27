# PDV Ibix - Cálculo de frete no checkout marketplace (reutilizável)
from decimal import Decimal
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models import AnuncioPlataforma, LojaAreaEntrega, LojaMarketplace


def resolver_regra_frete_anuncio(
    anuncio: AnuncioPlataforma, loja: LojaMarketplace
) -> tuple[str, str, Optional[Decimal], Optional[Decimal]]:
    if getattr(anuncio, "frete_sobrescrever_loja", False):
        formato = getattr(anuncio, "formato_frete_produto", None)
        if not formato:
            raise HTTPException(
                status_code=400,
                detail=f"Anúncio {anuncio.id} com frete inválido: formato_frete_produto ausente",
            )
        return (
            formato,
            "produto",
            getattr(anuncio, "taxa_entrega_fixa_produto", None),
            getattr(anuncio, "entrega_gratis_apos_produto", None),
        )
    return (
        (getattr(loja, "formato_frete", None) or "sem_frete"),
        "loja",
        getattr(loja, "taxa_entrega_fixa", None),
        getattr(loja, "entrega_gratis_apos", None),
    )


def calcular_taxa_item_frete(
    db: Session,
    loja: LojaMarketplace,
    anuncio: AnuncioPlataforma,
    subtotal_item: Decimal,
    tipo_entrega: str,
    endereco_cidade: Optional[str],
    endereco_uf: Optional[str],
) -> Tuple[Decimal, str, str]:
    formato, origem_regra, taxa_fixa, gratis_apos = resolver_regra_frete_anuncio(anuncio, loja)
    if tipo_entrega == "retirada":
        return Decimal("0"), formato, origem_regra
    if formato == "sem_frete":
        raise HTTPException(status_code=400, detail=f"Anúncio {anuncio.id} permite apenas retirada")
    if formato == "gratis":
        return Decimal("0"), formato, origem_regra
    if formato not in {"taxa_fixa", "plataforma"}:
        raise HTTPException(status_code=400, detail=f"Anúncio {anuncio.id} com formato de frete inválido")
    if taxa_fixa is None:
        raise HTTPException(status_code=400, detail=f"Anúncio {anuncio.id} requer taxa de frete configurada")

    if endereco_cidade and endereco_uf:
        area = (
            db.query(LojaAreaEntrega)
            .filter(
                LojaAreaEntrega.loja_id == loja.id,
                sa_func.lower(LojaAreaEntrega.cidade) == endereco_cidade.strip().lower(),
                sa_func.upper(LojaAreaEntrega.uf) == endereco_uf.strip().upper(),
                LojaAreaEntrega.ativo == True,
            )
            .first()
        )
        has_any_area = (
            db.query(LojaAreaEntrega)
            .filter(
                LojaAreaEntrega.loja_id == loja.id,
                LojaAreaEntrega.ativo == True,
            )
            .first()
            if not area
            else True
        )
        if area:
            if gratis_apos and subtotal_item >= gratis_apos:
                return Decimal("0"), formato, origem_regra
            return Decimal(str(area.taxa_entrega)), formato, origem_regra
        if has_any_area:
            raise HTTPException(
                status_code=400,
                detail=f"Entrega indisponível para o anúncio {anuncio.id} nesta localidade",
            )
    if gratis_apos and subtotal_item >= gratis_apos:
        return Decimal("0"), formato, origem_regra
    return Decimal(str(taxa_fixa)), formato, origem_regra
