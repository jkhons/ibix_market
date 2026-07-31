# PDV Ibix - Regras públicas de Transporte (consumo vitrine)
"""Resolve as regras públicas de transporte de uma loja para o consumidor (carrinho/checkout):
- Sem cidade/UF: devolve apenas o formato e taxa fixa da loja.
- Com cidade/UF: em **entrega própria** (`gratis` / `taxa_fixa`), o preço exibido cobrado
  vem sempre da loja (grátis ou `taxa_entrega_fixa`); `LojaAreaEntrega` limita **cobertura**
  (se houver linhas) e pode informar só prazo. Em **plataforma** (`plataforma`), há linha por
  cidade com `taxa_entrega` própria.

Esta função substitui o conteúdo antigo de `GET /api/v1/loja/{id}/frete` (loja.py) com
o mesmo contrato; o endpoint legado vira alias.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...models import LojaAreaEntrega, LojaMarketplace
from ...schemas.transporte import TransporteRegrasPublicResponse
from ...services.plataforma_cobertura_service import (
    cidade_uf_na_cobertura_plataforma,
    plataforma_cobertura_ativa,
)


def regras_publicas_loja(
    db: Session,
    loja_id: int,
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
) -> TransporteRegrasPublicResponse:
    """Calcula as regras públicas de transporte da loja para o consumidor.

    - Retorna 404 quando a loja não existe ou não está ativa.
    - Com cidade/UF:
      - **Entrega própria** (`gratis`, `taxa_fixa`): o valor público é o da própria loja
        (grátis ou `taxa_entrega_fixa`). Linhas em `loja_areas_entrega` servem apenas
        para limitar **onde há entrega**, e podem definir só `prazo_dias` quando o CEP casa.
      - **Entrega plataforma** (`plataforma`): com área cobrindo cidade, prevalece
        `taxa_entrega` da área; com áreas mas sem linha nesta cidade → indisponível;
        sem áreas → cai para `taxa_entrega_fixa` da loja.
    """
    loja = (
        db.query(LojaMarketplace)
        .filter(LojaMarketplace.id == loja_id, LojaMarketplace.status == "ativo")
        .first()
    )
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada ou inativa")

    cob_plat = plataforma_cobertura_ativa(db)

    resp = TransporteRegrasPublicResponse(
        formato_frete=(getattr(loja, "formato_frete", None) or "sem_frete"),
        tipo_entrega=loja.tipo_entrega or "retirada",
        taxa_entrega_fixa=loja.taxa_entrega_fixa,
        entrega_gratis_apos=loja.entrega_gratis_apos,
        raio_entrega_km=loja.raio_entrega_km,
        cobertura_plataforma_ativa=cob_plat,
    )

    if not (cidade and uf):
        return resp

    if cob_plat:
        ok_plat = cidade_uf_na_cobertura_plataforma(db, cidade, uf)
        resp.cidade_autorizada_plataforma = ok_plat
        if not ok_plat:
            resp.entrega_disponivel = False
            resp.mensagem = (
                "Esta localidade não está nas regiões atendidas pelo marketplace. Escolha outro "
                "endereço dentro das cidades divulgadas pela plataforma."
            )
            return resp

    area_match = (
        db.query(LojaAreaEntrega)
        .filter(
            LojaAreaEntrega.loja_id == loja_id,
            func.lower(LojaAreaEntrega.cidade) == cidade.strip().lower(),
            func.upper(LojaAreaEntrega.uf) == uf.strip().upper(),
            LojaAreaEntrega.ativo.is_(True),
        )
        .first()
    )

    has_any_area = (
        db.query(LojaAreaEntrega)
        .filter(LojaAreaEntrega.loja_id == loja_id, LojaAreaEntrega.ativo.is_(True))
        .first()
    ) is not None

    fmt = getattr(loja, "formato_frete", None) or "sem_frete"

    if fmt == "gratis":
        if has_any_area and not area_match:
            resp.entrega_disponivel = False
            resp.mensagem = "Não entregamos nessa localidade"
            return resp
        resp.entrega_disponivel = True
        resp.taxa_entrega_cidade = Decimal("0")
        resp.prazo_dias = area_match.prazo_dias if area_match else None
        return resp

    if fmt == "taxa_fixa":
        if has_any_area and not area_match:
            resp.entrega_disponivel = False
            resp.mensagem = "Não entregamos nessa localidade"
            return resp
        resp.entrega_disponivel = True
        resp.taxa_entrega_cidade = (
            Decimal(str(loja.taxa_entrega_fixa)) if loja.taxa_entrega_fixa else Decimal("0")
        )
        resp.prazo_dias = area_match.prazo_dias if area_match else None
        return resp

    # plataforma (ou legado): tarifa da área quando existir linha para a cidade
    if area_match:
        resp.entrega_disponivel = True
        resp.taxa_entrega_cidade = Decimal(str(area_match.taxa_entrega))
        resp.prazo_dias = area_match.prazo_dias
        return resp

    if has_any_area:
        resp.entrega_disponivel = False
        resp.mensagem = "Não entregamos nessa localidade"
        return resp

    resp.entrega_disponivel = True
    resp.taxa_entrega_cidade = (
        Decimal(str(loja.taxa_entrega_fixa)) if loja.taxa_entrega_fixa else Decimal("0")
    )
    resp.prazo_dias = None
    return resp
