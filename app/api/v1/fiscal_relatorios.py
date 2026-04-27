# PDV Ibix - API de relatórios fiscais (área do contador)
import csv
import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import get_cliente_scope_dep, require_permission
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models.empresa import Empresa
from ...models.nota_fiscal import NotaFiscal
from ...models.nota_servico import NotaServico
from ...models.usuario import Usuario

router = APIRouter(
    prefix="/fiscal/relatorios",
    tags=["Fiscal - Relatórios"],
)


def _filter_by_scope_nf(query, scope: ClienteScope):
    if scope.must_filter_by_cliente() and scope.allowed_ids:
        query = query.join(Empresa).filter(Empresa.cliente_id.in_(scope.allowed_ids))
    return query


def _filter_by_scope_ns(query, scope: ClienteScope):
    if scope.must_filter_by_cliente() and scope.allowed_ids:
        query = query.join(Empresa).filter(Empresa.cliente_id.in_(scope.allowed_ids))
    return query


@router.get("/notas-emitidas")
async def relatorio_notas_emitidas(
    data_inicio: Optional[date] = Query(None, description="Data inicial"),
    data_fim: Optional[date] = Query(None, description="Data final"),
    formato: str = Query("csv", description="Formato: csv ou excel"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("fiscal:exportar_relatorios")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Exporta notas emitidas no período (NF-e, NFC-e e NFS-e). Exige fiscal:exportar_relatorios."""
    if formato not in ("csv", "excel"):
        formato = "csv"
    q_nf = db.query(NotaFiscal).options(joinedload(NotaFiscal.empresa))
    q_nf = _filter_by_scope_nf(q_nf, scope)
    if data_inicio:
        q_nf = q_nf.filter(NotaFiscal.data_emissao >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim:
        q_nf = q_nf.filter(NotaFiscal.data_emissao <= datetime.combine(data_fim, datetime.max.time()))
    notas_fiscais = q_nf.filter(NotaFiscal.status.in_(["autorizado", "pendente", "rascunho", "enviada"])).order_by(NotaFiscal.data_emissao.desc()).all()

    q_ns = db.query(NotaServico).options(joinedload(NotaServico.empresa))
    q_ns = _filter_by_scope_ns(q_ns, scope)
    if data_inicio:
        q_ns = q_ns.filter(NotaServico.data_emissao >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim:
        q_ns = q_ns.filter(NotaServico.data_emissao <= datetime.combine(data_fim, datetime.max.time()))
    notas_servico = q_ns.filter(NotaServico.status.in_(["autorizado", "pendente", "rascunho", "enviada"])).order_by(NotaServico.data_emissao.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["tipo", "id", "numero", "data_emissao", "valor_total", "status", "empresa_id", "cliente_id"])
    for n in notas_fiscais:
        writer.writerow([
            "NF-e" if getattr(n, "tipo", None) and str(getattr(n.tipo, "value", "")).upper() == "NFE" else "NFC-e",
            n.id,
            n.numero,
            n.data_emissao.isoformat() if n.data_emissao else "",
            str(n.valor_total) if n.valor_total else "",
            str(getattr(n.status, "value", n.status)) if hasattr(n.status, "value") else str(n.status),
            n.empresa_id,
            n.cliente_id or "",
        ])
    for n in notas_servico:
        writer.writerow([
            "NFS-e",
            n.id,
            n.numero,
            n.data_emissao.isoformat() if n.data_emissao else "",
            str(n.valor_total) if n.valor_total else "",
            str(getattr(n.status, "value", n.status)) if hasattr(n.status, "value") else str(n.status),
            n.empresa_id,
            n.cliente_id or "",
        ])
    output.seek(0)
    if formato == "excel":
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=notas_emitidas.csv"},
        )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=notas_emitidas.csv"},
    )


@router.get("/resumo-periodo")
async def relatorio_resumo_periodo(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("fiscal:exportar_relatorios")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Resumo de quantidade e valor por tipo (NFS-e, NF-e, NFC-e) no período."""
    q_nf = db.query(func.count(NotaFiscal.id).label("qtd"), func.coalesce(func.sum(NotaFiscal.valor_total), 0).label("total")).join(Empresa)
    q_nf = _filter_by_scope_nf(q_nf, scope)
    if data_inicio:
        q_nf = q_nf.filter(NotaFiscal.data_emissao >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim:
        q_nf = q_nf.filter(NotaFiscal.data_emissao <= datetime.combine(data_fim, datetime.max.time()))
    q_nf = q_nf.filter(NotaFiscal.status == "autorizado")
    row_nf = q_nf.first()
    q_ns = db.query(func.count(NotaServico.id).label("qtd"), func.coalesce(func.sum(NotaServico.valor_total), 0).label("total")).join(Empresa)
    q_ns = _filter_by_scope_ns(q_ns, scope)
    if data_inicio:
        q_ns = q_ns.filter(NotaServico.data_emissao >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim:
        q_ns = q_ns.filter(NotaServico.data_emissao <= datetime.combine(data_fim, datetime.max.time()))
    q_ns = q_ns.filter(NotaServico.status == "autorizado")
    row_ns = q_ns.first()
    return {
        "periodo": {"data_inicio": str(data_inicio) if data_inicio else None, "data_fim": str(data_fim) if data_fim else None},
        "nf_e_nfce": {"quantidade": row_nf.qtd or 0, "valor_total": float(row_nf.total or 0)},
        "nfse": {"quantidade": row_ns.qtd or 0, "valor_total": float(row_ns.total or 0)},
    }
