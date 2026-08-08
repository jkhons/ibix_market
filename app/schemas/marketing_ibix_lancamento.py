# PDV Ibix — Schemas Marketing Ibix Lançamento (Superadmin)
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


StatusCopy = Literal["proposta", "aprovado", "rejeitado"]
StatusProducao = Literal["pendente", "gravado", "pronto"]
StatusPublicacao = Literal["pendente", "ig", "fb", "ambos"]
BlocoLiteral = Literal["A", "B", "C", "D"]
TipoLiteral = Literal["cheio", "leve", "reuso"]
CampanhaStatus = Literal["ativa", "encerrada"]


class MarketingCorteOut(BaseModel):
    corte: int
    tempo: str
    texto_tela: str
    visual: str


class MarketingPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campanha_id: int
    numero: int
    data_prevista: date
    bloco: BlocoLiteral
    tipo: TipoLiteral
    tema: str
    angulo: str
    copy_ref: Optional[str] = None
    duracao: Optional[str] = None
    legenda_reels: Optional[str] = None
    roteiro_notas: Optional[str] = None
    telas_necessarias: Optional[str] = None
    cortes: Optional[List[Any]] = None
    status_copy: StatusCopy
    telas_ok: bool
    status_producao: StatusProducao
    status_publicacao: StatusPublicacao
    publicado_em: Optional[datetime] = None
    chk_texto_curto: bool
    chk_tela_real: bool
    chk_mesmo_ig_fb: bool
    chk_frase_ancora: bool
    chk_entrega_regra: bool
    chk_stories_mesmo_dia: bool
    reuso_origem_numero: Optional[int] = None
    notas: Optional[str] = None
    updated_at: datetime
    updated_by_user_id: Optional[int] = None
    tem_roteiro: bool = False


class MarketingPostPatch(BaseModel):
    status_copy: Optional[StatusCopy] = None
    telas_ok: Optional[bool] = None
    status_producao: Optional[StatusProducao] = None
    status_publicacao: Optional[StatusPublicacao] = None
    chk_texto_curto: Optional[bool] = None
    chk_tela_real: Optional[bool] = None
    chk_mesmo_ig_fb: Optional[bool] = None
    chk_frase_ancora: Optional[bool] = None
    chk_entrega_regra: Optional[bool] = None
    chk_stories_mesmo_dia: Optional[bool] = None
    reuso_origem_numero: Optional[int] = Field(default=None, ge=1, le=28)
    notas: Optional[str] = Field(default=None, max_length=2000)


class MarketingCampanhaPatch(BaseModel):
    proximo_passo: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    status: Optional[CampanhaStatus] = None


class BlocoProgresso(BaseModel):
    bloco: BlocoLiteral
    total: int
    copy_aprovado: int
    publicados_ambos: int


class MarketingCampanhaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    titulo: str
    data_inicio: date
    data_fim: date
    canais: str
    status: CampanhaStatus
    proximo_passo: str
    formato: Optional[str] = None
    tom: Optional[str] = None
    linha_gancho: Optional[str] = None
    frase_ancora: Optional[str] = None
    linha_editorial: Optional[str] = None
    ritmo_resumo: Optional[str] = None
    politica_reuso: Optional[str] = None
    updated_at: datetime
    totais_status_copy: Dict[str, int]
    totais_status_publicacao: Dict[str, int]
    progresso_blocos: List[BlocoProgresso]
    post_hoje: Optional[MarketingPostOut] = None
    proximo_pendente: Optional[MarketingPostOut] = None
    pre_inicio: bool = False
    foco_montagem: List[int] = Field(default_factory=list)
