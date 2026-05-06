# PDV Ibix — Schemas regras de taxa marketplace (Billing / CA)
from __future__ import annotations

import json
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class GatewayItem(BaseModel):
    modo: Literal["fixo", "percent"]
    valor: Decimal = Field(ge=Decimal("0"))

    @model_validator(mode="after")
    def cap_percent(self):
        if self.modo == "percent" and self.valor > Decimal("100"):
            raise ValueError("Percentual não pode ser maior que 100")
        return self


class FaixaPlataformaItem(BaseModel):
    preco_min: Decimal = Field(ge=Decimal("0"))
    preco_max: Optional[Decimal] = None  # None = sem teto (faixa aberta à direita)
    modo: Literal["fixo", "percent"]
    valor: Decimal = Field(ge=Decimal("0"))

    @model_validator(mode="after")
    def ordem_e_percent(self):
        if self.modo == "percent" and self.valor > Decimal("100"):
            raise ValueError("Percentual não pode ser maior que 100")
        if self.preco_max is not None and self.preco_max < self.preco_min:
            raise ValueError("preco_max deve ser >= preco_min")
        return self


class MarketplaceTaxaPayload(BaseModel):
    faixas_plataforma: List[FaixaPlataformaItem] = Field(default_factory=list)
    gateway_pix: GatewayItem
    gateway_credito: GatewayItem
    gateway_debito: GatewayItem

    @model_validator(mode="after")
    def exige_faixa(self):
        if not self.faixas_plataforma:
            raise ValueError("Informe ao menos uma faixa de preço para a taxa da plataforma.")
        return self


def payload_to_json_str(payload: MarketplaceTaxaPayload) -> str:
    doc = {
        "faixas_plataforma": [f.model_dump(mode="json") for f in payload.faixas_plataforma],
        "gateway": {
            "pix": payload.gateway_pix.model_dump(mode="json"),
            "credito": payload.gateway_credito.model_dump(mode="json"),
            "debito": payload.gateway_debito.model_dump(mode="json"),
        },
    }
    return json.dumps(doc, ensure_ascii=False)


def payload_from_db_str(s: str) -> MarketplaceTaxaPayload:
    data = json.loads(s) if s else {}
    gw = data.get("gateway") or {}
    for key in ("pix", "credito", "debito"):
        if key not in gw:
            raise ValueError(f"gateway.{key} obrigatório no payload")
    return MarketplaceTaxaPayload(
        faixas_plataforma=[FaixaPlataformaItem.model_validate(x) for x in (data.get("faixas_plataforma") or [])],
        gateway_pix=GatewayItem.model_validate(gw["pix"]),
        gateway_credito=GatewayItem.model_validate(gw["credito"]),
        gateway_debito=GatewayItem.model_validate(gw["debito"]),
    )


def normalize_payload_dict(data: dict) -> MarketplaceTaxaPayload:
    """Aceita API com objeto gateway aninhado."""
    gw = data.get("gateway")
    if isinstance(gw, dict):
        merged = {
            "faixas_plataforma": data.get("faixas_plataforma") or [],
            "gateway_pix": gw.get("pix"),
            "gateway_credito": gw.get("credito"),
            "gateway_debito": gw.get("debito"),
        }
        return MarketplaceTaxaPayload.model_validate(merged)
    return MarketplaceTaxaPayload.model_validate(data)


# --- Responses API ---
class MarketplaceTaxaPreviewResponse(BaseModel):
    """Calculado para um preço de referência."""

    preco_referencia: Decimal
    custo_plataforma_estimado: Decimal
    gateway_pix_valor_estimado: Decimal
    gateway_credito_valor_estimado: Decimal
    gateway_debito_valor_estimado: Decimal


class MarketplaceTaxasVigentesResponse(BaseModel):
    regra_id: int
    nome_regra: str
    escopo_aplicado: Literal["tenant", "geral"]
    payload: MarketplaceTaxaPayload
    preview: Optional[MarketplaceTaxaPreviewResponse] = None


class MarketplaceTaxaRegraCreateRequest(BaseModel):
    nome: str = Field(..., max_length=200)
    ativo: bool = True
    escopo: Literal["geral", "tenant"]
    tenant_id: Optional[int] = None
    payload: MarketplaceTaxaPayload


class MarketplaceTaxaRegraUpdateRequest(BaseModel):
    nome: Optional[str] = Field(None, max_length=200)
    ativo: Optional[bool] = None
    payload: Optional[MarketplaceTaxaPayload] = None


class MarketplaceTaxaRegraAdminResponse(BaseModel):
    id: int
    nome: str
    ativo: bool
    escopo: Literal["geral", "tenant"]
    tenant_id: Optional[int] = None
    payload: MarketplaceTaxaPayload
