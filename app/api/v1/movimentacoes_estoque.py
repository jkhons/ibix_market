# PDV Ibix - API Movimentações de Estoque (Fase 2 - produtos por estabelecimento)
"""Registrar entrada/saída/ajuste e atualizar quantidade_atual do produto_cliente. Escopo por cliente_id."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import MovimentacaoEstoque, NfeDocumento, ProdutoCliente, Usuario
from ...schemas.movimentacao_estoque import MovimentacaoEstoqueCreate, MovimentacaoEstoqueResponse

router = APIRouter(prefix="/movimentacoes-estoque", tags=["Movimentações (estabelecimento)"])

TIPOS = ("entrada", "saida", "ajuste")


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if not scope.must_filter_by_cliente():
        return None
    return scope.allowed_ids or []


@router.get("/ultima-entrada-nfe-por-produto", response_model=Dict[str, Any])
async def ultima_entrada_nfe_por_produto(
    cliente_id: int = Query(..., description="ID do estabelecimento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna, por produto_cliente_id, a última movimentação de entrada com NFe (nfe_item_id preenchido).
    Usado na tela de estoque para rastreio e filtro 'Com entrada NFe'."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    rows = (
        db.query(MovimentacaoEstoque, NfeDocumento)
        .join(ProdutoCliente, ProdutoCliente.id == MovimentacaoEstoque.produto_cliente_id)
        .outerjoin(NfeDocumento, NfeDocumento.id == MovimentacaoEstoque.nfe_documento_id)
        .filter(
            ProdutoCliente.cliente_id == cliente_id,
            MovimentacaoEstoque.tipo == "entrada",
            MovimentacaoEstoque.nfe_item_id.isnot(None),
        )
        .order_by(MovimentacaoEstoque.produto_cliente_id, MovimentacaoEstoque.created_at.desc())
        .all()
    )
    result: Dict[str, Any] = {}
    for mov, doc in rows:
        pid = str(mov.produto_cliente_id)
        if pid not in result:
            result[pid] = {
                "numero": (doc.numero or "").strip() or None if doc else None,
                "serie": (doc.serie or "").strip() or None if doc else None,
                "chave": (doc.chave_acesso_44 or "").strip() or None if doc else None,
                "data": mov.created_at.isoformat() if mov.created_at else None,
            }
    return result


@router.get("/", response_model=dict)
async def listar_movimentacoes(
    produto_cliente_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None, description="Filtrar por estabelecimento"),
    tipo: Optional[str] = Query(None, description="entrada | saida | ajuste"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista movimentações. Produto/cliente deve estar no escopo."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and not allowed:
        return {"items": [], "total": 0, "skip": skip, "limit": limit}
    q = db.query(MovimentacaoEstoque)
    if produto_cliente_id is not None:
        p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_cliente_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        if allowed is not None and p.cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Produto fora do escopo")
        q = q.filter(MovimentacaoEstoque.produto_cliente_id == produto_cliente_id)
    elif cliente_id is not None:
        if allowed is not None and cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
        q = q.join(ProdutoCliente).filter(ProdutoCliente.cliente_id == cliente_id)
    elif allowed is not None:
        q = q.join(ProdutoCliente).filter(ProdutoCliente.cliente_id.in_(allowed))
    if tipo and tipo in TIPOS:
        q = q.filter(MovimentacaoEstoque.tipo == tipo)
    total = q.count()
    rows = q.order_by(MovimentacaoEstoque.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "items": [MovimentacaoEstoqueResponse.model_validate(r) for r in rows],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/", response_model=MovimentacaoEstoqueResponse, status_code=status.HTTP_201_CREATED)
async def registrar_movimentacao(
    body: MovimentacaoEstoqueCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Registra entrada/saída/ajuste e atualiza produto_cliente.quantidade_atual. Entrada soma; saída/ajuste subtraem."""
    allowed = _allowed_cliente_ids(scope)
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == body.produto_cliente_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if allowed is not None and p.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Produto fora do escopo")
    if body.tipo not in TIPOS:
        raise HTTPException(status_code=400, detail=f"tipo deve ser um de: {', '.join(TIPOS)}")
    qtd = body.quantidade
    if body.tipo == "entrada":
        p.quantidade_atual += qtd
    else:
        if p.quantidade_atual < qtd:
            raise HTTPException(
                status_code=400,
                detail=f"Quantidade insuficiente. Disponível: {p.quantidade_atual}, solicitado: {qtd}",
            )
        p.quantidade_atual -= qtd
    mov = MovimentacaoEstoque(
        produto_cliente_id=p.id,
        tipo=body.tipo,
        quantidade=qtd,
        valor_unitario=body.valor_unitario,
        documento_ref=body.documento_ref,
        observacao=body.observacao,
        usuario_id=current_user.id,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return MovimentacaoEstoqueResponse.model_validate(mov)
