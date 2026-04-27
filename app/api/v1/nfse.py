# PDV Ibix - API NFS-e (módulo faturamento)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.billing import _ensure_ca_tenant_and_subscription
from app.core.middleware import AuthMiddleware
from app.core.scope import get_cliente_ids_for_tenant
from app.database.connection import get_db
from app.models import Cliente, Empresa, OrdemServico, SubscriptionBilling, Tenant, Usuario
from app.models.nfse import NfseInvoice
from app.schemas.nfse import (
    NfseCancelRequest,
    NfseInvoiceResponse,
    NfseIssueRequest,
    TenantNfseConfigResponse,
    TenantNfseConfigUpdate,
)
from app.services.nfse import criar_invoice_from_os, criar_invoice_from_subscription
from app.worker.nfse_tasks import job_cancel_nfse, job_issue_nfse

router = APIRouter(prefix="/nfse", tags=["NFS-e"])


def _tenant_id_from_user(user: Usuario) -> Optional[int]:
    return getattr(user, "tenant_id", None)


def _to_response(inv: NfseInvoice) -> NfseInvoiceResponse:
    return NfseInvoiceResponse(
        id=inv.id,
        tenant_id=inv.tenant_id,
        empresa_id=inv.empresa_id,
        cliente_id=inv.cliente_id,
        origin_type=inv.origin_type,
        origin_id=inv.origin_id,
        status=inv.status,
        numero_nfse=inv.numero_nfse,
        codigo_verificacao=inv.codigo_verificacao,
        url_consulta=inv.url_consulta,
        data_emissao=inv.data_emissao,
        valor_servicos=inv.valor_servicos,
        valor_iss=inv.valor_iss,
        last_error_code=inv.last_error_code,
        last_error_msg=inv.last_error_msg,
        created_at=inv.created_at,
    )


