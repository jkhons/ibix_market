# PDV Ibix - API de relatórios genéricos (E-Relatórios)
# Catálogo, jobs assíncronos e download. Permissão: certificacao:relatorios:visualizar
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.middleware import get_cliente_scope_dep, get_current_user, require_permission
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models.orcamento import Orcamento
from ...models.report_job import ReportArtifact, ReportJob
from ...models.usuario import Usuario
from ...services.relatorios import REGISTRY, create_report_job, get_report
from ...worker.tasks import generate_report_task

router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"],
)


def _job_in_scope(job: ReportJob, scope: ClienteScope, user: Usuario) -> bool:
    """Verifica se o job está no escopo do usuário."""
    if user.role and user.role.nome == "Superadministrador":
        return True
    if scope.see_all:
        return True
    if job.cliente_id is None:
        return True
    return job.cliente_id in (scope.allowed_ids or [])


def _allowed_ids(scope: ClienteScope):
    if scope.is_superadmin or scope.see_all:
        return None
    return scope.allowed_ids or []


@router.get("/conversao-orcamentos")
async def relatorio_conversao_orcamentos(
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    cliente_id: int | None = Query(None),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    current_user: Usuario = Depends(get_current_user),
):
    """Relatório de conversão orçamentos → pedidos. Período e cliente_id opcionais. Taxa de conversão."""
    allowed = _allowed_ids(scope)
    q = db.query(Orcamento)
    if allowed is not None:
        q = q.filter(Orcamento.cliente_id.in_(allowed))
    if cliente_id is not None:
        if allowed is not None and cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Cliente fora do escopo")
        q = q.filter(Orcamento.cliente_id == cliente_id)
    if data_inicio is not None:
        q = q.filter(Orcamento.created_at >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim is not None:
        q = q.filter(Orcamento.created_at <= datetime.combine(data_fim, datetime.max.time()))
    total = q.count()
    convertidos = q.filter(Orcamento.convertido_em_pedido_id.isnot(None)).count()
    taxa = (convertidos / total * 100) if total else 0
    return {
        "total_orcamentos": total,
        "orcamentos_convertidos": convertidos,
        "taxa_conversao_percentual": round(taxa, 2),
        "data_inicio": str(data_inicio) if data_inicio else None,
        "data_fim": str(data_fim) if data_fim else None,
        "cliente_id": cliente_id,
    }


@router.get("/catalogo")
async def catalogo_relatorios(
    current_user: Usuario = Depends(require_permission("certificacao:relatorios:visualizar")),
):
    """Lista relatórios disponíveis (do registry em código)."""
    return [
        {
            "report_key": r.meta.report_key,
            "name": r.meta.name,
            "description": r.meta.description,
            "output_formats": r.meta.output_formats,
            "required_module": r.meta.required_module,
            "required_perm": r.meta.required_perm,
            "param_schema": r.meta.param_schema,
        }
        for r in REGISTRY.values()
    ]


@router.post("/jobs")
async def criar_job(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("certificacao:relatorios:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria um job de relatório e envia para a fila Celery."""
    report_key = payload.get("report_key")
    output_format = payload.get("output_format", "pdf")
    params = payload.get("params") or {}

    if not report_key:
        raise HTTPException(status_code=400, detail="report_key é obrigatório")

    try:
        get_report(report_key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Relatório não encontrado: {report_key}")

    # Cliente_id para escopo: usar primeiro do scope se houver
    cliente_id = scope.allowed_ids[0] if scope.allowed_ids else None

    job = create_report_job(
        db,
        user_id=current_user.id,
        report_key=report_key,
        output_format=output_format,
        params=params,
        cliente_id=cliente_id,
    )
    generate_report_task.delay(str(job.id))
    return {"job_id": str(job.id), "status": job.status}


@router.get("/jobs/{job_id}")
async def status_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("certificacao:relatorios:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna o status do job."""
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="job_id inválido")
    job = db.get(ReportJob, uid)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if not _job_in_scope(job, scope, current_user):
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "error_message": job.error_message,
    }


@router.get("/jobs/{job_id}/download")
async def download_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("certificacao:relatorios:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Faz download do artefato gerado."""
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="job_id inválido")
    job = db.get(ReportJob, uid)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if not _job_in_scope(job, scope, current_user):
        raise HTTPException(status_code=404, detail="Job não encontrado")
    art = (
        db.query(ReportArtifact)
        .filter(ReportArtifact.job_id == job.id)
        .order_by(ReportArtifact.id.desc())
        .first()
    )
    if not art:
        raise HTTPException(status_code=409, detail="Relatório ainda não está pronto")
    return FileResponse(
        path=art.storage_path,
        media_type=art.mime_type,
        filename=art.filename,
    )
