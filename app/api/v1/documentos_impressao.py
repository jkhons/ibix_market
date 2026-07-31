from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.core.middleware import forbid_cliente_access, get_current_user
from app.database.connection import get_db
from app.models.documento_impressao_template import DocumentoImpressaoTemplate
from app.models.usuario import Usuario
from app.schemas.documento_impressao import (
    DocumentoImpressaoPreviewRequest,
    DocumentoImpressaoTemplateCreate,
    DocumentoImpressaoTemplateList,
    DocumentoImpressaoTemplateResponse,
    DocumentoImpressaoTemplateUpdate,
)
from app.services.documento_impressao_service import (
    contexto_mock,
    gerar_pdf_bytes,
    renderizar_html,
)

router = APIRouter(prefix="/documentos-impressao", tags=["Documentos de Impressão"])


def _tenant_id(user: Usuario) -> int:
    tid = getattr(user, "tenant_id", None)
    if tid is None:
        raise HTTPException(status_code=403, detail="Tenant não identificado")
    return tid


def _get_template_tenant(db: Session, template_id: int, tenant_id: int) -> DocumentoImpressaoTemplate:
    tpl = (
        db.query(DocumentoImpressaoTemplate)
        .filter(
            DocumentoImpressaoTemplate.id == template_id,
            DocumentoImpressaoTemplate.tenant_id == tenant_id,
        )
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return tpl


@router.get("/templates", response_model=DocumentoImpressaoTemplateList)
def listar_templates(
    tipo: Optional[str] = Query(None, description="orcamento | ordem_servico"),
    ativo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    tenant_id = _tenant_id(current_user)
    q = db.query(DocumentoImpressaoTemplate).filter(DocumentoImpressaoTemplate.tenant_id == tenant_id)
    if tipo:
        if tipo not in ("orcamento", "ordem_servico"):
            raise HTTPException(status_code=400, detail="tipo inválido")
        q = q.filter(DocumentoImpressaoTemplate.tipo_documento == tipo)
    if ativo is not None:
        q = q.filter(DocumentoImpressaoTemplate.ativo == ativo)
    rows = q.order_by(DocumentoImpressaoTemplate.is_padrao.desc(), DocumentoImpressaoTemplate.nome).all()
    return {"templates": rows, "total": len(rows)}


@router.get("/templates/{template_id}", response_model=DocumentoImpressaoTemplateResponse)
def obter_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    return _get_template_tenant(db, template_id, _tenant_id(current_user))


@router.post("/templates", response_model=DocumentoImpressaoTemplateResponse, status_code=201)
def criar_template(
    body: DocumentoImpressaoTemplateCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    tenant_id = _tenant_id(current_user)
    dup = (
        db.query(DocumentoImpressaoTemplate)
        .filter(
            DocumentoImpressaoTemplate.tenant_id == tenant_id,
            DocumentoImpressaoTemplate.tipo_documento == body.tipo_documento,
            DocumentoImpressaoTemplate.nome == body.nome,
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="Já existe template com este nome para o tipo")

    if body.is_padrao:
        db.query(DocumentoImpressaoTemplate).filter(
            DocumentoImpressaoTemplate.tenant_id == tenant_id,
            DocumentoImpressaoTemplate.tipo_documento == body.tipo_documento,
            DocumentoImpressaoTemplate.is_padrao.is_(True),
        ).update({"is_padrao": False})

    tpl = DocumentoImpressaoTemplate(
        tenant_id=tenant_id,
        tipo_documento=body.tipo_documento,
        nome=body.nome,
        conteudo_html=body.conteudo_html,
        css_extra=body.css_extra,
        is_padrao=body.is_padrao,
        ativo=body.ativo,
        created_by=current_user.id,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.put("/templates/{template_id}", response_model=DocumentoImpressaoTemplateResponse)
def atualizar_template(
    template_id: int,
    body: DocumentoImpressaoTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    tenant_id = _tenant_id(current_user)
    tpl = _get_template_tenant(db, template_id, tenant_id)
    data = body.model_dump(exclude_unset=True)
    if "nome" in data and data["nome"] != tpl.nome:
        dup = (
            db.query(DocumentoImpressaoTemplate)
            .filter(
                DocumentoImpressaoTemplate.tenant_id == tenant_id,
                DocumentoImpressaoTemplate.tipo_documento == tpl.tipo_documento,
                DocumentoImpressaoTemplate.nome == data["nome"],
                DocumentoImpressaoTemplate.id != tpl.id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="Já existe template com este nome para o tipo")
    if data.get("is_padrao"):
        db.query(DocumentoImpressaoTemplate).filter(
            DocumentoImpressaoTemplate.tenant_id == tenant_id,
            DocumentoImpressaoTemplate.tipo_documento == tpl.tipo_documento,
            DocumentoImpressaoTemplate.is_padrao.is_(True),
            DocumentoImpressaoTemplate.id != tpl.id,
        ).update({"is_padrao": False})
    for k, v in data.items():
        setattr(tpl, k, v)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.post("/templates/{template_id}/definir-padrao", response_model=DocumentoImpressaoTemplateResponse)
def definir_padrao(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    tenant_id = _tenant_id(current_user)
    tpl = _get_template_tenant(db, template_id, tenant_id)
    db.query(DocumentoImpressaoTemplate).filter(
        DocumentoImpressaoTemplate.tenant_id == tenant_id,
        DocumentoImpressaoTemplate.tipo_documento == tpl.tipo_documento,
        DocumentoImpressaoTemplate.is_padrao.is_(True),
    ).update({"is_padrao": False})
    tpl.is_padrao = True
    tpl.ativo = True
    db.commit()
    db.refresh(tpl)
    return tpl


@router.post("/preview")
def preview_template(
    body: DocumentoImpressaoPreviewRequest,
    request: Request,
    formato: str = Query("html", description="html | pdf"),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    brand = getattr(request.state, "brand", None)
    ctx = contexto_mock(body.tipo_documento)
    if brand:
        ctx["brand_nome"] = getattr(brand, "nome_exibicao", ctx.get("brand_nome"))
        ctx["brand_logo_url"] = getattr(brand, "logo_url", ctx.get("brand_logo_url"))
    html = renderizar_html(body.conteudo_html, ctx, body.css_extra)
    if formato == "pdf":
        try:
            pdf = gerar_pdf_bytes(html)
        except (ImportError, OSError) as e:
            raise HTTPException(status_code=503, detail=f"Geração PDF indisponível: {e}") from e
        return Response(content=pdf, media_type="application/pdf")
    return HTMLResponse(content=html)
