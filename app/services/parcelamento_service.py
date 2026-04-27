# PDV Ibix - Service para simulação de parcelamento
from decimal import ROUND_HALF_UP, Decimal
from typing import List

MAX_PARCELAS_SEM_JUROS = 3
MAX_PARCELAS_COM_JUROS = 12
TAXA_JUROS_MENSAL = Decimal("0.0199")  # 1.99% a.m. (padrão Mercado Pago)
PARCELA_MINIMA = Decimal("5.00")


def simular_parcelas(valor: Decimal) -> dict:
    if valor <= 0:
        return {"valor_original": valor, "opcoes": []}

    opcoes: List[dict] = []

    for n in range(1, MAX_PARCELAS_COM_JUROS + 1):
        if n <= MAX_PARCELAS_SEM_JUROS:
            valor_parcela = (valor / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total = valor_parcela * n
            opcoes.append({
                "parcelas": n,
                "valor_parcela": valor_parcela,
                "total": total,
                "juros": False,
                "taxa_juros": None,
            })
        else:
            coef = (TAXA_JUROS_MENSAL * (1 + TAXA_JUROS_MENSAL) ** n) / ((1 + TAXA_JUROS_MENSAL) ** n - 1)
            valor_parcela = (valor * coef).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if valor_parcela < PARCELA_MINIMA:
                break
            total = valor_parcela * n
            opcoes.append({
                "parcelas": n,
                "valor_parcela": valor_parcela,
                "total": total,
                "juros": True,
                "taxa_juros": TAXA_JUROS_MENSAL * 100,
            })

    return {"valor_original": valor, "opcoes": opcoes}
