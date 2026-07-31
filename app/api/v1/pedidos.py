# PDV Ibix - API de Pedidos (Módulo Orçamento e Pedido)
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from app.core.document_ref import build_doc_ref, doc_ref_like_patterns, next_seq_for_year
from app.core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from app.core.scope import ClienteScope
from app.database.connection import get_db
from app.models import Orcamento, Pedido, PedidoItem, ProdutoCliente, Tenant, Usuario
from app.schemas.cupom import CupomConteudoResponse
from app.schemas.pedido import PedidoCreate, PedidoFaturarBody, PedidoListResponse, PedidoResponse, PedidoUpdate
from app.services.cupom_receipt import gerar_cupom_resumo_pedido_negocio
from app.services.pdf_orcamento_pedido import gerar_pdf_pedido
from app.services.pedido_service import faturar_pedido, liberar_reserva, reservar_estoque

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def _allowed_ids(scope: ClienteScope):
    if scope.is_superadmin:
        return None
    return scope.allowed_ids or []


def _pedido_no_escopo(db: Session, pedido_id: int, scope: ClienteScope, load_itens: bool = False) -> Pedido | None:
    q = db.query(Pedido).filter(Pedido.id == pedido_id)
    if load_itens:
        q = q.options(joinedload(Pedido.itens))
    p = q.first()
    if not p:
        return None
    allowed = _allowed_ids(scope)
    if allowed is not None and p.cliente_id not in allowed:
        return None
    return p


def _proximo_numero_pedido(db: Session, cliente_id: int) -> str:
    ano = datetime.now().year
    patterns = doc_ref_like_patterns("PED", ano)
    rows = (
        db.query(Pedido.numero_pedido)
        .filter(
            Pedido.cliente_id == cliente_id,
            or_(*[Pedido.numero_pedido.like(p) for p in patterns]),
        )
        .all()
    )
    seq = next_seq_for_year((r[0] for r in rows), ano, prefix="PED")
    return build_doc_ref("PED", seq, ano)


@router.get("", response_model=dict)
async def listar_pedidos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: str | None = Query(None),
    cliente_id: int | None = Query(None),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista pedidos com paginação. Filtro por status e cliente_id (estabelecimento)."""
    q = db.query(Pedido)
    allowed = _allowed_ids(scope)
    if allowed is not None:
        q = q.filter(Pedido.cliente_id.in_(allowed))
    if status:
        q = q.filter(Pedido.status == status)
    if cliente_id is not None:
        if allowed is not None and cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Cliente fora do escopo")
        q = q.filter(Pedido.cliente_id == cliente_id)
    total = q.count()
    rows = q.order_by(desc(Pedido.created_at)).offset(skip).limit(limit).all()
    itens = [PedidoListResponse.model_validate(r) for r in rows]
    return {"pedidos": itens, "total": total, "skip": skip, "limit": limit}


@router.get("/{pedido_id}", response_model=PedidoResponse)
async def obter_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Detalhe de um pedido."""
    p = _pedido_no_escopo(db, pedido_id, scope, load_itens=True)
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return PedidoResponse.model_validate(p)


