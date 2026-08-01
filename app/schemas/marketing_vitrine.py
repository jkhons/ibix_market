# PDV Ibix — Schemas Marketing Vitrine
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.schemas.marketplace import AnuncioVitrineResponse

TipoBloco = Literal["destaque", "oferta_semana", "destaque_agora"]
TipoCard = Literal["livre", "anuncio", "cabecalho_ofertas"]


DestaqueLayout = Literal["carrossel", "grade"]


class MarketingVitrineConfigResponse(BaseModel):
    id: int
    mostrar_todos_produtos: bool
    ativo: bool
    mostrar_hero_carrossel: bool = True
    mostrar_secao_em_alta: bool = True
    mostrar_secao_lojas_destaque: bool = True
    titulo_faixa_destaques: Optional[str] = None
    destaque_layout: DestaqueLayout = "carrossel"
    destaque_mostrar_setas: bool = True
    destaque_scroll_snap: bool = True
    destaque_embaralhar: bool = False
    titulo_em_alta: Optional[str] = None
    subtitulo_em_alta: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class MarketingVitrineConfigUpdate(BaseModel):
    mostrar_todos_produtos: Optional[bool] = None
    ativo: Optional[bool] = None
    mostrar_hero_carrossel: Optional[bool] = None
    mostrar_secao_em_alta: Optional[bool] = None
    mostrar_secao_lojas_destaque: Optional[bool] = None
    titulo_faixa_destaques: Optional[str] = Field(None, max_length=200)
    destaque_layout: Optional[DestaqueLayout] = None
    destaque_mostrar_setas: Optional[bool] = None
    destaque_scroll_snap: Optional[bool] = None
    destaque_embaralhar: Optional[bool] = None
    titulo_em_alta: Optional[str] = Field(None, max_length=200)
    subtitulo_em_alta: Optional[str] = None


def _norm_cliente_ids(v: Optional[List[int]]) -> Optional[List[int]]:
    if not v:
        return None
    out: List[int] = []
    seen = set()
    for x in v:
        if x is None:
            continue
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if i < 1 or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out or None


class MarketingVitrineCardBase(BaseModel):
    tipo_bloco: TipoBloco
    tipo_card: TipoCard
    titulo: Optional[str] = Field(None, max_length=200)
    descricao: Optional[str] = None
    imagem_url: Optional[str] = None
    link_url: Optional[str] = None
    anuncio_id: Optional[int] = None
    anuncio_ids: Optional[List[int]] = None
    limite_exibicao: Optional[int] = Field(None, ge=1, le=8)
    # Apenas cabecalho_ofertas: clientes.id (tenant / CA); vazio = todas as lojas.
    cliente_ids: Optional[List[int]] = None
    embaralhar_produtos: Optional[bool] = None
    somente_com_desconto: Optional[bool] = None
    ordem: int = Field(100, ge=0)
    ativo: bool = True
    inicio_em: Optional[datetime] = None
    fim_em: Optional[datetime] = None


class MarketingVitrineCardCreate(MarketingVitrineCardBase):
    @model_validator(mode="after")
    def _regras_v1(self):
        if self.inicio_em and self.fim_em and self.inicio_em > self.fim_em:
            raise ValueError("inicio_em deve ser anterior ou igual a fim_em")
        if self.tipo_card == "livre":
            if not (self.titulo and self.titulo.strip()):
                raise ValueError("titulo é obrigatório para tipo_card=livre")
            if not (self.imagem_url and self.imagem_url.strip()):
                raise ValueError("imagem_url é obrigatória para tipo_card=livre")
            if not (self.link_url and self.link_url.strip()):
                raise ValueError("link_url é obrigatória para tipo_card=livre")
            if self.anuncio_id is not None:
                raise ValueError("anuncio_id deve ser nulo para tipo_card=livre")
            if self.limite_exibicao is not None:
                raise ValueError("limite_exibicao não se aplica a tipo_card=livre")
            if self.cliente_ids is not None:
                raise ValueError("cliente_ids não se aplica a tipo_card=livre")
            if self.embaralhar_produtos is not None:
                raise ValueError("embaralhar_produtos não se aplica a tipo_card=livre")
            if self.somente_com_desconto is not None:
                raise ValueError("somente_com_desconto não se aplica a tipo_card=livre")
        elif self.tipo_card == "anuncio":
            ids = _norm_cliente_ids(self.anuncio_ids)
            aid = self.anuncio_id if (self.anuncio_id is not None and self.anuncio_id > 0) else None
            if not aid and not ids:
                raise ValueError("anuncio_id ou anuncio_ids é obrigatório para tipo_card=anuncio")
            if aid and ids and aid not in ids:
                ids = [aid] + ids
            if self.titulo and self.titulo.strip():
                raise ValueError("titulo não deve ser enviado para tipo_card=anuncio na V1")
            if self.imagem_url and str(self.imagem_url).strip():
                raise ValueError("imagem_url não deve ser enviada para tipo_card=anuncio na V1")
            if self.link_url and str(self.link_url).strip():
                raise ValueError("link_url não deve ser enviada para tipo_card=anuncio na V1")
            if self.limite_exibicao is not None:
                raise ValueError("limite_exibicao não se aplica a tipo_card=anuncio")
            if self.cliente_ids is not None:
                raise ValueError("cliente_ids não se aplica a tipo_card=anuncio")
            if self.embaralhar_produtos is not None:
                raise ValueError("embaralhar_produtos não se aplica a tipo_card=anuncio")
            if self.somente_com_desconto is not None:
                raise ValueError("somente_com_desconto não se aplica a tipo_card=anuncio")
            return self.model_copy(update={"anuncio_id": aid or (ids[0] if ids else None), "anuncio_ids": ids})
        elif self.tipo_card == "cabecalho_ofertas":
            if self.tipo_bloco not in ("oferta_semana", "destaque_agora"):
                raise ValueError(
                    "cabecalho_ofertas exige tipo_bloco=oferta_semana ou destaque_agora"
                )
            if self.imagem_url and str(self.imagem_url).strip():
                raise ValueError("imagem_url não se usa em cabecalho_ofertas")
            if self.link_url and str(self.link_url).strip():
                raise ValueError("link_url não se usa em cabecalho_ofertas")
            if self.anuncio_id is not None:
                raise ValueError("anuncio_id não se usa em cabecalho_ofertas")
            if self.anuncio_ids is not None:
                raise ValueError("anuncio_ids não se usa em cabecalho_ofertas")
            lim = self.limite_exibicao if self.limite_exibicao is not None else 8
            if lim < 1 or lim > 8:
                raise ValueError("limite_exibicao deve estar entre 1 e 8")
            cids = _norm_cliente_ids(self.cliente_ids)
            emb = bool(self.embaralhar_produtos) if self.embaralhar_produtos is not None else False
            som = bool(self.somente_com_desconto) if self.somente_com_desconto is not None else True
            return self.model_copy(
                update={
                    "limite_exibicao": lim,
                    "cliente_ids": cids,
                    "embaralhar_produtos": emb,
                    "somente_com_desconto": som,
                }
            )
        else:
            raise ValueError("tipo_card inválido")
        return self


