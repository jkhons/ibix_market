# PDV Ibix - Preço público (sem auth) para landing page
"""Endpoint público: retorna preço vigente para exibição na landing de preços."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database.connection import get_db
from ...models.preco_pdv import PrecoPdv
from ...schemas.preco_pdv import PrecoPdvResponse

router = APIRouter(prefix="/precos", tags=["Preços (público)"])


@router.get("/vigente", response_model=PrecoPdvResponse)
def preco_vigente_publico(db: Session = Depends(get_db)):
    """Retorna o preço vigente (sem autenticação) — usado pela landing page."""
    preco = (
        db.query(PrecoPdv)
        .filter(PrecoPdv.ativo == True)
        .order_by(PrecoPdv.vigencia_inicio.desc())
        .first()
    )
    if not preco:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum preço vigente configurado")
    return preco
