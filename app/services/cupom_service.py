# PDV Ibix - Service para cupons de desconto do marketplace
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.error_codes import (
    CUPOM_EXPIRADO,
    CUPOM_INVALIDO,
    CUPOM_LIMITE_ATINGIDO,
    CUPOM_VALOR_MINIMO,
)
from app.models.cupom_consumidor import CupomConsumidor
from app.models.cupom_marketplace import CupomMarketplace
from app.models.loja_marketplace import LojaMarketplace

logger = logging.getLogger(__name__)


def validar_cupom(
    db: Session,
    codigo: str,
    consumidor_id: int,
    valor_total: Decimal,
    loja_id: Optional[int] = None,
) -> dict:
    cupom = (
        db.query(CupomMarketplace)
        .filter(CupomMarketplace.codigo == codigo.upper().strip())
        .first()
    )
    if not cupom or not cupom.ativo:
        return {"valido": False, "desconto": None, "tipo_desconto": None, "mensagem": "Cupom inválido", "code": CUPOM_INVALIDO}

    agora = datetime.now(timezone.utc)
    if cupom.valido_de and cupom.valido_de > agora:
        return {"valido": False, "desconto": None, "tipo_desconto": None, "mensagem": "Cupom ainda não está ativo", "code": CUPOM_INVALIDO}
    if cupom.valido_ate and cupom.valido_ate < agora:
        return {"valido": False, "desconto": None, "tipo_desconto": None, "mensagem": "Cupom expirado", "code": CUPOM_EXPIRADO}

    if cupom.uso_maximo is not None and cupom.uso_atual >= cupom.uso_maximo:
        return {"valido": False, "desconto": None, "tipo_desconto": None, "mensagem": "Cupom esgotado", "code": CUPOM_LIMITE_ATINGIDO}

    if cupom.uso_maximo_por_consumidor is not None:
        usos_consumidor = (
            db.query(func.count(CupomConsumidor.id))
            .filter(
                CupomConsumidor.cupom_id == cupom.id,
                CupomConsumidor.consumidor_id == consumidor_id,
            )
            .scalar()
        )
        if usos_consumidor >= cupom.uso_maximo_por_consumidor:
            return {"valido": False, "desconto": None, "tipo_desconto": None, "mensagem": "Você já usou este cupom", "code": CUPOM_LIMITE_ATINGIDO}

    if cupom.valor_minimo_pedido and valor_total < cupom.valor_minimo_pedido:
        return {
            "valido": False,
            "desconto": None,
            "tipo_desconto": None,
            "mensagem": f"Valor mínimo do pedido: R$ {cupom.valor_minimo_pedido:.2f}",
            "code": CUPOM_VALOR_MINIMO,
        }

    if cupom.loja_id is not None and loja_id is not None and cupom.loja_id != loja_id:
        return {"valido": False, "desconto": None, "tipo_desconto": None, "mensagem": "Cupom não é válido para esta loja", "code": CUPOM_INVALIDO}

    if cupom.tipo_desconto == "percentual":
        desconto = (valor_total * cupom.valor_desconto / Decimal("100")).quantize(Decimal("0.01"))
    else:
        desconto = min(cupom.valor_desconto, valor_total)

    return {
        "valido": True,
        "desconto": desconto,
        "tipo_desconto": cupom.tipo_desconto,
        "mensagem": f"Cupom aplicado: -R$ {desconto:.2f}",
        "cupom_id": cupom.id,
        "code": None,
    }


def aplicar_cupom(db: Session, cupom_id: int, consumidor_id: int, pedido_id: int) -> bool:
    """Aplica cupom atomicamente com UPDATE condicional para evitar race condition."""
    if cupom_id is None:
        return False

    updated = (
        db.query(CupomMarketplace)
        .filter(
            CupomMarketplace.id == cupom_id,
            CupomMarketplace.ativo.is_(True),
            (CupomMarketplace.uso_maximo.is_(None)) | (CupomMarketplace.uso_atual < CupomMarketplace.uso_maximo),
        )
        .update(
            {"uso_atual": CupomMarketplace.uso_atual + 1},
            synchronize_session=False,
        )
    )
    if updated == 0:
        logger.warning("cupom_id=%s não pôde ser aplicado (esgotado ou inativo)", cupom_id)
        return False

    try:
        uso = CupomConsumidor(
            cupom_id=cupom_id,
            consumidor_id=consumidor_id,
            pedido_id=pedido_id,
        )
        db.add(uso)
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.warning("Uso duplicado cupom_id=%s consumidor_id=%s", cupom_id, consumidor_id)
        return False
    return True


def listar_disponiveis(db: Session, consumidor_id: int) -> List[dict]:
    agora = datetime.now(timezone.utc)
    cupons = (
        db.query(CupomMarketplace)
        .filter(
            CupomMarketplace.ativo.is_(True),
            (CupomMarketplace.valido_de.is_(None)) | (CupomMarketplace.valido_de <= agora),
            (CupomMarketplace.valido_ate.is_(None)) | (CupomMarketplace.valido_ate >= agora),
        )
        .all()
    )
    resultado = []
    for c in cupons:
        if c.uso_maximo is not None and c.uso_atual >= c.uso_maximo:
            continue
        if c.uso_maximo_por_consumidor is not None:
            usos = (
                db.query(func.count(CupomConsumidor.id))
                .filter(CupomConsumidor.cupom_id == c.id, CupomConsumidor.consumidor_id == consumidor_id)
                .scalar()
            )
            if usos >= c.uso_maximo_por_consumidor:
                continue

        loja_nome = None
        if c.loja_id:
            loja = db.query(LojaMarketplace.nome_loja).filter(LojaMarketplace.id == c.loja_id).first()
            loja_nome = loja[0] if loja else None

        resultado.append({
            "id": c.id,
            "codigo": c.codigo,
            "tipo_desconto": c.tipo_desconto,
            "valor_desconto": c.valor_desconto,
            "valor_minimo_pedido": c.valor_minimo_pedido,
            "valido_ate": c.valido_ate,
            "loja_nome": loja_nome,
        })
    return resultado