@router.get("/{pedido_id}/cupom", response_model=CupomConteudoResponse)
async def obter_cupom_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna conteúdo do cupom não fiscal do pedido interno para impressão (térmica / browser)."""
    p = (
        db.query(Pedido)
        .options(joinedload(Pedido.itens), joinedload(Pedido.cliente))
        .filter(Pedido.id == pedido_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    allowed = _allowed_ids(scope)
    if allowed is not None and p.cliente_id not in allowed:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    tenant_id = getattr(current_user, "tenant_id", None)
    cupom_tipo = "nao_fiscal"
    if tenant_id:
        tenant = db.get(Tenant, tenant_id)
        if tenant and getattr(tenant, "cupom_tipo", None) == "fiscal":
            cupom_tipo = "fiscal"
    if cupom_tipo == "fiscal":
        return CupomConteudoResponse(tipo="fiscal", linhas=[], html=None)
    estab = "Estabelecimento"
    if p.cliente and (p.cliente.nome or "").strip():
        estab = (p.cliente.nome or "").strip()
    itens_data = []
    for i in p.itens or []:
        itens_data.append(
            {
                "codigo_produto": i.codigo_produto or "",
                "descricao_produto": i.descricao_produto or "",
                "quantidade": float(i.quantidade),
                "preco_unitario": float(i.preco_unitario),
                "total_item": float(i.total_item),
            }
        )
    linhas, html = gerar_cupom_resumo_pedido_negocio(
        estabelecimento_nome=estab,
        numero_pedido=p.numero_pedido or "",
        data_referencia=p.data_pedido or p.created_at,
        status=p.status or "",
        subtotal=p.subtotal,
        desconto=p.desconto,
        acrescimo=p.acrescimo,
        total=p.total,
        observacoes=p.observacoes,
        itens=itens_data,
    )
    return CupomConteudoResponse(tipo="nao_fiscal", linhas=linhas, html=html)


@router.post("", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
async def criar_pedido(
    body: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria pedido em rascunho (direto ou com orcamento_id se vier de conversão)."""
    allowed = _allowed_ids(scope)
    if allowed is not None and body.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Cliente fora do escopo")
    numero = _proximo_numero_pedido(db, body.cliente_id)
    subtotal = Decimal("0")
    itens_orm = []
    for item in body.itens:
        pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == item.produto_cliente_id).first()
        if not pc:
            raise HTTPException(status_code=404, detail=f"Produto {item.produto_cliente_id} não encontrado")
        if pc.cliente_id != body.cliente_id:
            raise HTTPException(status_code=400, detail=f"Produto não pertence ao estabelecimento {body.cliente_id}")
        total_item = Decimal(str(item.quantidade * item.preco_unitario))
        if item.desconto_valor:
            total_item -= Decimal(str(item.desconto_valor))
        elif item.desconto_percentual:
            total_item -= total_item * Decimal(str(item.desconto_percentual)) / Decimal("100")
        subtotal += total_item
        itens_orm.append({
            "produto_cliente_id": item.produto_cliente_id,
            "codigo_produto": pc.codigo,
            "descricao_produto": pc.nome,
            "quantidade": item.quantidade,
            "preco_unitario": item.preco_unitario,
            "desconto_percentual": item.desconto_percentual,
            "desconto_valor": item.desconto_valor,
            "total_item": total_item,
        })
    # Se o pedido está vinculado a um orçamento, validar e marcar orçamento como convertido (evita conversão duplicada)
    if body.orcamento_id:
        orc = db.query(Orcamento).filter(Orcamento.id == body.orcamento_id).first()
        if not orc:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado")
        if allowed is not None and orc.cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Orçamento fora do escopo")
        if orc.convertido_em_pedido_id:
            raise HTTPException(status_code=400, detail="Orçamento já foi convertido em pedido")
        if orc.cliente_id != body.cliente_id:
            raise HTTPException(status_code=400, detail="Orçamento não pertence ao estabelecimento do pedido")

    total = subtotal
    ped = Pedido(
        orcamento_id=body.orcamento_id,
        cliente_id=body.cliente_id,
        vendedor_id=current_user.id,
        numero_pedido=numero,
        data_prevista_entrega=body.data_prevista_entrega,
        status="rascunho",
        reserva_estoque=False,
        subtotal=subtotal,
        desconto=Decimal("0"),
        acrescimo=Decimal("0"),
        total=total,
        observacoes=body.observacoes,
    )
    db.add(ped)
    db.flush()
    if body.orcamento_id:
        orc = db.query(Orcamento).filter(Orcamento.id == body.orcamento_id).first()
        if orc and not orc.convertido_em_pedido_id:
            orc.status = "convertido"
            orc.convertido_em_pedido_id = ped.id
            orc.data_conversao = datetime.utcnow()
    for i in itens_orm:
        db.add(PedidoItem(
            pedido_id=ped.id,
            produto_cliente_id=i["produto_cliente_id"],
            codigo_produto=i["codigo_produto"],
            descricao_produto=i["descricao_produto"],
            quantidade=i["quantidade"],
            preco_unitario=i["preco_unitario"],
            desconto_percentual=i.get("desconto_percentual"),
            desconto_valor=i.get("desconto_valor"),
            total_item=i["total_item"],
            status="pendente",
        ))
    db.commit()
    db.refresh(ped)
    return PedidoResponse.model_validate(ped)