class MarketingVitrineCardUpdate(BaseModel):
    tipo_bloco: Optional[TipoBloco] = None
    tipo_card: Optional[TipoCard] = None
    titulo: Optional[str] = Field(None, max_length=200)
    descricao: Optional[str] = None
    imagem_url: Optional[str] = None
    link_url: Optional[str] = None
    anuncio_id: Optional[int] = None
    anuncio_ids: Optional[List[int]] = None
    limite_exibicao: Optional[int] = Field(None, ge=1, le=8)
    cliente_ids: Optional[List[int]] = None
    embaralhar_produtos: Optional[bool] = None
    somente_com_desconto: Optional[bool] = None
    ordem: Optional[int] = Field(None, ge=0)
    ativo: Optional[bool] = None
    inicio_em: Optional[datetime] = None
    fim_em: Optional[datetime] = None


class MarketingVitrineCardAdminResponse(BaseModel):
    id: int
    tipo_bloco: str
    tipo_card: str
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    imagem_url: Optional[str] = None
    link_url: Optional[str] = None
    anuncio_id: Optional[int] = None
    anuncio_ids: Optional[List[int]] = None
    limite_exibicao: Optional[int] = None
    cliente_ids: Optional[List[int]] = None
    embaralhar_produtos: Optional[bool] = None
    somente_com_desconto: Optional[bool] = None
    ordem: int
    ativo: bool
    inicio_em: Optional[datetime] = None
    fim_em: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class MarketingPublicLivre(BaseModel):
    tipo_card: Literal["livre"] = "livre"
    card_id: int
    titulo: str
    imagem_url: str
    link_url: str
    descricao: Optional[str] = None


class MarketingPublicAnuncio(BaseModel):
    tipo_card: Literal["anuncio"] = "anuncio"
    card_id: int
    anuncio: AnuncioVitrineResponse


MarketingPublicItem = Union[MarketingPublicLivre, MarketingPublicAnuncio]


class MarketingVitrinePublicConfig(BaseModel):
    mostrar_todos_produtos: bool
    titulo_ofertas_semana: Optional[str] = None
    subtitulo_ofertas_semana: Optional[str] = None
    ativo: bool = True
    limite_ofertas_semana: int = Field(8, ge=1, le=8)
    # Fallback dinâmico: filtro por tenants (clientes.id / CA); vazio = todas as lojas.
    ofertas_cliente_ids: Optional[List[int]] = None
    ofertas_embaralhar: bool = False
    ofertas_somente_desconto: bool = True
    # Seção «Oferta em destaque agora» (mesmo padrão de Oferta Relâmpago / cabecalho_ofertas).
    titulo_destaque_agora: Optional[str] = None
    subtitulo_destaque_agora: Optional[str] = None
    limite_destaque_agora: int = Field(8, ge=1, le=8)
    destaque_agora_cliente_ids: Optional[List[int]] = None
    destaque_agora_embaralhar: bool = False
    destaque_agora_somente_desconto: bool = True
    mostrar_hero_carrossel: bool = True
    mostrar_secao_em_alta: bool = True
    mostrar_secao_lojas_destaque: bool = True
    titulo_faixa_destaques: Optional[str] = None
    titulo_em_alta: Optional[str] = None
    subtitulo_em_alta: Optional[str] = None
    destaque_embaralhar: bool = False


class MarketingVitrinePublicPayload(BaseModel):
    config: MarketingVitrinePublicConfig
    destaques: List[Dict[str, Any]]
    ofertas_semana: List[Dict[str, Any]]
    destaque_agora: List[Dict[str, Any]] = []
    generated_at: str  # ISO 8601 (mesmo formato JSON da API pública)
