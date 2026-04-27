# PDV Ibix - API LGPD para consumidor mobile
"""Consentimentos, exportar dados e solicitar exclusão de conta."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...database.connection import get_db
from ...schemas.mobile import (
    ConsentimentosResponse,
    ConsentimentoUpdateRequest,
    ExcluirContaRequest,
)
from ...services.lgpd_service import (
    exportar_dados,
    get_consentimentos,
    solicitar_exclusao,
    update_consentimentos,
)
from .loja import get_current_consumidor

router = APIRouter(prefix="/loja/minha-conta", tags=["Loja – LGPD"])


@router.get("/consentimentos", response_model=ConsentimentosResponse)
async def listar_consentimentos(
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    items = get_consentimentos(db, consumidor.id)
    return {"items": items}


@router.patch("/consentimentos", response_model=ConsentimentosResponse)
async def atualizar_consentimentos(
    body: ConsentimentoUpdateRequest,
    request: Request,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    from ...core.rate_limiter import get_client_ip
    ip = get_client_ip(request)
    try:
        items = update_consentimentos(
            db,
            consumidor_id=consumidor.id,
            ip=ip,
            updates=[c.model_dump() for c in body.consentimentos],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"detail": str(e), "code": "CONSENT_INVALID_TYPE"})
    return {"items": items}


@router.get("/dados-exportar")
async def exportar_meus_dados(
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Exporta todos os dados do consumidor (LGPD Art. 18)."""
    try:
        dados = exportar_dados(db, consumidor.id)
    except ValueError:
        raise HTTPException(status_code=404, detail={"detail": "Consumidor não encontrado", "code": "CONSUMIDOR_NOT_FOUND"})
    return dados


@router.post("/excluir-conta", status_code=202)
async def excluir_minha_conta(
    body: ExcluirContaRequest,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Solicita exclusão de conta (LGPD). Conta desativada imediatamente, exclusão em 30 dias."""
    try:
        solicitar_exclusao(db, consumidor.id, body.senha)
    except PermissionError:
        raise HTTPException(status_code=401, detail={"detail": "Senha incorreta", "code": "WRONG_PASSWORD"})
    except ValueError:
        raise HTTPException(status_code=404, detail={"detail": "Consumidor não encontrado", "code": "CONSUMIDOR_NOT_FOUND"})
    return {"mensagem": "Conta desativada. Exclusão definitiva em 30 dias. Contate o suporte para cancelar."}
