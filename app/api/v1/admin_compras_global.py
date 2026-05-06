# PDV Ibix — Superadmin: linhas de compra (PDV + vitrine), produto e categoria
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.middleware import require_superadmin
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.admin_compras_global import CompraGlobalLinha, CompraGlobalListResponse
from app.services.admin_compras_global_service import listar_compras_globais

router = APIRouter(prefix="/admin/compras-globais", tags=["Admin — Compras globais"])


def _parse_dt(val: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    if not val or not str(val).strip():
        return None
    s = str(val).strip()
    try:
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            if end_of_day:
                return datetime.fromisoformat(f"{s}T23:59:59")
            return datetime.fromisoformat(f"{s}T00:00:00")
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.get("/linhas", response_model=CompraGlobalListResponse)
async def listar_linhas_compras_globais(
    origem: str = Query(
        "todos",
        description="pdv | vitrine | todos",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    busca_email: Optional[str] = Query(None, description="Filtra por e-mail do comprador (contém)"),
    data_inicio: Optional[str] = Query(None, description="ISO ou YYYY-MM-DD"),
    data_fim: Optional[str] = Query(None, description="ISO ou YYYY-MM-DD (fim do dia se só data)"),
    incluir_pdv_sem_cliente: bool = Query(
        False,
        description="Se true, inclui linhas de PDV sem cliente vinculado (ex.: consumidor final)",
    ),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    """
    Lista linhas de item de compra em todo o sistema (Superadministrador).

    - **PDV**: vendas finalizadas; por padrão só linhas com `cliente_id` na venda.
    - **Vitrine**: itens de pedidos marketplace com `status_pagamento = pago`.
    - **Produto / categoria**: PDV via `produtos_cliente` + categoria cadastrada; vitrine via snapshot do pedido.
    - **cookies**: reservado (null); atribuição UTM/canal em `atribuicao` para vitrine.
    """
    o = (origem or "").strip().lower()
    if o not in ("pdv", "vitrine", "todos"):
        raise HTTPException(status_code=400, detail="origem deve ser pdv, vitrine ou todos")
    origem = o

    di = _parse_dt(data_inicio, end_of_day=False)
    df = _parse_dt(data_fim, end_of_day=True)

    raw, total = listar_compras_globais(
        db,
        origem=origem,
        skip=skip,
        limit=limit,
        busca_email=busca_email,
        data_inicio=di,
        data_fim=df,
        apenas_com_cliente_identificado_pdv=not incluir_pdv_sem_cliente,
    )
    items = [CompraGlobalLinha.model_validate(x) for x in raw]
    return CompraGlobalListResponse(items=items, total=total, skip=skip, limit=limit)