@router.put("/{pedido_id}", response_model=PedidoResponse)
async def atualizar_pedido(
    pedido_id: int,
    body: PedidoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza pedido apenas se estiver em rascunho."""
    p = _pedido_no_escopo(db, pedido_id, scope, load_itens=True)
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if p.status != "rascunho":
        raise HTTPException(status_code=400, detail="Só pedido em rascunho pode ser editado")
    if body.data_prevista_entrega is not None:
        p.data_prevista_entrega = body.data_prevista_entrega
    if body.observacoes is not None:
        p.observacoes = body.observacoes
    if body.itens is not None:
        for existing in p.itens[:]:
            db.delete(existing)
        subtotal = Decimal("0")
        for item in body.itens:
            pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == item.produto_cliente_id).first()
            if not pc:
                raise HTTPException(status_code=404, detail=f"Produto {item.produto_cliente_id} não encontrado")
            if pc.cliente_id != p.cliente_id:
                raise HTTPException(status_code=400, detail="Produto não pertence ao estabelecimento")
            total_item = Decimal(str(item.quantidade * item.preco_unitario))
            if item.desconto_valor:
                total_item -= Decimal(str(item.desconto_valor))
            elif item.desconto_percentual:
                total_item -= total_item * Decimal(str(item.desconto_percentual)) / Decimal("100")
            subtotal += total_item
            db.add(
                PedidoItem(
                    pedido_id=p.id,
                    produto_cliente_id=item.produto_cliente_id,
                    codigo_produto=pc.codigo,
                    descricao_produto=pc.nome,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    desconto_percentual=item.desconto_percentual,
                    desconto_valor=item.desconto_valor,
                    total_item=total_item,
                    status="pendente",
                )
            )
        p.subtotal = subtotal
        p.total = subtotal
    db.commit()
    db.refresh(p)
    return PedidoResponse.model_validate(p)


@router.post("/{pedido_id}/cancelar", response_model=PedidoResponse)
async def cancelar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cancela o pedido (status = cancelado). Libera reserva se houver."""
    p = _pedido_no_escopo(db, pedido_id, scope, load_itens=True)
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if p.status == "cancelado":
        raise HTTPException(status_code=400, detail="Pedido já está cancelado")
    liberar_reserva(db, pedido_id)
    p = _pedido_no_escopo(db, pedido_id, scope, load_itens=True)
    p.status = "cancelado"
    db.commit()
    db.refresh(p)
    return PedidoResponse.model_validate(p)


@router.post("/{pedido_id}/reservar-estoque", response_model=dict)
async def reservar_estoque_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria reserva de estoque para os itens do pedido."""
    p = _pedido_no_escopo(db, pedido_id, scope, load_itens=False)
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    ok, msg = reservar_estoque(db, pedido_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": "Reserva de estoque realizada"}


@router.post("/{pedido_id}/liberar-reserva", response_model=dict)
async def liberar_reserva_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Libera a reserva de estoque do pedido."""
    p = _pedido_no_escopo(db, pedido_id, scope, load_itens=False)
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    liberar_reserva(db, pedido_id)
    return {"message": "Reserva liberada"}


@router.post("/{pedido_id}/faturar", response_model=dict)
async def faturar_pedido_route(
    pedido_id: int,
    body: PedidoFaturarBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Fatura (parcial ou total) itens do pedido; gera NF em rascunho e registra em pedido_faturamento."""
    p = _pedido_no_escopo(db, pedido_id, scope, load_itens=True)
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    itens_faturar = [(x.pedido_item_id, Decimal(str(x.quantidade))) for x in body.itens]
    ok, msg, nota_id = faturar_pedido(db, pedido_id, itens_faturar, current_user.id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": "Faturamento registrado", "nota_fiscal_id": nota_id}


def _dados_pedido_para_pdf(p) -> dict:
    """Monta dicionário para geração de PDF do pedido."""
    return {
        "numero_pedido": p.numero_pedido,
        "data_pedido": p.data_pedido,
        "data_prevista_entrega": p.data_prevista_entrega,
        "status": p.status,
        "cliente_nome": (p.cliente.nome if p.cliente else ""),
        "subtotal": p.subtotal,
        "total": p.total,
        "observacoes": p.observacoes or "",
        "itens": [
            {
                "codigo_produto": i.codigo_produto,
                "descricao_produto": i.descricao_produto,
                "quantidade": i.quantidade,
                "quantidade_faturada": i.quantidade_faturada,
                "preco_unitario": i.preco_unitario,
                "total_item": i.total_item,
            }
            for i in (p.itens or [])
        ],
    }


@router.get("/{pedido_id}/pdf")
async def download_pdf_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Gera e retorna PDF do pedido."""
    p = db.query(Pedido).options(
        joinedload(Pedido.itens),
        joinedload(Pedido.cliente),
    ).filter(Pedido.id == pedido_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    allowed = _allowed_ids(scope)
    if allowed is not None and p.cliente_id not in allowed:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    dados = _dados_pedido_para_pdf(p)
    pdf_bytes = gerar_pdf_pedido(dados)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="pedido-{p.numero_pedido}.pdf"'})
