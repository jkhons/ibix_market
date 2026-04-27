# PDV Ibix - Resolvedor de CFOP
"""Define CFOP com base no contexto da operação (não no produto). Usado pelo motor tributário."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TipoMovimentoCFOP(str, Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class DestinoGeograficoCFOP(str, Enum):
    INTERNA = "interna"
    INTERESTADUAL = "interestadual"
    EXTERIOR = "exterior"


class NaturezaOperacaoCFOP(str, Enum):
    VENDA = "venda"
    DEVOLUCAO = "devolucao"
    REMESSA = "remessa"
    RETORNO = "retorno"
    TRANSFERENCIA = "transferencia"
    BONIFICACAO = "bonificacao"
    CONSERTO = "conserto"
    INDUSTRIALIZACAO = "industrializacao"
    SIMPLES_FATURAMENTO = "simples_faturamento"
    VENDA_ORDEM = "venda_ordem"


class OrigemMercadoriaComercial(str, Enum):
    PRODUCAO_PROPRIA = "producao_propria"
    MERCADORIA_TERCEIROS = "mercadoria_terceiros"


class ErroCFOPResolver(Exception):
    """Contexto insuficiente para resolver CFOP."""


@dataclass
class ContextoCFOP:
    """Contexto da operação para decisão de CFOP."""
    tipo_documento: str  # TipoMovimentoCFOP value
    uf_emitente: str
    uf_destinatario: Optional[str]
    destino_geografico: str  # DestinoGeograficoCFOP value
    natureza_operacao: str  # NaturezaOperacaoCFOP value
    origem_mercadoria_comercial: str  # OrigemMercadoriaComercial value
    destinatario_contribuinte_icms: Optional[bool] = None
    consumidor_final: Optional[bool] = None
    gera_icms_st: bool = False
    finalidade_emissao: Optional[str] = None


def resolver_cfop(contexto: ContextoCFOP) -> str:
    """
    Resolve CFOP com base no contexto da operação.
    Retorna CFOP 4 dígitos (ex.: 5102, 6101).
    Levanta ErroCFOPResolver se contexto insuficiente.
    """
    tipo = (contexto.tipo_documento or "").strip().lower()
    natureza = (contexto.natureza_operacao or "venda").strip().lower()
    destino = (contexto.destino_geografico or "").strip().lower()
    origem_com = (contexto.origem_mercadoria_comercial or "mercadoria_terceiros").strip().lower()

    # Fase 1: saída - venda
    if tipo == TipoMovimentoCFOP.SAIDA.value:
        if natureza == NaturezaOperacaoCFOP.VENDA.value:
            if destino == DestinoGeograficoCFOP.INTERNA.value:
                if origem_com == OrigemMercadoriaComercial.PRODUCAO_PROPRIA.value:
                    return "5101"
                return "5102"
            if destino == DestinoGeograficoCFOP.INTERESTADUAL.value:
                if origem_com == OrigemMercadoriaComercial.PRODUCAO_PROPRIA.value:
                    return "6101"
                return "6102"
            if destino == DestinoGeograficoCFOP.EXTERIOR.value:
                raise ErroCFOPResolver(
                    "Operação de saída para exterior não mapeada na fase 1. Configure manualmente."
                )
        if natureza == NaturezaOperacaoCFOP.DEVOLUCAO.value:
            raise ErroCFOPResolver(
                "Devolução de saída não mapeada na fase 1. Configure manualmente."
            )
        raise ErroCFOPResolver(
            f"Natureza de operação '{natureza}' para saída não mapeada. Use venda, devolução, etc."
        )

    # Fase 1: entrada - devolução
    if tipo == TipoMovimentoCFOP.ENTRADA.value:
        if natureza == NaturezaOperacaoCFOP.DEVOLUCAO.value:
            if destino == DestinoGeograficoCFOP.INTERNA.value:
                return "1202"
            if destino == DestinoGeograficoCFOP.INTERESTADUAL.value:
                return "2202"
            if destino == DestinoGeograficoCFOP.EXTERIOR.value:
                raise ErroCFOPResolver("Devolução de entrada do exterior não mapeada.")
        if natureza == NaturezaOperacaoCFOP.VENDA.value:
            if destino == DestinoGeograficoCFOP.INTERNA.value:
                return "1102"
            if destino == DestinoGeograficoCFOP.INTERESTADUAL.value:
                return "2102"
        raise ErroCFOPResolver(
            f"Natureza '{natureza}' para entrada não mapeada na fase 1."
        )

    raise ErroCFOPResolver(
        f"Tipo de documento '{tipo}' inválido. Use 'entrada' ou 'saida'."
    )
