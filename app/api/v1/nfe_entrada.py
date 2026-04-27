# PDV Ibix - API Entrada de Notas NFe (importação XML compras)
"""Upload de XML, listagem de documentos, conciliação de itens e confirmar e lançar no estoque."""
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import NfeDocumento, NfeItem, ProdutoCliente, Usuario
from ...schemas.nfe_entrada import (
    NfeConfirmarLancarResponse,
    NfeDocumentoResponse,
    NfeImportLoteItemResult,
    NfeImportLoteResponse,
    NfeImportResponse,
    NfeItemResponse,
    NfeItemVincularBody,
)
from ...services.fiscal.nfe_entrada_service import (
    NFE_ENTRADA_IMPORTAR_LOTE_MAX,
    calcular_custos_rateados,
    confirmar_e_lancar_estoque,
    importar_xml,
    importar_xml_lote,
    vincular_item,
)

router = APIRouter(
    prefix="/nfe-entrada",
    tags=["Entrada de Notas NFe"],
    dependencies=[Depends(forbid_cliente_access)],
)


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if not scope.must_filter_by_cliente():
        return None
    return scope.allowed_ids or []


def _ensure_cliente_in_scope(cliente_id: int, scope: ClienteScope) -> None:
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")


@router.post("/importar", response_model=NfeImportResponse, status_code=status.HTTP_201_CREATED)
async def importar_nfe_xml(
    cliente_id: int = Query(..., description="ID do estabelecimento (clientes.id)"),
    arquivo: UploadFile = File(..., description="Arquivo XML da NF-e"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Importa XML de NF-e de entrada; cria documento e itens; aplica auto-vínculo por GTIN e mapa fornecedor."""
    _ensure_cliente_in_scope(cliente_id, scope)
    content = await arquivo.read()
    if not content.strip():
        raise HTTPException(status_code=400, detail="Arquivo XML vazio")
    try:
        doc, avisos = importar_xml(db, cliente_id, content, guardar_xml=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        from ...core.logging import log_error
        log_error("Falha inesperada na importação de NF-e entrada", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Não foi possível processar o XML. Verifique se o arquivo é uma NF-e válida.",
        )
    # importar_xml já faz commit
    db.refresh(doc)
    doc_data = _documento_response_com_emitente(db, doc)
    return NfeImportResponse(documento=NfeDocumentoResponse.model_validate(doc_data), avisos=avisos)


def _documento_response_com_emitente(db: Session, doc: NfeDocumento) -> dict:
    doc = (
        db.query(NfeDocumento)
        .options(joinedload(NfeDocumento.emitente_fornecedor))
        .filter(NfeDocumento.id == doc.id)
        .first()
    )
    doc_data = NfeDocumentoResponse.model_validate(doc).model_dump()
    doc_data["emitente_nome"] = (
        (doc.emitente_razao_social or "").strip()
        or (doc.emitente_fornecedor.nome if doc and doc.emitente_fornecedor else None)
    ) or None
    return doc_data


@router.post("/importar-lote", response_model=NfeImportLoteResponse, status_code=status.HTTP_200_OK)
async def importar_nfe_xml_lote(
    cliente_id: int = Query(..., description="ID do estabelecimento (clientes.id)"),
    arquivos: List[UploadFile] = File(..., description="XMLs de NF-e (vários arquivos no mesmo campo 'arquivos')"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Importa vários XMLs em uma única requisição (evita rate limit por tenant ao importar dezenas de notas)."""
    _ensure_cliente_in_scope(cliente_id, scope)
    if not arquivos:
        raise HTTPException(status_code=400, detail="Envie pelo menos um arquivo XML.")
    if len(arquivos) > NFE_ENTRADA_IMPORTAR_LOTE_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"No máximo {NFE_ENTRADA_IMPORTAR_LOTE_MAX} arquivos por lote. Divida em mais de uma importação.",
        )
    pares: List[Tuple[str, bytes]] = []
    for up in arquivos:
        raw = await up.read()
        nome = (up.filename or "arquivo.xml").strip() or "arquivo.xml"
        pares.append((nome, raw))

    raw_resultados = importar_xml_lote(db, cliente_id, pares)
    itens: List[NfeImportLoteItemResult] = []
    ok = 0
    err = 0
    for row in raw_resultados:
        doc_data = None
        if row.get("documento"):
            doc_data = _documento_response_com_emitente(db, row["documento"])
        if row.get("sucesso"):
            ok += 1
        else:
            err += 1
        doc_model = NfeDocumentoResponse.model_validate(doc_data) if doc_data else None
        itens.append(
            NfeImportLoteItemResult(
                arquivo=row["arquivo"],
                sucesso=bool(row.get("sucesso")),
                erro=row.get("erro"),
                documento=doc_model,
                avisos=row.get("avisos") or [],
            )
        )
    return NfeImportLoteResponse(resultados=itens, total_ok=ok, total_erro=err)


@router.get("/documentos", response_model=dict)
async def listar_documentos(
    cliente_id: int = Query(..., description="ID do estabelecimento"),
    entrada_saida: Optional[str] = Query(None, description="ENTRADA, SAIDA ou omitir para listar todos"),
    status_filtro: Optional[str] = Query(None, description="IMPORTADO, CONCILIADO, etc."),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista NF-e importadas do estabelecimento. Sem entrada_saida lista todas (entrada e saída). Inclui nome do emissor."""
    _ensure_cliente_in_scope(cliente_id, scope)
    q = (
        db.query(NfeDocumento)
        .options(
            joinedload(NfeDocumento.emitente_fornecedor),
            joinedload(NfeDocumento.itens),
        )
        .filter(NfeDocumento.cliente_id == cliente_id)
    )
    if entrada_saida and str(entrada_saida).strip():
        q = q.filter(NfeDocumento.entrada_saida == str(entrada_saida).strip().upper())
    if status_filtro:
        q = q.filter(NfeDocumento.status == status_filtro)
    total = q.count()
    rows = q.order_by(NfeDocumento.emissao_em.desc().nullslast(), NfeDocumento.id.desc()).offset(skip).limit(limit).all()
    items = []
    for r in rows:
        data = NfeDocumentoResponse.model_validate(r).model_dump()
        data["emitente_nome"] = (
            (r.emitente_razao_social or "").strip()
            or (r.emitente_fornecedor.nome if r.emitente_fornecedor else None)
        ) or None
        total_itens = len(r.itens) if r.itens else 0
        itens_vinculados = sum(
            1 for i in (r.itens or []) if i.conciliar_status == "VINCULADO" and i.produto_cliente_id is not None
        )
        data["total_itens"] = total_itens
        data["itens_vinculados"] = itens_vinculados
        items.append(data)
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/documentos/{nfe_id}/itens", response_model=dict)
async def listar_itens_documento(
    nfe_id: int,
    cliente_id: int = Query(..., description="ID do estabelecimento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista itens da NF-e para conciliação."""
    _ensure_cliente_in_scope(cliente_id, scope)
    doc = db.query(NfeDocumento).filter(
        NfeDocumento.id == nfe_id,
        NfeDocumento.cliente_id == cliente_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    itens = db.query(NfeItem).filter(NfeItem.nfe_id == nfe_id).order_by(NfeItem.numero_item, NfeItem.id).all()
    return {
        "documento": NfeDocumentoResponse.model_validate(doc),
        "itens": [NfeItemResponse.model_validate(i) for i in itens],
    }


@router.patch("/itens/{nfe_item_id}/vincular", response_model=NfeItemResponse)
async def vincular_item_produto(
  nfe_item_id: int,
  body: NfeItemVincularBody,
  cliente_id: int = Query(..., description="ID do estabelecimento"),
  db: Session = Depends(get_db),
  current_user: Usuario = Depends(get_current_user),
  scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Vincula um item da NF-e a um produto interno (produtos_cliente). Atualiza o mapa produto-fornecedor."""
    _ensure_cliente_in_scope(cliente_id, scope)
    item = db.query(NfeItem).filter(NfeItem.id == nfe_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    doc = db.query(NfeDocumento).filter(NfeDocumento.id == item.nfe_id).first()
    if not doc or doc.cliente_id != cliente_id:
        raise HTTPException(status_code=404, detail="Nota não encontrada ou de outro estabelecimento")
    prod = db.query(ProdutoCliente).filter(
        ProdutoCliente.id == body.produto_cliente_id,
        ProdutoCliente.cliente_id == cliente_id,
    ).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    updated = vincular_item(db, nfe_item_id, body.produto_cliente_id, nfe_documento_id=doc.id, atualizar_mapa=True)
    if not updated:
        raise HTTPException(status_code=400, detail="Não foi possível vincular o item")
    db.commit()
    db.refresh(updated)
    return NfeItemResponse.model_validate(updated)


@router.post("/documentos/{nfe_id}/confirmar-lancar", response_model=NfeConfirmarLancarResponse)
async def confirmar_lancar_estoque(
    nfe_id: int,
    cliente_id: int = Query(..., description="ID do estabelecimento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Gera movimentações de estoque (ENTRADA) a partir dos itens vinculados e marca a nota como conciliada."""
    _ensure_cliente_in_scope(cliente_id, scope)
    doc = db.query(NfeDocumento).filter(
        NfeDocumento.id == nfe_id,
        NfeDocumento.cliente_id == cliente_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    count, erros = confirmar_e_lancar_estoque(db, nfe_id, usuario_id=getattr(current_user, "id", None))
    if erros:
        raise HTTPException(status_code=400, detail="; ".join(erros))
    return NfeConfirmarLancarResponse(movimentacoes_criadas=count)


@router.get("/documentos/{nfe_id}/custos", response_model=List[dict])
async def obter_custos_rateados(
    nfe_id: int,
    cliente_id: int = Query(..., description="ID do estabelecimento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna o custo rateado por item (para conferência antes de confirmar e lançar)."""
    _ensure_cliente_in_scope(cliente_id, scope)
    doc = db.query(NfeDocumento).filter(
        NfeDocumento.id == nfe_id,
        NfeDocumento.cliente_id == cliente_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    return calcular_custos_rateados(db, nfe_id)
