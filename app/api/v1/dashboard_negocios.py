from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, joinedload

from app.core.middleware import get_cliente_scope_dep, get_current_user
from app.core.scope import ClienteScope, get_current_cliente_admin_id
from app.database.connection import get_db
from app.models import (
    AberturaCaixa,
    Caixa,
    Cliente,
    Empresa,
    MaterialCategoria,
    OrdemServico,
    ProdutoCliente,
    Usuario,
    Venda,
    VendaItem,
    VendaPagamento,
)
from app.models.venda import StatusVenda

router = APIRouter(
    prefix="/negocios",
    tags=["Negócios"]
)

# Status considerados como vendas concluídas (para faturamento e indicadores)
STATUS_VENDA_LIQUIDA = (StatusVenda.CONFIRMADA.value, StatusVenda.FINALIZADA.value, StatusVenda.FINALIZADA_LEGADO.value)

# Fase 4 – performance: limite máximo de período para gráficos e relatórios (evitar consultas pesadas)
MAX_PERIODO_DIAS = 366


def _aplicar_escopo_vendas(query, scope: ClienteScope, allowed_ids: Optional[List[int]]):
    """Aplica filtro de escopo (cliente_id) na query de Venda quando must_filter."""
    if scope.must_filter_by_cliente() and allowed_ids is not None and len(allowed_ids) > 0:
        return query.filter(Venda.cliente_id.in_(allowed_ids))
    return query


