# PDV Ibix - API do Portal do Cliente Final (Subcliente)
"""Endpoints restritos ao escopo do cliente final: resumo de gastos e valores por equipamento."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.middleware import get_cliente_scope_dep, get_current_user
from app.core.scope import ClienteScope
from app.database.connection import get_db
from app.models import NotaServico, OrdemServico, Venda
from app.models.usuario import Usuario

router = APIRouter(
    prefix="/portal",
    tags=["Portal Cliente Final"],
)


def _require_subcliente_scope(scope: ClienteScope, current_user: Usuario) -> None:
    """Garante que o usuário é Subcliente com escopo de um único cliente. Levanta 403 caso contrário."""
    if not current_user.role or current_user.role.nome != "Subcliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao Portal do Cliente Final.",
        )
    if not scope.must_filter_by_cliente() or not scope.allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cliente não vinculado.",
        )


@router.get("/resumo-gastos", response_model=dict)
def resumo_gastos(
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna resumo de gastos (vendas, ordens de serviço, notas) para o cliente do token. Apenas Subcliente."""
    _require_subcliente_scope(scope, current_user)
    allowed = scope.allowed_ids

    # Total vendas (Venda.total onde cliente_id in allowed)
    vendas_row = (
        db.query(
            func.coalesce(func.sum(Venda.total), 0).label("total"),
            func.count(Venda.id).label("quantidade"),
        )
        .filter(Venda.cliente_id.in_(allowed))
        .first()
    )
    total_vendas = float(vendas_row.total or 0)
    quantidade_vendas = int(vendas_row.quantidade or 0)

    # Total ordens de serviço: soma dos itens das OS do cliente (ou total da OS se não houver itens)
    ordens = (
        db.query(OrdemServico)
        .options(selectinload(OrdemServico.itens))
        .filter(OrdemServico.cliente_id.in_(allowed))
        .all()
    )
    total_ordens = 0.0
    quantidade_ordens = len(ordens)
    for os_obj in ordens:
        if os_obj.itens:
            total_ordens += sum(float(getattr(i, "valor_total") or 0) for i in os_obj.itens)
        else:
            # fallback: não há campo total na OS; usar 0
            pass

    # Total notas de serviço (destinatário = cliente)
    notas_row = (
        db.query(
            func.coalesce(func.sum(NotaServico.valor_total), 0).label("total"),
            func.count(NotaServico.id).label("quantidade"),
        )
        .filter(NotaServico.cliente_id.in_(allowed))
        .first()
    )
    total_notas = float(notas_row.total or 0)
    quantidade_notas = int(notas_row.quantidade or 0)

    return {
        "vendas": {"total": total_vendas, "quantidade": quantidade_vendas},
        "ordens_servico": {"total": total_ordens, "quantidade": quantidade_ordens},
        "notas_fiscais": {"total": total_notas, "quantidade": quantidade_notas},
        "total_geral": total_vendas + total_ordens + total_notas,
    }


@router.get("/equipamentos/valores-servicos", response_model=dict)
def valores_servicos_por_equipamento(
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    """Módulo equipamentos removido - retorna lista vazia."""
    _require_subcliente_scope(scope, current_user)
    return {"equipamentos": []}
