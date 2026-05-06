# PDV Ibix — Listagem Superadmin: compras PDV + vitrine (produto e categoria)
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Boolean, Integer, Numeric, String, cast, func, literal, select, union_all
from sqlalchemy.orm import Session, aliased

from app.models.cliente import Cliente
from app.models.material_categoria import MaterialCategoria
from app.models.pedido_item_marketplace import PedidoItemMarketplace
from app.models.pedido_marketplace import PedidoMarketplace
from app.models.produto_cliente import ProdutoCliente
from app.models.venda import StatusVenda, Venda, VendaItem


STATUS_VENDA_CONCLUIDA = (
    StatusVenda.CONFIRMADA.value,
    StatusVenda.FINALIZADA.value,
    StatusVenda.FINALIZADA_LEGADO.value,
)


def _rows_to_payload(rows: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        origem = r.origem
        attr: Optional[Dict[str, Any]] = None
        cookies: Optional[Dict[str, Any]] = None
        if origem == "vitrine":
            attr = {}
            if getattr(r, "canal_origem", None):
                attr["canal_origem"] = r.canal_origem
            if getattr(r, "utm_source", None):
                attr["utm_source"] = r.utm_source
            if getattr(r, "utm_medium", None):
                attr["utm_medium"] = r.utm_medium
            if getattr(r, "utm_campaign", None):
                attr["utm_campaign"] = r.utm_campaign
            if getattr(r, "aceite_marketing_snapshot", None) is not None:
                attr["aceite_marketing"] = bool(r.aceite_marketing_snapshot)
            if getattr(r, "consumidor_marketplace_id", None) is not None:
                attr["consumidor_marketplace_id"] = r.consumidor_marketplace_id
            if not attr:
                attr = None
        nome_comprador = (r.comprador_nome or "").strip() or "—"
        cat = getattr(r, "categoria", None)
        if isinstance(cat, str):
            cat = cat.strip() or None
        out.append(
            {
                "origem": origem,
                "linha_id": int(r.linha_id),
                "data_ref": r.data_ref,
                "estabelecimento_cliente_id": int(r.estabelecimento_cliente_id),
                "estabelecimento_nome": r.estabelecimento_nome,
                "cliente_id": int(r.cliente_id) if r.cliente_id is not None else None,
                "comprador_nome": nome_comprador,
                "comprador_email": (r.comprador_email or "").strip() or None,
                "produto_nome": r.produto_nome or "—",
                "categoria": cat,
                "quantidade": Decimal(str(r.quantidade)),
                "valor_total_item": Decimal(str(r.valor_total_item)),
                "documento_ref": r.documento_ref or "",
                "venda_ou_pedido_id": int(r.venda_ou_pedido_id),
                "atribuicao": attr,
                "cookies": cookies,
            }
        )
    return out


def listar_linhas_pdv(
    db: Session,
    *,
    skip: int,
    limit: int,
    busca_email: Optional[str],
    data_inicio: Optional[datetime],
    data_fim: Optional[datetime],
    apenas_com_cliente_identificado: bool,
) -> Tuple[List[Dict[str, Any]], int]:
    Comprador = aliased(Cliente, name="comprador_pdv")
    Estab = aliased(Cliente, name="estab_pdv")

    base = (
        db.query(
            literal("pdv").label("origem"),
            VendaItem.id.label("linha_id"),
            Venda.data_venda.label("data_ref"),
            ProdutoCliente.cliente_id.label("estabelecimento_cliente_id"),
            Estab.nome.label("estabelecimento_nome"),
            Venda.cliente_id.label("cliente_id"),
            Comprador.nome.label("comprador_nome"),
            Comprador.email.label("comprador_email"),
            ProdutoCliente.nome.label("produto_nome"),
            func.coalesce(MaterialCategoria.nome, ProdutoCliente.categoria).label("categoria"),
            cast(VendaItem.quantidade, Numeric(12, 4)).label("quantidade"),
            VendaItem.valor_total.label("valor_total_item"),
            Venda.numero_venda.label("documento_ref"),
            Venda.id.label("venda_ou_pedido_id"),
            cast(literal(None), String).label("canal_origem"),
            cast(literal(None), String).label("utm_source"),
            cast(literal(None), String).label("utm_medium"),
            cast(literal(None), String).label("utm_campaign"),
            cast(literal(None), Boolean).label("aceite_marketing_snapshot"),
            cast(literal(None), Integer).label("consumidor_marketplace_id"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .join(ProdutoCliente, ProdutoCliente.id == VendaItem.produto_cliente_id)
        .outerjoin(MaterialCategoria, MaterialCategoria.id == ProdutoCliente.categoria_id)
        .join(Estab, Estab.id == ProdutoCliente.cliente_id)
        .outerjoin(Comprador, Comprador.id == Venda.cliente_id)
        .filter(Venda.status.in_(STATUS_VENDA_CONCLUIDA))
        .filter(VendaItem.produto_cliente_id.isnot(None))
    )
    if apenas_com_cliente_identificado:
        base = base.filter(Venda.cliente_id.isnot(None))
    if busca_email:
        like = f"%{busca_email.strip()}%"
        base = base.filter(Comprador.email.ilike(like))
    if data_inicio is not None:
        base = base.filter(Venda.data_venda >= data_inicio)
    if data_fim is not None:
        base = base.filter(Venda.data_venda <= data_fim)

    total = base.count()
    rows = (
        base.order_by(Venda.data_venda.desc()).offset(skip).limit(limit).all()
    )
    return _rows_to_payload(rows), total


def listar_linhas_vitrine(
    db: Session,
    *,
    skip: int,
    limit: int,
    busca_email: Optional[str],
    data_inicio: Optional[datetime],
    data_fim: Optional[datetime],
) -> Tuple[List[Dict[str, Any]], int]:
    Estab = aliased(Cliente, name="estab_mp")

    base = (
        db.query(
            literal("vitrine").label("origem"),
            PedidoItemMarketplace.id.label("linha_id"),
            PedidoMarketplace.created_at.label("data_ref"),
            PedidoMarketplace.tenant_id.label("estabelecimento_cliente_id"),
            Estab.nome.label("estabelecimento_nome"),
            literal(None).label("cliente_id"),
            PedidoMarketplace.comprador_nome.label("comprador_nome"),
            PedidoMarketplace.comprador_email.label("comprador_email"),
            PedidoItemMarketplace.nome_produto_snapshot.label("produto_nome"),
            PedidoItemMarketplace.categoria_snapshot.label("categoria"),
            cast(PedidoItemMarketplace.quantidade, Numeric(12, 4)).label("quantidade"),
            PedidoItemMarketplace.preco_total.label("valor_total_item"),
            PedidoMarketplace.numero_pedido.label("documento_ref"),
            PedidoMarketplace.id.label("venda_ou_pedido_id"),
            PedidoMarketplace.canal_origem.label("canal_origem"),
            PedidoMarketplace.utm_source.label("utm_source"),
            PedidoMarketplace.utm_medium.label("utm_medium"),
            PedidoMarketplace.utm_campaign.label("utm_campaign"),
            PedidoMarketplace.aceite_marketing_snapshot.label("aceite_marketing_snapshot"),
            PedidoMarketplace.comprador_id.label("consumidor_marketplace_id"),
        )
        .select_from(PedidoItemMarketplace)
        .join(PedidoMarketplace, PedidoMarketplace.id == PedidoItemMarketplace.pedido_id)
        .outerjoin(Estab, Estab.id == PedidoMarketplace.tenant_id)
        .filter(func.lower(PedidoMarketplace.status_pagamento) == "pago")
    )
    if busca_email:
        like = f"%{busca_email.strip()}%"
        base = base.filter(PedidoMarketplace.comprador_email.ilike(like))
    if data_inicio is not None:
        base = base.filter(PedidoMarketplace.created_at >= data_inicio)
    if data_fim is not None:
        base = base.filter(PedidoMarketplace.created_at <= data_fim)

    total = base.count()
    rows = (
        base.order_by(PedidoMarketplace.created_at.desc()).offset(skip).limit(limit).all()
    )
    return _rows_to_payload(rows), total


def _union_pdv_vitrine_select(
    *,
    busca_email: Optional[str],
    data_inicio: Optional[datetime],
    data_fim: Optional[datetime],
    apenas_com_cliente_identificado_pdv: bool,
):
    """Constrói dois selects compatíveis para UNION ALL."""
    Comprador = aliased(Cliente, name="comprador_pdv_u")
    Estab_pdv = aliased(Cliente, name="estab_pdv_u")
    Estab_mp = aliased(Cliente, name="estab_mp_u")

    pdv_sel = (
        select(
            literal("pdv").label("origem"),
            VendaItem.id.label("linha_id"),
            Venda.data_venda.label("data_ref"),
            ProdutoCliente.cliente_id.label("estabelecimento_cliente_id"),
            Estab_pdv.nome.label("estabelecimento_nome"),
            Venda.cliente_id.label("cliente_id"),
            Comprador.nome.label("comprador_nome"),
            Comprador.email.label("comprador_email"),
            ProdutoCliente.nome.label("produto_nome"),
            func.coalesce(MaterialCategoria.nome, ProdutoCliente.categoria).label("categoria"),
            cast(VendaItem.quantidade, Numeric(12, 4)).label("quantidade"),
            VendaItem.valor_total.label("valor_total_item"),
            Venda.numero_venda.label("documento_ref"),
            Venda.id.label("venda_ou_pedido_id"),
            cast(literal(None), String).label("canal_origem"),
            cast(literal(None), String).label("utm_source"),
            cast(literal(None), String).label("utm_medium"),
            cast(literal(None), String).label("utm_campaign"),
            cast(literal(None), Boolean).label("aceite_marketing_snapshot"),
            cast(literal(None), Integer).label("consumidor_marketplace_id"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .join(ProdutoCliente, ProdutoCliente.id == VendaItem.produto_cliente_id)
        .outerjoin(MaterialCategoria, MaterialCategoria.id == ProdutoCliente.categoria_id)
        .join(Estab_pdv, Estab_pdv.id == ProdutoCliente.cliente_id)
        .outerjoin(Comprador, Comprador.id == Venda.cliente_id)
        .where(Venda.status.in_(STATUS_VENDA_CONCLUIDA))
        .where(VendaItem.produto_cliente_id.isnot(None))
    )
    if apenas_com_cliente_identificado_pdv:
        pdv_sel = pdv_sel.where(Venda.cliente_id.isnot(None))
    if busca_email:
        like = f"%{busca_email.strip()}%"
        pdv_sel = pdv_sel.where(Comprador.email.ilike(like))
    if data_inicio is not None:
        pdv_sel = pdv_sel.where(Venda.data_venda >= data_inicio)
    if data_fim is not None:
        pdv_sel = pdv_sel.where(Venda.data_venda <= data_fim)

    mp_sel = (
        select(
            literal("vitrine").label("origem"),
            PedidoItemMarketplace.id.label("linha_id"),
            PedidoMarketplace.created_at.label("data_ref"),
            PedidoMarketplace.tenant_id.label("estabelecimento_cliente_id"),
            Estab_mp.nome.label("estabelecimento_nome"),
            cast(literal(None), Integer).label("cliente_id"),
            PedidoMarketplace.comprador_nome.label("comprador_nome"),
            PedidoMarketplace.comprador_email.label("comprador_email"),
            PedidoItemMarketplace.nome_produto_snapshot.label("produto_nome"),
            PedidoItemMarketplace.categoria_snapshot.label("categoria"),
            cast(PedidoItemMarketplace.quantidade, Numeric(12, 4)).label("quantidade"),
            PedidoItemMarketplace.preco_total.label("valor_total_item"),
            PedidoMarketplace.numero_pedido.label("documento_ref"),
            PedidoMarketplace.id.label("venda_ou_pedido_id"),
            PedidoMarketplace.canal_origem.label("canal_origem"),
            PedidoMarketplace.utm_source.label("utm_source"),
            PedidoMarketplace.utm_medium.label("utm_medium"),
            PedidoMarketplace.utm_campaign.label("utm_campaign"),
            PedidoMarketplace.aceite_marketing_snapshot.label("aceite_marketing_snapshot"),
            PedidoMarketplace.comprador_id.label("consumidor_marketplace_id"),
        )
        .select_from(PedidoItemMarketplace)
        .join(PedidoMarketplace, PedidoMarketplace.id == PedidoItemMarketplace.pedido_id)
        .outerjoin(Estab_mp, Estab_mp.id == PedidoMarketplace.tenant_id)
        .where(func.lower(PedidoMarketplace.status_pagamento) == "pago")
    )
    if busca_email:
        like = f"%{busca_email.strip()}%"
        mp_sel = mp_sel.where(PedidoMarketplace.comprador_email.ilike(like))
    if data_inicio is not None:
        mp_sel = mp_sel.where(PedidoMarketplace.created_at >= data_inicio)
    if data_fim is not None:
        mp_sel = mp_sel.where(PedidoMarketplace.created_at <= data_fim)

    return union_all(pdv_sel, mp_sel)


def listar_compras_globais(
    db: Session,
    *,
    origem: str,
    skip: int,
    limit: int,
    busca_email: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    apenas_com_cliente_identificado_pdv: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    origem = (origem or "todos").strip().lower()
    if origem == "pdv":
        return listar_linhas_pdv(
            db,
            skip=skip,
            limit=limit,
            busca_email=busca_email,
            data_inicio=data_inicio,
            data_fim=data_fim,
            apenas_com_cliente_identificado=apenas_com_cliente_identificado_pdv,
        )
    if origem == "vitrine":
        return listar_linhas_vitrine(
            db,
            skip=skip,
            limit=limit,
            busca_email=busca_email,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    u = _union_pdv_vitrine_select(
        busca_email=busca_email,
        data_inicio=data_inicio,
        data_fim=data_fim,
        apenas_com_cliente_identificado_pdv=apenas_com_cliente_identificado_pdv,
    ).subquery("u")

    cnt = db.scalar(select(func.count()).select_from(u))
    total = int(cnt or 0)

    stmt = select(u).order_by(u.c.data_ref.desc()).offset(skip).limit(limit)
    mapped = [
        SimpleNamespace(**dict(row._mapping))
        for row in db.execute(stmt)
    ]
    return _rows_to_payload(mapped), total
