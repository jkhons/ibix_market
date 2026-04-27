# PDV Ibix - Motor tributário de ICMS para NF-e
"""Resolve CFOP, CST/CSOSN, origem e ICMS por item com base em regras parametrizadas por empresa e contexto."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional, Union

from sqlalchemy.orm import Session

from app.models.regra_fiscal_icms import (
    RegraFiscalIcms,
    TipoDestinatarioFiscalEnum,
    TipoOperacaoFiscalEnum,
)

MOTOR_VERSAO = "1.0"

# Tipo aceito pelas funções do motor (ORM ou cache)
RegraFiscalTipo = Union[RegraFiscalIcms, "RegraFiscalIcmsCache"]


@dataclass
class RegraFiscalIcmsCache:
    """Versão leve para cache Redis. Atributos compatíveis com RegraFiscalIcms (duck typing)."""
    id: int
    empresa_id: int
    crt: Optional[int]
    tipo_operacao: Optional[str]
    tipo_destinatario: Optional[str]
    uf_destinatario: Optional[str]
    ncm_prefix: Optional[str]
    ncm_exato: Optional[str]
    cest: Optional[str]
    cfop_filtro: Optional[str]
    vigencia_inicio: Optional[date]
    vigencia_fim: Optional[date]
    cfop: str
    origem_mercadoria: int
    cst_icms: Optional[str]
    csosn: Optional[str]
    aliquota_icms: Decimal
    modalidade_bc_icms: Optional[str]
    percentual_reducao_bc: Optional[Decimal]
    gera_icms_st: bool
    aliquota_icms_st: Optional[Decimal]
    modalidade_bc_icms_st: Optional[str]
    percentual_mva_st: Optional[Decimal]
    permite_credito_icms: Optional[bool]
    ordem_prioridade: int


class ErroMotorTributario(Exception):
    """Erro bloqueante do motor tributário (nenhuma regra, ambiguidade, incompatibilidade CRT)."""
    pass


@dataclass
class ContextoFiscalItem:
    """Contexto da operação para decisão tributária por item."""
    empresa_id: int
    crt: int
    uf_emitente: str
    uf_destinatario: Optional[str]
    tipo_destinatario: str  # "pf" | "pj"
    tipo_operacao: str  # TipoOperacaoFiscalEnum value
    ncm: str
    cest: Optional[str] = None
    cfop_sugerido: Optional[str] = None


@dataclass
class DecisaoFiscalItem:
    """Resultado da decisão tributária por item."""
    cfop: str
    origem_mercadoria: int
    cst_icms: Optional[str]
    csosn: Optional[str]
    aliquota_icms: Decimal
    modalidade_bc_icms: Optional[str]
    percentual_reducao_bc: Optional[Decimal]
    aliquota_icms_st: Optional[Decimal]
    modalidade_bc_icms_st: Optional[str]
    percentual_mva_st: Optional[Decimal]
    regra_fiscal_id: int
    mensagem_motor: str


def _regra_val(regra: RegraFiscalTipo, attr: str) -> Optional[str]:
    """Extrai valor string de tipo_operacao/tipo_destinatario (ORM enum ou cache str)."""
    v = getattr(regra, attr, None)
    return getattr(v, "value", v) if v is not None else None


def _especificidade_regra(regra: RegraFiscalTipo) -> tuple:
    """Calcula score de especificidade (maior = mais específico)."""
    ncm = 0
    if regra.ncm_exato and str(regra.ncm_exato).strip():
        ncm = 3
    elif regra.ncm_prefix and str(regra.ncm_prefix).strip():
        ncm = 2
    else:
        ncm = 1

    uf = 2 if (regra.uf_destinatario and str(regra.uf_destinatario).strip()) else 1
    td = _regra_val(regra, "tipo_destinatario")
    tipo_dest = 2 if (td and td != TipoDestinatarioFiscalEnum.QUALQUER.value) else 1
    crt = 2 if regra.crt is not None else 1

    return (ncm, uf, tipo_dest, crt)


def _regra_compativel_contexto(regra: RegraFiscalTipo, ctx: ContextoFiscalItem, hoje) -> bool:
    """Verifica se a regra aplica ao contexto."""
    if regra.crt is not None and regra.crt != ctx.crt:
        return False
    top = _regra_val(regra, "tipo_operacao")
    if top and top != TipoOperacaoFiscalEnum.QUALQUER.value:
        if top != ctx.tipo_operacao:
            return False
    td = _regra_val(regra, "tipo_destinatario")
    if td and td != TipoDestinatarioFiscalEnum.QUALQUER.value:
        if td != ctx.tipo_destinatario:
            return False

    if ctx.uf_destinatario is None or not str(ctx.uf_destinatario).strip():
        if regra.uf_destinatario and str(regra.uf_destinatario).strip():
            return False
    else:
        if regra.uf_destinatario and str(regra.uf_destinatario).strip():
            uf_ctx = str(ctx.uf_destinatario).strip().upper()[:2]
            uf_regra = str(regra.uf_destinatario).strip().upper()[:2]
            if uf_ctx != uf_regra:
                return False

    ncm_limpo = str(ctx.ncm or "").replace(".", "").replace(" ", "")[:8]
    if regra.ncm_exato and str(regra.ncm_exato).strip():
        ncm_regra = str(regra.ncm_exato).replace(".", "").strip()[:8]
        if ncm_limpo != ncm_regra:
            return False
    elif regra.ncm_prefix and str(regra.ncm_prefix).strip():
        prefix = str(regra.ncm_prefix).replace(".", "").strip()[:4]
        if not ncm_limpo.startswith(prefix):
            return False

    if regra.cest and str(regra.cest).strip() and ctx.cest:
        if str(ctx.cest).strip() != str(regra.cest).strip():
            return False

    if regra.cfop_filtro and str(regra.cfop_filtro).strip() and ctx.cfop_sugerido:
        cfop_regra = str(regra.cfop_filtro).replace(".", "").strip()[:4]
        cfop_ctx = str(ctx.cfop_sugerido).replace(".", "").strip()[:4]
        if cfop_ctx != cfop_regra:
            return False

    if regra.vigencia_inicio and hoje < regra.vigencia_inicio:
        return False
    if regra.vigencia_fim and hoje > regra.vigencia_fim:
        return False

    return True


def _validar_resultado_regra(regra: RegraFiscalTipo, ctx: ContextoFiscalItem) -> None:
    """Valida compatibilidade do resultado da regra com CRT. Lança ErroMotorTributario se inválido."""
    if regra.cst_icms and str(regra.cst_icms).strip() and regra.csosn and str(regra.csosn).strip():
        raise ErroMotorTributario("Regra fiscal retorna CST e CSOSN simultaneamente (inconsistente).")
    if ctx.crt in (1, 2):
        if regra.cst_icms and str(regra.cst_icms).strip():
            raise ErroMotorTributario(
                f"Regra fiscal ID {regra.id} retorna CST ICMS, mas empresa usa CRT {ctx.crt} (Simples Nacional - deve usar CSOSN)."
            )
    else:
        if regra.csosn and str(regra.csosn).strip():
            raise ErroMotorTributario(
                f"Regra fiscal ID {regra.id} retorna CSOSN, mas empresa usa CRT {ctx.crt} (Regime Normal - deve usar CST)."
            )


def resolver_regra_icms(
    db: Session,
    contexto: ContextoFiscalItem,
    regras_precarregadas: Optional[List[RegraFiscalTipo]] = None,
) -> DecisaoFiscalItem:
    """Resolve a melhor regra fiscal para o item e retorna a decisão. Lança ErroMotorTributario se falhar.

    Quando regras_precarregadas é fornecido (lista de regras já filtradas por empresa e ativo),
    evita query repetida em loop (otimização N+1).
    """
    hoje = date.today()

    if not contexto.ncm or not str(contexto.ncm).strip():
        raise ErroMotorTributario("NCM é obrigatório para resolver regra fiscal.")

    if regras_precarregadas is not None:
        regras = regras_precarregadas
    else:
        regras = (
            db.query(RegraFiscalIcms)
            .filter(
                RegraFiscalIcms.empresa_id == contexto.empresa_id,
                RegraFiscalIcms.ativo == True,
            )
            .order_by(RegraFiscalIcms.ordem_prioridade.asc())
            .all()
        )

    candidatas = [r for r in regras if _regra_compativel_contexto(r, contexto, hoje)]

    if not candidatas:
        raise ErroMotorTributario(
            "Nenhuma regra fiscal ICMS aplicável para esta empresa e operação. Cadastre uma regra em Regras Fiscais."
        )

    def _sort_key(r):
        e = _especificidade_regra(r)
        # ordem_prioridade: menor = maior prioridade; id como desempate final (menor id vence)
        return (-e[0], -e[1], -e[2], -e[3], r.ordem_prioridade, r.id)

    candidatas.sort(key=_sort_key)
    melhor_chave = _sort_key(candidatas[0])
    empatadas = [r for r in candidatas if _sort_key(r) == melhor_chave]

    if len(empatadas) > 1:
        raise ErroMotorTributario(
            f"Múltiplas regras fiscais equivalentes aplicáveis (IDs: {[r.id for r in empatadas]}). "
            "Ajuste ordem_prioridade ou critérios para desempate."
        )

    regra = candidatas[0]
    _validar_resultado_regra(regra, contexto)

    return DecisaoFiscalItem(
        cfop=str(regra.cfop).strip()[:4],
        origem_mercadoria=int(regra.origem_mercadoria) if regra.origem_mercadoria is not None else 0,
        cst_icms=str(regra.cst_icms).strip()[:5] if regra.cst_icms and str(regra.cst_icms).strip() else None,
        csosn=str(regra.csosn).strip()[:5] if regra.csosn and str(regra.csosn).strip() else None,
        aliquota_icms=regra.aliquota_icms if regra.aliquota_icms is not None else Decimal("0"),
        modalidade_bc_icms=str(regra.modalidade_bc_icms).strip() if regra.modalidade_bc_icms else None,
        percentual_reducao_bc=regra.percentual_reducao_bc,
        aliquota_icms_st=regra.aliquota_icms_st,
        modalidade_bc_icms_st=str(regra.modalidade_bc_icms_st).strip() if regra.modalidade_bc_icms_st else None,
        percentual_mva_st=regra.percentual_mva_st,
        regra_fiscal_id=regra.id,
        mensagem_motor=f"Regra {regra.id} aplicada (ordem {regra.ordem_prioridade}).",
    )
