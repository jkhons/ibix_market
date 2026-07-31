# PDV Ibix - API Cupons para consumidor mobile
"""Validar e listar cupons disponíveis — requer consumidor autenticado."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database.connection import get_db
from ...schemas.mobile import (
    CupomDisponivelResponse,
    CupomValidarRequest,
    CupomValidarResponse,
)
from ...services.cupom_service import listar_disponiveis, validar_cupom
from .loja import get_current_consumidor

from ...core.brand_module_gating import MARKETPLACE_ROUTER_DEPENDENCIES

router = APIRouter(
    prefix="/loja/cupons",
    tags=["Loja – Cupons"],
    dependencies=MARKETPLACE_ROUTER_DEPENDENCIES,
)


@router.post("/validar", response_model=CupomValidarResponse)
async def validar_cupom_endpoint(
    body: CupomValidarRequest,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Valida se o cupom é aplicável ao pedido do consumidor."""
    resultado = validar_cupom(
        db,
        codigo=body.codigo,
        consumidor_id=consumidor.id,
        valor_total=body.valor_total,
        loja_id=body.loja_id,
    )
    return {
        "valido": resultado["valido"],
        "desconto": resultado.get("desconto"),
        "tipo_desconto": resultado.get("tipo_desconto"),
        "mensagem": resultado["mensagem"],
        "code": resultado.get("code"),
    }


@router.get("/disponiveis", response_model=list[CupomDisponivelResponse])
async def listar_cupons_disponiveis(
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Lista cupons ativos e disponíveis para o consumidor."""
    return listar_disponiveis(db, consumidor.id)
