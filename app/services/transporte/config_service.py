# PDV Ibix - Serviço de configuração de Transporte
"""Tradução entre modos da UI (Retirada / Ambos→submodo) e o `formato_frete` persistido
em `lojas_marketplace` (CHECK definido em ft01_frete_transp).

Fonte única de verdade: qualquer leitura/escrita de configuração de transporte da loja
deve passar por estas funções. Não duplicar a tradução em `marketplace.py` nem em
templates.

Mapeamento canônico:

| modo (UI)   | submodo (UI)     | formato_frete (banco) | taxa_entrega_fixa | entrega_gratis_apos |
|-------------|------------------|-----------------------|--------------------|----------------------|
| retirada    | —                | sem_frete             | NULL               | NULL                 |
| ambos       | propria_gratis   | gratis                | NULL               | NULL                 |
| ambos       | propria_valor    | taxa_fixa             | valor (≥ 0)        | opcional (≥ 0)       |
| ambos       | plataforma       | plataforma            | opcional           | opcional             |

`tipo_entrega` da loja é mantido como campo informativo: "retirada" quando modo=retirada,
"entrega" quando modo=ambos. Não é fonte de regra de cálculo (vide
`marketplace_frete_checkout.py`).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from ...models import LojaMarketplace
from ...schemas.transporte import (
    FormatoFreteBanco,
    TransporteConfigResponse,
    TransporteConfigUpdate,
    TransporteModo,
    TransporteSubmodo,
)


def derivar_modo_submodo(
    formato_frete: Optional[str],
) -> Tuple[TransporteModo, Optional[TransporteSubmodo]]:
    """A partir do `formato_frete` salvo no banco, devolve `modo` e `submodo` para a UI.

    Combinações desconhecidas caem em ("retirada", None) com aviso silencioso para evitar
    fallback escondido nas chamadas; documentadas como modo seguro.
    """
    fmt = (formato_frete or "sem_frete").strip()
    if fmt == "sem_frete":
        return ("retirada", None)
    if fmt == "gratis":
        return ("ambos", "propria_gratis")
    if fmt == "taxa_fixa":
        return ("ambos", "propria_valor")
    if fmt == "plataforma":
        return ("ambos", "plataforma")
    return ("retirada", None)


def aplicar_config_no_modelo(loja: LojaMarketplace, body: TransporteConfigUpdate) -> None:
    """Aplica o body validado nos atributos do modelo `LojaMarketplace`.

    Não comita: caller controla a transação.
    Limpa campos não aplicáveis a cada modo para manter o estado consistente.
    """
    modo: TransporteModo = body.modo
    submodo: Optional[TransporteSubmodo] = body.submodo

    if modo == "retirada":
        loja.formato_frete = "sem_frete"
        loja.tipo_entrega = "retirada"
        loja.taxa_entrega_fixa = None
        loja.entrega_gratis_apos = None
        if body.raio_entrega_km is not None:
            loja.raio_entrega_km = body.raio_entrega_km
        return

    # modo=ambos
    loja.tipo_entrega = "entrega"
    if submodo == "propria_gratis":
        loja.formato_frete = "gratis"
        loja.taxa_entrega_fixa = None
        loja.entrega_gratis_apos = None
    elif submodo == "propria_valor":
        loja.formato_frete = "taxa_fixa"
        loja.taxa_entrega_fixa = body.taxa_entrega_fixa
        loja.entrega_gratis_apos = body.entrega_gratis_apos
    elif submodo == "plataforma":
        loja.formato_frete = "plataforma"
        loja.taxa_entrega_fixa = body.taxa_entrega_fixa
        loja.entrega_gratis_apos = body.entrega_gratis_apos

    if body.raio_entrega_km is not None:
        loja.raio_entrega_km = body.raio_entrega_km


def montar_response(loja: LojaMarketplace) -> TransporteConfigResponse:
    """Constrói o payload de leitura da configuração de transporte da loja."""
    modo, submodo = derivar_modo_submodo(getattr(loja, "formato_frete", None))
    return TransporteConfigResponse(
        loja_id=loja.id,
        cliente_id=loja.cliente_id,
        modo=modo,
        submodo=submodo,
        taxa_entrega_fixa=loja.taxa_entrega_fixa,
        entrega_gratis_apos=loja.entrega_gratis_apos,
        raio_entrega_km=loja.raio_entrega_km,
        formato_frete=(getattr(loja, "formato_frete", None) or "sem_frete"),
        tipo_entrega=loja.tipo_entrega or "retirada",
    )


__all__ = [
    "aplicar_config_no_modelo",
    "derivar_modo_submodo",
    "montar_response",
    "Decimal",  # exposto para tests/uso conveniente
    "FormatoFreteBanco",
]
