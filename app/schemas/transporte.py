# PDV Ibix - Schemas Transporte
"""Schemas do módulo Transporte (ex-frete): configuração de transporte da loja,
regras públicas de frete consumidas pela vitrine.

Atores cobertos:
- Loja (CA) — define modo (Retirada | Ambos) e, em Ambos, submodo (própria grátis | própria
  valor | plataforma) via PATCH /api/v1/transporte/loja/{id}.
- Consumidor (vitrine) — consome GET /api/v1/transporte/loja/{id}/regras?cidade=&uf=.
- Superadmin — pode alterar transporte de qualquer loja; gerencia logística local em outros
  módulos (entregadores, repasses).

Evoluções futuras (manter neste módulo): prazos de entrega, SLAs por região, custo do
entregador por categoria, regras de cobertura avançadas.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# Modos expostos ao CA na UI. Tradução para formato_frete (banco) fica em config_service.
TransporteModo = Literal["retirada", "ambos"]
TransporteSubmodo = Literal["propria_gratis", "propria_valor", "plataforma"]

# Formato_frete persistido em lojas_marketplace (CHECK constraint definida na migração
# ft01_frete_transp). Mantido aqui para tipagem; não alterar valores sem nova migração.
FormatoFreteBanco = Literal["sem_frete", "gratis", "taxa_fixa", "plataforma"]


class TransporteConfigResponse(BaseModel):
    """Configuração de transporte da loja (visão CA/Superadmin)."""

    loja_id: int
    cliente_id: int
    modo: TransporteModo
    submodo: Optional[TransporteSubmodo] = None
    taxa_entrega_fixa: Optional[Decimal] = None
    entrega_gratis_apos: Optional[Decimal] = None
    raio_entrega_km: Optional[int] = None
    # Reflexo do banco (debug / auditoria); UI deve usar modo/submodo.
    formato_frete: FormatoFreteBanco
    tipo_entrega: str

    model_config = {"from_attributes": True}


class TransporteConfigUpdate(BaseModel):
    """Body do PATCH /api/v1/transporte/loja/{id}.

    Valida combinações: em modo=retirada, nenhum valor de taxa é aceito; em modo=ambos
    o submodo é obrigatório; em submodo=propria_valor, taxa_entrega_fixa é obrigatória
    (mas pode ser zero, equivalente a grátis).
    """

    modo: TransporteModo
    submodo: Optional[TransporteSubmodo] = None
    taxa_entrega_fixa: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Aplicável quando submodo=propria_valor; ≥ 0.",
    )
    entrega_gratis_apos: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Opcional em submodo=propria_valor; pedidos acima deste valor têm frete zerado.",
    )
    raio_entrega_km: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _coerencia(self) -> "TransporteConfigUpdate":
        if self.modo == "retirada":
            if self.submodo is not None:
                raise ValueError("submodo não se aplica quando modo=retirada")
            if self.taxa_entrega_fixa is not None or self.entrega_gratis_apos is not None:
                raise ValueError("valores de frete não se aplicam em modo=retirada")
            return self
        if self.submodo is None:
            raise ValueError("submodo obrigatório quando modo=ambos")
        if self.submodo == "propria_gratis":
            if self.taxa_entrega_fixa not in (None, Decimal(0)):
                raise ValueError("submodo=propria_gratis não aceita taxa_entrega_fixa > 0")
        elif self.submodo == "propria_valor":
            if self.taxa_entrega_fixa is None:
                raise ValueError("submodo=propria_valor exige taxa_entrega_fixa (≥ 0)")
        return self


class TransporteRegrasPublicResponse(BaseModel):
    """Resposta do GET público de regras: usado pelo carrinho/checkout da vitrine.

    Mantém o mesmo contrato do legado GET /api/v1/loja/{id}/frete para compatibilidade
    com fetches existentes; campos opcionais aparecem apenas quando cidade/UF são
    informados.
    """

    formato_frete: FormatoFreteBanco
    tipo_entrega: str
    taxa_entrega_fixa: Optional[Decimal] = None
    entrega_gratis_apos: Optional[Decimal] = None
    raio_entrega_km: Optional[int] = None
    entrega_disponivel: Optional[bool] = None
    taxa_entrega_cidade: Optional[Decimal] = None
    prazo_dias: Optional[int] = None
    mensagem: Optional[str] = None
    # Cobertura geográfica definida pela plataforma (Superadmin). Quando há cidades cadastradas,
    # entrega ao domicílio só vale em localidades listadas (`GET …/transporte/regioes-cobertura`).
    cobertura_plataforma_ativa: bool = False
    cidade_autorizada_plataforma: Optional[bool] = None