def _produtos_mais_vendidos(db: Session, scope: ClienteScope, allowed_ids: Optional[List[int]],
                            data_inicio: date, data_fim: date, limite: int = 10) -> List[Dict[str, Any]]:
    """Top produtos por quantidade vendida no período (escopo aplicado). Usa apenas ProdutoCliente."""
    q = (
        db.query(
            func.max(ProdutoCliente.nome).label("nome"),
            func.sum(VendaItem.quantidade).label("quantidade"),
            func.sum(VendaItem.valor_total).label("valor_total"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .outerjoin(ProdutoCliente, ProdutoCliente.id == VendaItem.produto_cliente_id)
        .filter(
            func.date(Venda.data_venda) >= data_inicio,
            func.date(Venda.data_venda) <= data_fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if scope.must_filter_by_cliente() and allowed_ids:
        q = q.filter(Venda.cliente_id.in_(allowed_ids))
    q = q.group_by(VendaItem.produto_cliente_id)
    q = q.order_by(func.sum(VendaItem.quantidade).desc()).limit(limite)
    rows = q.all()
    return [
        {"nome": (r.nome or "Produto"), "quantidade": float(r.quantidade or 0), "valor_total": float(r.valor_total or 0)}
        for r in rows
    ]


def _mapear_vendas_recentes(rows: List[tuple]) -> List[Dict[str, Any]]:
    vendas: List[Dict[str, Any]] = []
    for row in rows:
        vendas.append({
            "id": row.id,
            "numero_venda": row.numero_venda,
            "data_venda": row.data_venda.isoformat() if row.data_venda else None,
            "status": row.status,
            "total": float(row.total) if row.total is not None else 0.0,
            "cliente_nome": row.cliente_nome or "Cliente não informado"
        })
    return vendas


def _mapear_os_recentes(rows: List[tuple]) -> List[Dict[str, Any]]:
    ordens: List[Dict[str, Any]] = []
    for row in rows:
        ordens.append({
            "id": row.id,
            "codigo": row.codigo,
            "status": row.status,
            "data_abertura": row.data_abertura.isoformat() if row.data_abertura else None,
            "cliente_nome": row.cliente_nome or "Cliente não informado"
        })
    return ordens


@router.get("/dashboard", response_model=dict)
async def obter_dashboard_negocios(
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna dados do dashboard de negócios conforme o perfil do usuário.
    Inclui: vendas (total, faturamento, ticket médio, pendentes, itens_por_venda_media,
    itens_por_venda_hoje, cancelamentos_30d, taxa_cancelamento), produtos_mais_vendidos,
    estoque, ordens_servico."""
    must_filter = scope.must_filter_by_cliente()
    allowed_ids = scope.allowed_ids if must_filter else None
    role_nome = current_user.role.nome if current_user.role else None
    get_current_cliente_admin_id(db, current_user.id, role_nome)

    vendas_query = db.query(
        func.count(Venda.id).label("total_vendas"),
        func.coalesce(func.sum(Venda.total), 0).label("valor_total_vendas"),
        func.coalesce(
            func.sum(
                case(
                    (Venda.status == StatusVenda.PENDENTE.value, 1),
                    else_=0
                )
            ),
            0
        ).label("vendas_pendentes")
    )
    if must_filter:
        if not allowed_ids:
            return {
                "vendas": {
                    "total_vendas": 0, "valor_total_vendas": 0.0, "vendas_pendentes": 0, "ticket_medio": 0.0,
                    "recentes": [], "itens_por_venda_media": 0.0, "itens_por_venda_hoje": 0.0,
                    "cancelamentos_30d": 0, "taxa_cancelamento": 0.0,
                },
                "produtos_mais_vendidos": {"dia": [], "semana": [], "mes": []},
                "estoque": None,
                "ordens_servico": {"total": 0, "por_status": {"aberta": 0, "em_andamento": 0, "aguardando_material": 0, "aguardando_cliente": 0, "concluida": 0, "cancelada": 0}, "recentes": []},
            }
        vendas_query = vendas_query.filter(Venda.cliente_id.in_(allowed_ids))

    vendas_stats = vendas_query.one()
    total_vendas = int(vendas_stats.total_vendas or 0)
    valor_total_vendas = float(vendas_stats.valor_total_vendas or 0)
    vendas_pendentes = int(vendas_stats.vendas_pendentes or 0)
    ticket_medio = (valor_total_vendas / total_vendas) if total_vendas else 0.0

    # Fase 4: indicadores do dia (faturamento, vendas, clientes atendidos, ticket médio)
    hoje = date.today()
    q_hoje = db.query(
        func.count(Venda.id).label("vendas_hoje"),
        func.coalesce(func.sum(Venda.total), 0).label("faturamento_hoje"),
        func.count(func.distinct(Venda.cliente_id)).label("clientes_atendidos_hoje"),
    ).filter(
        func.date(Venda.data_venda) == hoje,
        Venda.status.in_(STATUS_VENDA_LIQUIDA),
    )
    if must_filter and allowed_ids:
        q_hoje = q_hoje.filter(Venda.cliente_id.in_(allowed_ids))
    row_hoje = q_hoje.one()
    vendas_hoje = int(row_hoje.vendas_hoje or 0)
    faturamento_hoje = float(row_hoje.faturamento_hoje or 0)
    clientes_atendidos_hoje = int(row_hoje.clientes_atendidos_hoje or 0)
    ticket_medio_hoje = (faturamento_hoje / vendas_hoje) if vendas_hoje else 0.0

    # Produtos por venda (média de itens por transação) - PDV benchmark
    delta_30d = hoje - timedelta(days=30)
    q_itens_mes = (
        db.query(
            func.sum(VendaItem.quantidade).label("total_itens"),
            func.count(func.distinct(Venda.id)).label("total_vendas"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .filter(
            func.date(Venda.data_venda) >= delta_30d,
            func.date(Venda.data_venda) <= hoje,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if must_filter and allowed_ids:
        q_itens_mes = q_itens_mes.filter(Venda.cliente_id.in_(allowed_ids))
    row_itens_mes = q_itens_mes.one()
    total_itens_mes = float(row_itens_mes.total_itens or 0)
    vendas_mes_count = int(row_itens_mes.total_vendas or 0)
    itens_por_venda_media = (total_itens_mes / vendas_mes_count) if vendas_mes_count else 0.0

    q_itens_hoje = (
        db.query(
            func.sum(VendaItem.quantidade).label("total_itens"),
            func.count(func.distinct(Venda.id)).label("total_vendas"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .filter(
            func.date(Venda.data_venda) == hoje,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if must_filter and allowed_ids:
        q_itens_hoje = q_itens_hoje.filter(Venda.cliente_id.in_(allowed_ids))
    row_itens_hoje = q_itens_hoje.one()
    total_itens_hoje = float(row_itens_hoje.total_itens or 0)
    vendas_hoje_count = int(row_itens_hoje.total_vendas or 0)
    itens_por_venda_hoje = (total_itens_hoje / vendas_hoje_count) if vendas_hoje_count else 0.0

    # Cancelamentos (últimos 30 dias) e taxa de cancelamento
    q_cancel = (
        db.query(func.count(Venda.id).label("cancelados"))
        .filter(
            func.date(Venda.data_venda) >= delta_30d,
            func.date(Venda.data_venda) <= hoje,
            Venda.status == StatusVenda.CANCELADA.value,
        )
    )
    if must_filter and allowed_ids:
        q_cancel = q_cancel.filter(Venda.cliente_id.in_(allowed_ids))
    cancelamentos_30d = int(q_cancel.scalar() or 0)
    concluidas_30d = vendas_mes_count
    total_30d = concluidas_30d + cancelamentos_30d
    taxa_cancelamento = (cancelamentos_30d / total_30d * 100) if total_30d else 0.0

    # Produtos mais vendidos: dia, semana, mês (Fase 4)
    produtos_mais_vendidos = {}
    if must_filter and not allowed_ids:
        produtos_mais_vendidos = {"dia": [], "semana": [], "mes": []}
    else:
        produtos_mais_vendidos = {
            "dia": _produtos_mais_vendidos(db, scope, allowed_ids if must_filter else None, hoje, hoje, 10),
            "semana": _produtos_mais_vendidos(db, scope, allowed_ids if must_filter else None, hoje - timedelta(days=7), hoje, 10),
            "mes": _produtos_mais_vendidos(db, scope, allowed_ids if must_filter else None, hoje - timedelta(days=30), hoje, 10),
        }

    vendas_recentes_query = db.query(
        Venda.id,
        Venda.numero_venda,
        Venda.data_venda,
        Venda.status,
        Venda.total,
        Cliente.nome.label("cliente_nome")
    ).outerjoin(Cliente, Cliente.id == Venda.cliente_id)
    if must_filter and allowed_ids:
        vendas_recentes_query = vendas_recentes_query.filter(Venda.cliente_id.in_(allowed_ids))

    vendas_recentes = _mapear_vendas_recentes(
        vendas_recentes_query.order_by(Venda.data_venda.desc(), Venda.id.desc()).limit(5).all()
    )

    ordens_status_query = db.query(
        OrdemServico.status,
        func.count(OrdemServico.id).label("total")
    )
    if must_filter and allowed_ids:
        ordens_status_query = ordens_status_query.filter(OrdemServico.cliente_id.in_(allowed_ids))
    ordens_status_query = ordens_status_query.group_by(OrdemServico.status)
    ordens_status_rows = ordens_status_query.all()

    ordens_por_status = {
        "aberta": 0,
        "em_andamento": 0,
        "aguardando_material": 0,
        "aguardando_cliente": 0,
        "concluida": 0,
        "cancelada": 0
    }
    for status, total in ordens_status_rows:
        ordens_por_status[str(status)] = int(total or 0)

    total_ordens = sum(ordens_por_status.values())

    ordens_recentes_query = db.query(
        OrdemServico.id,
        OrdemServico.codigo,
        OrdemServico.status,
        OrdemServico.data_abertura,
        Cliente.nome.label("cliente_nome")
    ).join(Cliente, Cliente.id == OrdemServico.cliente_id)
    if must_filter and allowed_ids:
        ordens_recentes_query = ordens_recentes_query.filter(OrdemServico.cliente_id.in_(allowed_ids))

    ordens_recentes = _mapear_os_recentes(
        ordens_recentes_query.order_by(OrdemServico.data_abertura.desc(), OrdemServico.id.desc()).limit(5).all()
    )

    def _base_produtos_cliente():
        q = db.query(ProdutoCliente)
        if must_filter and allowed_ids:
            q = q.filter(ProdutoCliente.cliente_id.in_(allowed_ids))
        return q
    estoque_stats = {
        "total_produtos": _base_produtos_cliente().count(),
        "total_categorias": _base_produtos_cliente().filter(ProdutoCliente.categoria_id.isnot(None)).with_entities(ProdutoCliente.categoria_id).distinct().count(),
        "estoque_baixo": _base_produtos_cliente().filter(
            and_(
                ProdutoCliente.quantidade_atual <= ProdutoCliente.quantidade_minima,
                ProdutoCliente.controla_estoque == True
            )
        ).count(),
        "valor_total_estoque": float(_base_produtos_cliente().with_entities(func.sum(ProdutoCliente.valor_custo * ProdutoCliente.quantidade_atual)).scalar() or 0)
    }

    return {
        "vendas": {
            "total_vendas": total_vendas,
            "valor_total_vendas": valor_total_vendas,
            "vendas_pendentes": vendas_pendentes,
            "ticket_medio": ticket_medio,
            "recentes": vendas_recentes,
            "faturamento_hoje": faturamento_hoje,
            "vendas_hoje": vendas_hoje,
            "clientes_atendidos_hoje": clientes_atendidos_hoje,
            "ticket_medio_hoje": ticket_medio_hoje,
            "itens_por_venda_media": round(itens_por_venda_media, 2),
            "itens_por_venda_hoje": round(itens_por_venda_hoje, 2),
            "cancelamentos_30d": cancelamentos_30d,
            "taxa_cancelamento": round(taxa_cancelamento, 2),
        },
        "produtos_mais_vendidos": produtos_mais_vendidos,
        "estoque": estoque_stats,
        "ordens_servico": {
            "total": total_ordens,
            "por_status": ordens_por_status,
            "recentes": ordens_recentes
        }
    }


@router.get("/dashboard/graficos", response_model=dict)
async def obter_graficos_dashboard(
    data_inicio: Optional[date] = Query(None, description="Início do período"),
    data_fim: Optional[date] = Query(None, description="Fim do período"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por estabelecimento"),
    caixa_id: Optional[int] = Query(None, description="Filtrar por caixa"),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
):
    """Gráficos do dashboard: vendas por período, por forma de pagamento, por vendedor, horários de pico, por categoria. Respeita ClienteScope."""
    must_filter = scope.must_filter_by_cliente()
    allowed_ids = scope.allowed_ids if must_filter else None
    if must_filter and not allowed_ids:
        return {
            "vendas_por_periodo": [],
            "vendas_por_forma_pagamento": [],
            "vendas_por_vendedor": [],
            "horarios_pico": [],
            "vendas_por_categoria": [],
        }
    fim = data_fim or date.today()
    inicio = data_inicio or (fim - timedelta(days=30))
    if (fim - inicio).days > MAX_PERIODO_DIAS:
        inicio = fim - timedelta(days=MAX_PERIODO_DIAS)

    if cliente_id is not None and must_filter and cliente_id not in (allowed_ids or []):
        return {
            "vendas_por_periodo": [],
            "vendas_por_forma_pagamento": [],
            "vendas_por_vendedor": [],
            "horarios_pico": [],
            "vendas_por_categoria": [],
        }

    # Vendas por período (agrupado por dia)
    q_periodo = (
        db.query(
            func.date(Venda.data_venda).label("data"),
            func.count(Venda.id).label("total_vendas"),
            func.coalesce(func.sum(Venda.total), 0).label("valor"),
        )
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if must_filter and allowed_ids:
        q_periodo = q_periodo.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q_periodo = q_periodo.filter(Venda.cliente_id == cliente_id)
    if caixa_id is not None:
        q_periodo = q_periodo.join(AberturaCaixa, AberturaCaixa.id == Venda.abertura_caixa_id).filter(AberturaCaixa.caixa_id == caixa_id)
    q_periodo = q_periodo.group_by(func.date(Venda.data_venda)).order_by(func.date(Venda.data_venda))
    vendas_por_periodo = [
        {"data": str(r.data), "total_vendas": int(r.total_vendas or 0), "valor": float(r.valor or 0)}
        for r in q_periodo.all()
    ]

    # Por forma de pagamento: usar VendaPagamento (fracionamento)
    q_forma = (
        db.query(
            VendaPagamento.forma.label("forma"),
            func.count(func.distinct(Venda.id)).label("total_vendas"),
            func.coalesce(func.sum(VendaPagamento.valor), 0).label("valor"),
        )
        .join(Venda, Venda.id == VendaPagamento.venda_id)
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
            VendaPagamento.status != "estornado",
        )
    )
    if must_filter and allowed_ids:
        q_forma = q_forma.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q_forma = q_forma.filter(Venda.cliente_id == cliente_id)
    if caixa_id is not None:
        q_forma = q_forma.join(AberturaCaixa, AberturaCaixa.id == Venda.abertura_caixa_id).filter(AberturaCaixa.caixa_id == caixa_id)
    q_forma = q_forma.group_by(VendaPagamento.forma)
    vendas_por_forma = [
        {"forma": r.forma or "outros", "total_vendas": int(r.total_vendas or 0), "valor": float(r.valor or 0)}
        for r in q_forma.all()
    ]
    # Vendas sem fracionamento (só tipo_pagamento na venda)
    q_forma_v = (
        db.query(
            Venda.tipo_pagamento.label("forma"),
            func.count(Venda.id).label("total_vendas"),
            func.coalesce(func.sum(Venda.total), 0).label("valor"),
        )
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
            ~Venda.id.in_(db.query(VendaPagamento.venda_id).distinct()),
        )
    )
    if must_filter and allowed_ids:
        q_forma_v = q_forma_v.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q_forma_v = q_forma_v.filter(Venda.cliente_id == cliente_id)
    if caixa_id is not None:
        q_forma_v = q_forma_v.join(AberturaCaixa, AberturaCaixa.id == Venda.abertura_caixa_id).filter(AberturaCaixa.caixa_id == caixa_id)
    q_forma_v = q_forma_v.group_by(Venda.tipo_pagamento)
    for r in q_forma_v.all():
        if r.forma:
            vendas_por_forma.append({"forma": r.forma, "total_vendas": int(r.total_vendas or 0), "valor": float(r.valor or 0)})

    # Por vendedor
    q_vend = (
        db.query(
            Venda.vendedor_id,
            Usuario.nome.label("vendedor_nome"),
            func.count(Venda.id).label("total_vendas"),
            func.coalesce(func.sum(Venda.total), 0).label("valor"),
        )
        .outerjoin(Usuario, Usuario.id == Venda.vendedor_id)
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if must_filter and allowed_ids:
        q_vend = q_vend.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q_vend = q_vend.filter(Venda.cliente_id == cliente_id)
    if caixa_id is not None:
        q_vend = q_vend.join(AberturaCaixa, AberturaCaixa.id == Venda.abertura_caixa_id).filter(AberturaCaixa.caixa_id == caixa_id)
    q_vend = q_vend.group_by(Venda.vendedor_id, Usuario.nome)
    vendas_por_vendedor = [
        {"vendedor_id": r.vendedor_id, "vendedor_nome": r.vendedor_nome or "-", "total_vendas": int(r.total_vendas or 0), "valor": float(r.valor or 0)}
        for r in q_vend.all()
    ]

    # Horários de pico (hora do dia)
    q_hora = (
        db.query(
            func.extract("hour", Venda.data_venda).label("hora"),
            func.count(Venda.id).label("total_vendas"),
            func.coalesce(func.sum(Venda.total), 0).label("valor"),
        )
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if must_filter and allowed_ids:
        q_hora = q_hora.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q_hora = q_hora.filter(Venda.cliente_id == cliente_id)
    if caixa_id is not None:
        q_hora = q_hora.join(AberturaCaixa, AberturaCaixa.id == Venda.abertura_caixa_id).filter(AberturaCaixa.caixa_id == caixa_id)
    q_hora = q_hora.group_by(func.extract("hour", Venda.data_venda)).order_by(func.extract("hour", Venda.data_venda))
    horarios_pico = [
        {"hora": int(r.hora or 0), "total_vendas": int(r.total_vendas or 0), "valor": float(r.valor or 0)}
        for r in q_hora.all()
    ]

    # Por categoria (join MaterialCategoria; sem categoria_id usa "Outros")
    q_cat = (
        db.query(
            func.coalesce(MaterialCategoria.nome, ProdutoCliente.categoria, "Outros").label("categoria"),
            func.count(VendaItem.id).label("total_itens"),
            func.coalesce(func.sum(VendaItem.valor_total), 0).label("valor"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .join(ProdutoCliente, ProdutoCliente.id == VendaItem.produto_cliente_id)
        .outerjoin(MaterialCategoria, MaterialCategoria.id == ProdutoCliente.categoria_id)
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
            VendaItem.produto_cliente_id.isnot(None),
        )
    )
    if must_filter and allowed_ids:
        q_cat = q_cat.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q_cat = q_cat.filter(Venda.cliente_id == cliente_id)
    if caixa_id is not None:
        q_cat = q_cat.join(AberturaCaixa, AberturaCaixa.id == Venda.abertura_caixa_id).filter(AberturaCaixa.caixa_id == caixa_id)
    q_cat = q_cat.group_by(func.coalesce(MaterialCategoria.nome, ProdutoCliente.categoria, "Outros"))
    vendas_por_categoria = [
        {"categoria": r.categoria or "Outros", "total_vendas": int(r.total_itens or 0), "valor": float(r.valor or 0)}
        for r in q_cat.all()
    ]

    return {
        "vendas_por_periodo": vendas_por_periodo,
        "vendas_por_forma_pagamento": vendas_por_forma,
        "vendas_por_vendedor": vendas_por_vendedor,
        "horarios_pico": horarios_pico,
        "vendas_por_categoria": vendas_por_categoria,
    }


# ---------- Fase 4.2: Relatórios operacionais (escopo e filtros por estabelecimento/PDV) ----------


@router.get("/relatorios/fechamento-caixa", response_model=dict)
async def relatorio_fechamento_caixa(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    cliente_id: Optional[int] = Query(None),
    caixa_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
):
    """Relatório de fechamento de caixa: aberturas/fechamentos no período. Respeita ClienteScope (via PDV.cliente_id)."""
    must_filter = scope.must_filter_by_cliente()
    allowed_ids = scope.allowed_ids if must_filter else None
    if must_filter and not allowed_ids:
        return {"itens": [], "total": 0}
    fim = data_fim or date.today()
    inicio = data_inicio or (fim - timedelta(days=30))
    if (fim - inicio).days > MAX_PERIODO_DIAS:
        inicio = fim - timedelta(days=MAX_PERIODO_DIAS)
    q = (
        db.query(
            AberturaCaixa.id,
            AberturaCaixa.caixa_id,
            Caixa.identificador.label("caixa_identificador"),
            AberturaCaixa.usuario_id,
            Usuario.nome.label("operador_nome"),
            AberturaCaixa.data_abertura,
            AberturaCaixa.data_fechamento,
            AberturaCaixa.valor_inicial,
            AberturaCaixa.valor_final,
            AberturaCaixa.status,
        )
        .join(Caixa, Caixa.id == AberturaCaixa.caixa_id)
        .join(Empresa, Empresa.id == Caixa.empresa_id)
        .outerjoin(Usuario, Usuario.id == AberturaCaixa.usuario_id)
        .filter(func.date(AberturaCaixa.data_abertura) >= inicio, func.date(AberturaCaixa.data_abertura) <= fim)
    )
    if must_filter and allowed_ids:
        q = q.filter(Empresa.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q = q.filter(Empresa.cliente_id == cliente_id)
    if caixa_id is not None:
        q = q.filter(AberturaCaixa.caixa_id == caixa_id)
    q = q.order_by(AberturaCaixa.data_abertura.desc())
    rows = q.all()
    itens = [
        {
            "id": r.id,
            "caixa_id": r.caixa_id,
            "caixa_identificador": r.caixa_identificador or "-",
            "operador_nome": r.operador_nome or "-",
            "data_abertura": r.data_abertura.isoformat() if r.data_abertura else None,
            "data_fechamento": r.data_fechamento.isoformat() if r.data_fechamento else None,
            "valor_inicial": float(r.valor_inicial or 0),
            "valor_final": float(r.valor_final or 0) if r.valor_final is not None else None,
            "status": r.status,
        }
        for r in rows
    ]
    return {"itens": itens, "total": len(itens)}


@router.get("/relatorios/vendas-periodo", response_model=dict)
async def relatorio_vendas_periodo(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    cliente_id: Optional[int] = Query(None),
    caixa_id: Optional[int] = Query(None),
    vendedor_id: Optional[int] = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
):
    """Relatório de vendas por período (listagem paginada). Filtros por escopo, estabelecimento, PDV e vendedor."""
    must_filter = scope.must_filter_by_cliente()
    allowed_ids = scope.allowed_ids if must_filter else None
    if must_filter and not allowed_ids:
        return {"itens": [], "total": 0, "pagina": pagina, "por_pagina": por_pagina}
    fim = data_fim or date.today()
    inicio = data_inicio or (fim - timedelta(days=30))
    if (fim - inicio).days > MAX_PERIODO_DIAS:
        inicio = fim - timedelta(days=MAX_PERIODO_DIAS)
    q = (
        db.query(Venda)
        .options(joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa))
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if must_filter and allowed_ids:
        q = q.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q = q.filter(Venda.cliente_id == cliente_id)
    if caixa_id is not None:
        q = q.join(AberturaCaixa, AberturaCaixa.id == Venda.abertura_caixa_id).filter(AberturaCaixa.caixa_id == caixa_id)
    if vendedor_id is not None:
        q = q.filter(Venda.vendedor_id == vendedor_id)
    total = q.count()
    q = q.order_by(Venda.data_venda.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina)
    vendas = q.all()
    itens = []
    for v in vendas:
        cxo = None
        if getattr(v, "abertura_caixa", None) and getattr(v.abertura_caixa, "caixa", None):
            cxo = v.abertura_caixa.caixa
        itens.append(
            {
                "id": v.id,
                "numero_venda": v.numero_venda,
                "data_venda": v.data_venda.isoformat() if v.data_venda else None,
                "cliente_id": v.cliente_id,
                "vendedor_id": v.vendedor_id,
                "total": float(v.total or 0),
                "status": v.status,
                "caixa_id": cxo.id if cxo else None,
                "caixa_identificador": cxo.identificador if cxo else None,
            }
        )
    return {"itens": itens, "total": total, "pagina": pagina, "por_pagina": por_pagina}


@router.get("/relatorios/mais-vendidos", response_model=dict)
async def relatorio_mais_vendidos(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    cliente_id: Optional[int] = Query(None),
    limite: int = Query(50, ge=1, le=200),
    ordenar: str = Query("quantidade", description="quantidade ou valor"),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
):
    """Relatório mais vendidos: top produtos por quantidade ou faturamento no período. Escopo e filtro por estabelecimento."""
    must_filter = scope.must_filter_by_cliente()
    allowed_ids = scope.allowed_ids if must_filter else None
    if must_filter and not allowed_ids:
        return {"itens": []}
    fim = data_fim or date.today()
    inicio = data_inicio or (fim - timedelta(days=30))
    if (fim - inicio).days > MAX_PERIODO_DIAS:
        inicio = fim - timedelta(days=MAX_PERIODO_DIAS)
    if cliente_id is not None and must_filter and cliente_id not in (allowed_ids or []):
        return {"itens": []}
    ids_filtro = [cliente_id] if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])) else (allowed_ids if must_filter else None)
    q = (
        db.query(
            func.max(ProdutoCliente.nome).label("nome"),
            func.sum(VendaItem.quantidade).label("quantidade"),
            func.sum(VendaItem.valor_total).label("valor_total"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .outerjoin(ProdutoCliente, ProdutoCliente.id == VendaItem.produto_cliente_id)
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if ids_filtro:
        q = q.filter(Venda.cliente_id.in_(ids_filtro))
    q = q.group_by(VendaItem.produto_cliente_id)
    if ordenar == "valor":
        q = q.order_by(func.sum(VendaItem.valor_total).desc())
    else:
        q = q.order_by(func.sum(VendaItem.quantidade).desc())
    q = q.limit(limite)
    rows = q.all()
    itens = [
        {"nome": r.nome or "Produto", "quantidade": float(r.quantidade or 0), "valor_total": float(r.valor_total or 0)}
        for r in rows
    ]
    return {"itens": itens}


@router.get("/relatorios/custo-venda", response_model=dict)
async def relatorio_custo_venda(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    cliente_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
):
    """Relatório custo x venda: produtos com custo médio, valor venda, margem e markup no período. Por estabelecimento (escopo)."""
    must_filter = scope.must_filter_by_cliente()
    allowed_ids = scope.allowed_ids if must_filter else None
    if must_filter and not allowed_ids:
        return {"itens": []}
    fim = data_fim or date.today()
    inicio = data_inicio or (fim - timedelta(days=30))
    if (fim - inicio).days > MAX_PERIODO_DIAS:
        inicio = fim - timedelta(days=MAX_PERIODO_DIAS)
    # Agregar itens de venda com custo (ProdutoCliente): soma quantidade e valor_total; custo do produto
    q = (
        db.query(
            func.max(ProdutoCliente.nome).label("nome"),
            func.sum(VendaItem.quantidade).label("quantidade_vendida"),
            func.sum(VendaItem.valor_total).label("valor_venda_total"),
            func.max(ProdutoCliente.valor_custo).label("custo_unitario"),
            func.max(ProdutoCliente.valor_venda).label("preco_venda_unitario"),
        )
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .outerjoin(ProdutoCliente, ProdutoCliente.id == VendaItem.produto_cliente_id)
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status.in_(STATUS_VENDA_LIQUIDA),
        )
    )
    if must_filter and allowed_ids:
        q = q.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q = q.filter(Venda.cliente_id == cliente_id)
    q = q.group_by(VendaItem.produto_cliente_id)
    rows = q.all()
    itens = []
    for r in rows:
        custo_u = float(r.custo_unitario or 0)
        preco_u = float(r.preco_venda_unitario or 0)
        qtd = float(r.quantidade_vendida or 0)
        valor_venda = float(r.valor_venda_total or 0)
        custo_total = custo_u * qtd if custo_u else 0
        margem_valor = valor_venda - custo_total if custo_total else None
        margem_pct = (margem_valor / valor_venda * 100) if valor_venda and margem_valor is not None else None
        markup_pct = ((preco_u - custo_u) / custo_u * 100) if custo_u and preco_u else None
        itens.append({
            "nome": r.nome or "Produto",
            "quantidade_vendida": qtd,
            "valor_venda_total": valor_venda,
            "custo_unitario": custo_u,
            "custo_total": custo_total,
            "margem_valor": margem_valor,
            "margem_percentual": round(margem_pct, 2) if margem_pct is not None else None,
            "markup_percentual": round(markup_pct, 2) if markup_pct is not None else None,
        })
    return {"itens": itens}


@router.get("/relatorios/cancelamentos", response_model=dict)
async def relatorio_cancelamentos(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    cliente_id: Optional[int] = Query(None),
    caixa_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
):
    """Relatório de vendas canceladas no período. Escopo e filtros por estabelecimento/PDV."""
    must_filter = scope.must_filter_by_cliente()
    allowed_ids = scope.allowed_ids if must_filter else None
    if must_filter and not allowed_ids:
        return {"itens": [], "total": 0}
    fim = data_fim or date.today()
    inicio = data_inicio or (fim - timedelta(days=30))
    if (fim - inicio).days > MAX_PERIODO_DIAS:
        inicio = fim - timedelta(days=MAX_PERIODO_DIAS)
    q = (
        db.query(Venda)
        .options(joinedload(Venda.abertura_caixa).joinedload(AberturaCaixa.caixa))
        .filter(
            func.date(Venda.data_venda) >= inicio,
            func.date(Venda.data_venda) <= fim,
            Venda.status == StatusVenda.CANCELADA.value,
        )
    )
    if must_filter and allowed_ids:
        q = q.filter(Venda.cliente_id.in_(allowed_ids))
    if cliente_id is not None and (not must_filter or cliente_id in (allowed_ids or [])):
        q = q.filter(Venda.cliente_id == cliente_id)
    if caixa_id is not None:
        q = q.join(AberturaCaixa, AberturaCaixa.id == Venda.abertura_caixa_id).filter(AberturaCaixa.caixa_id == caixa_id)
    q = q.order_by(Venda.data_venda.desc())
    vendas = q.all()
    itens = []
    for v in vendas:
        cxo = None
        if getattr(v, "abertura_caixa", None) and getattr(v.abertura_caixa, "caixa", None):
            cxo = v.abertura_caixa.caixa
        itens.append(
            {
                "id": v.id,
                "numero_venda": v.numero_venda,
                "data_venda": v.data_venda.isoformat() if v.data_venda else None,
                "total": float(v.total or 0),
                "cliente_id": v.cliente_id,
                "caixa_id": cxo.id if cxo else None,
                "caixa_identificador": cxo.identificador if cxo else None,
            }
        )
    return {"itens": itens, "total": len(itens)}