@router.get("/invoices", response_model=dict)
def listar_invoices(
    status_filter: Optional[str] = Query(None, alias="status", description="DRAFT, QUEUED, SENT, AUTHORIZED, REJECTED, CANCELED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Lista NFS-e do tenant do usuário (escopo por tenant_id)."""
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")
    q = db.query(NfseInvoice).filter(NfseInvoice.tenant_id == tenant_id)
    if status_filter:
        q = q.filter(NfseInvoice.status == status_filter)
    total = q.count()
    rows = q.order_by(NfseInvoice.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [_to_response(r) for r in rows], "total": total, "skip": skip, "limit": limit}


@router.post("/from-subscription/{subscription_id}", response_model=NfseInvoiceResponse)
def criar_e_enfileirar_from_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """
    Cria NfseInvoice a partir da subscription (usa default_empresa e ca_cliente do tenant)
    e enfileira emissão. Idempotente por (tenant_id, SUBSCRIPTION, subscription_id).
    """
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")

    sub = db.query(SubscriptionBilling).filter(
        SubscriptionBilling.id == subscription_id,
        SubscriptionBilling.tenant_id == tenant_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription não encontrada")

    tenant = db.get(Tenant, tenant_id)
    if not tenant or not getattr(tenant, "default_empresa_id", None) or not getattr(tenant, "ca_cliente_id", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure empresa emissora padrão e cliente CA no tenant.",
        )

    from datetime import date

    inv = criar_invoice_from_subscription(
        db=db,
        subscription_id=subscription_id,
        tenant_id=tenant_id,
        empresa_id=tenant.default_empresa_id,
        cliente_id=tenant.ca_cliente_id,
        data_competencia=date.today(),
        descricao_servico="Mensalidade PDV Ibix",
        valor_servicos=float(sub.valor_mensal_centavos or 0) / 100.0,
        aliquota_iss=0,
    )
    if not inv:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Falha ao criar invoice (validação)")
    db.commit()
    job_issue_nfse.delay(inv.id)
    return _to_response(inv)


@router.post("/from-os/{ordem_servico_id}", response_model=NfseInvoiceResponse)
def criar_e_enfileirar_from_os(
    ordem_servico_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """
    Cria NfseInvoice a partir da OS (usa empresa_id da OS ou tenant.default_empresa_id)
    e enfileira emissão. Idempotente por (tenant_id, OS, ordem_servico_id).
    """
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")

    os_obj = db.query(OrdemServico).filter(OrdemServico.id == ordem_servico_id).first()
    if not os_obj or os_obj.cliente_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de serviço não encontrada")

    tenant = db.get(Tenant, tenant_id)
    empresa_id = getattr(os_obj, "empresa_id", None) or (getattr(tenant, "default_empresa_id", None) if tenant else None)
    if not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure empresa emissora na OS ou no tenant.",
        )
    emp = db.get(Empresa, empresa_id)
    if not emp or emp.municipio_ibge is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empresa sem código IBGE do município.",
        )

    from datetime import date
    from decimal import Decimal
    total_os = sum(
        (getattr(i, "valor_total", None) or Decimal("0")) for i in (os_obj.itens or [])
    )
    inv = criar_invoice_from_os(
        db=db,
        ordem_servico_id=ordem_servico_id,
        tenant_id=tenant_id,
        empresa_id=empresa_id,
        cliente_id=os_obj.cliente_id,
        data_competencia=date.today(),
        descricao_servico=f"Serviço OS {os_obj.codigo}",
        valor_servicos=float(total_os),
        aliquota_iss=0,
        municipio_prestacao_ibge=emp.municipio_ibge,
    )
    if not inv:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Falha ao criar invoice (validação)")
    db.commit()
    job_issue_nfse.delay(inv.id)
    return _to_response(inv)


@router.post("/issue", response_model=dict)
def enfileirar_emissao(
    body: NfseIssueRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Enfileira job de emissão para um invoice existente (tenant scoped)."""
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")
    inv = db.get(NfseInvoice, body.invoice_id)
    if not inv or inv.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice não encontrado")
    if inv.status not in ("DRAFT", "QUEUED", "REJECTED"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice não pode ser reenviado")
    inv.status = "QUEUED"
    db.commit()
    job_issue_nfse.delay(inv.id)
    return {"invoice_id": inv.id, "status": "queued"}


@router.get("/pendencias", response_model=dict)
def listar_pendencias(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Lista NFS-e em fila ou rejeitadas (pendências fiscais) do tenant."""
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")
    q = db.query(NfseInvoice).filter(
        NfseInvoice.tenant_id == tenant_id,
        NfseInvoice.status.in_(("QUEUED", "REJECTED")),
    )
    items = q.order_by(NfseInvoice.created_at.desc()).limit(100).all()
    return {"items": [_to_response(i) for i in items], "total": len(items)}


@router.post("/cancel", response_model=dict)
def enfileirar_cancelamento(
    body: NfseCancelRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Enfileira cancelamento (apenas AUTHORIZED)."""
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")
    inv = db.get(NfseInvoice, body.invoice_id)
    if not inv or inv.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice não encontrado")
    job_cancel_nfse.delay(inv.id, body.reason)
    return {"invoice_id": inv.id, "status": "cancel_queued"}


# ---------- Config fiscal CA (default_empresa, ca_cliente) ----------


@router.get("/tenant-config", response_model=TenantNfseConfigResponse)
def get_tenant_nfse_config(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Retorna config NFS-e do tenant (default_empresa_id, ca_cliente_id) e listas de empresas/clientes do escopo para selects."""
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        tenant_id = _ensure_ca_tenant_and_subscription(db, current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")
    cliente_ids = get_cliente_ids_for_tenant(db, tenant_id)
    empresas = []
    if cliente_ids:
        for e in db.query(Empresa).filter(Empresa.cliente_id.in_(cliente_ids)).order_by(Empresa.razao_social):
            empresas.append({"id": e.id, "razao_social": e.razao_social or "", "municipio_ibge": e.municipio_ibge})
    clientes = []
    for c in db.query(Cliente).filter(Cliente.id.in_(cliente_ids)).order_by(Cliente.nome) if cliente_ids else []:
        clientes.append({"id": c.id, "nome": c.nome or "", "municipio_ibge": c.municipio_ibge})

    # Cliente CA já nasce com empresa fiscal; quando há só uma empresa e um cliente no escopo, definir automaticamente
    default_empresa_id = getattr(tenant, "default_empresa_id", None)
    ca_cliente_id = getattr(tenant, "ca_cliente_id", None)
    auto_saved = False
    if default_empresa_id is None and len(empresas) == 1:
        tenant.default_empresa_id = empresas[0]["id"]
        default_empresa_id = empresas[0]["id"]
        auto_saved = True
    if ca_cliente_id is None and len(clientes) == 1:
        tenant.ca_cliente_id = clientes[0]["id"]
        ca_cliente_id = clientes[0]["id"]
        auto_saved = True
    if auto_saved:
        db.commit()

    return TenantNfseConfigResponse(
        default_empresa_id=default_empresa_id,
        ca_cliente_id=ca_cliente_id,
        empresas=empresas,
        clientes=clientes,
    )


@router.patch("/tenant-config", response_model=dict)
def update_tenant_nfse_config(
    body: TenantNfseConfigUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Atualiza config NFS-e do tenant (apenas CA do próprio tenant)."""
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        tenant_id = _ensure_ca_tenant_and_subscription(db, current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")
    if body.default_empresa_id is not None:
        tenant.default_empresa_id = body.default_empresa_id if body.default_empresa_id else None
    if body.ca_cliente_id is not None:
        tenant.ca_cliente_id = body.ca_cliente_id if body.ca_cliente_id else None
    db.commit()
    return {"default_empresa_id": tenant.default_empresa_id, "ca_cliente_id": tenant.ca_cliente_id}


# ---------- Assistente IBGE (cidade + UF → municipio_ibge) ----------


@router.get("/ibge-assist", response_model=List[dict])
def ibge_assist(
    uf: str = Query(..., min_length=2, max_length=2),
    cidade: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Assistente IBGE: retorna municípios da UF (e opcionalmente filtra por nome). Código IBGE = id do município na API IBGE."""
    import httpx
    uf_upper = uf.upper().strip()
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_upper}/municipios"
            )
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []
    out = []
    cidade_lower = (cidade or "").strip().lower()
    for m in data:
        nome = (m.get("nome") or "")
        if cidade_lower and cidade_lower not in nome.lower():
            continue
        out.append({"codigo_ibge": m.get("id"), "nome": nome, "uf": uf_upper})
    return out[:100]
