"""Geração de número sequencial de venda (VENDA-{ano}-{numero:06d}). Reutilizado por API de vendas e por Enviar para vendas (OS)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.venda import Venda


def gerar_numero_venda(db: Session) -> str:
    """Gera próximo número de venda no formato VENDA-{ano}-{numero:06d}."""
    ano_atual = datetime.now().year
    ultima_venda = (
        db.query(Venda)
        .filter(Venda.numero_venda.like(f"VENDA-{ano_atual}-%"))
        .order_by(Venda.numero_venda.desc())
        .first()
    )
    if ultima_venda:
        try:
            numero_parte = ultima_venda.numero_venda.split("-")[2]
            proximo_numero = int(numero_parte) + 1
        except (IndexError, ValueError):
            proximo_numero = 1
    else:
        proximo_numero = 1
    return f"VENDA-{ano_atual}-{proximo_numero:06d}"
