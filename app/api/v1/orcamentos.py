# PDV Ibix - API de Orçamentos (Módulo Orçamento e Pedido)
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from app.core.audit import audit_action
from app.core.document_ref import build_doc_ref, doc_ref_like_patterns, next_seq_for_year
from app.core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from app.core.scope import ClienteScope
from app.database.connection import get_db
from app.models import Orcamento, OrcamentoItem, Pedido, PedidoItem, ProdutoCliente, Usuario
from app.schemas.orcamento import (
    OrcamentoConverterOsRequest,
    OrcamentoConverterRequest,
    OrcamentoCreate,
    OrcamentoListResponse,
    OrcamentoResponse,
    OrcamentoUpdate,
)
from app.services.orcamento_conversao_service import (
    converter_orcamento_em_ordem_servico,
    converter_orcamento_em_venda_pendente,
)
from app.services.orcamento_service import expirar_orcamentos
from app.services.pdf_orcamento_pedido import gerar_pdf_orcamento
from app.services.documento_impressao_service import (
    gerar_pdf_orcamento_com_template,
    template_padrao_tenant,
)
from app.services.conversao_venda_service import tenant_id_do_vendedor

router = APIRouter(prefix="/orcamentos", tags=["Orçamentos"])


def _allowed_ids(scope: ClienteScope):
    if scope.is_superadmin:
        return None
    return scope.allowed_ids or []


def _orcamento_no_escopo(
    db: Session,
    orcamento_id: int,
    scope: ClienteScope,
    load_itens: bool = False,
    load_clientes: bool = False,
) -> Orcamento | None:
    q = db.query(Orcamento).filter(Orcamento.id == orcamento_id)
    opts = []
    if load_itens:
        opts.append(joinedload(Orcamento.itens))
    if load_clientes:
        opts.append(joinedload(Orcamento.cliente))
        opts.append(joinedload(Orcamento.destinatario))
    if opts:
        q = q.options(*opts)
    o = q.first()
    if not o:
        return None
    allowed = _allowed_ids(scope)
    if allowed is not None and o.cliente_id not in allowed:
        return None
    return o


def _proximo_numero_orcamento(db: Session, cliente_id: int) -> str:
    ano = datetime.now().year
    patterns = doc_ref_like_patterns("ORC", ano)
    rows = (
        db.query(Orcamento.numero_orcamento)
        .filter(
            Orcamento.cliente_id == cliente_id,
            or_(*[Orcamento.numero_orcamento.like(p) for p in patterns]),
        )
        .all()
    )
    seq = next_seq_for_year((r[0] for r in rows), ano, prefix="ORC")
    return build_doc_ref("ORC", seq, ano)


@router.get("", response_model=dict)
async def listar_orcamentos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: str | None = Query(None),
    cliente_id: int | None = Query(None),
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista orçamentos com paginação. Filtro por status e cliente_id (estabelecimento)."""
    q = db.query(Orcamento)
    allowed = _allowed_ids(scope)
    if allowed is not None:
        q = q.filter(Orcamento.cliente_id.in_(allowed))
    if status:
        q = q.filter(Orcamento.status == status)
    if cliente_id is not None:
        if allowed is not None and cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Cliente fora do escopo")
        q = q.filter(Orcamento.cliente_id == cliente_id)
    total = q.count()
    rows = (
        q.options(
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.destinatario),
            joinedload(Orcamento.vendedor),
            joinedload(Orcamento.itens),
        )
        .order_by(desc(Orcamento.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    itens = []
    for r in rows:
        base = OrcamentoListResponse.model_validate(r)
        vendedor_nome = r.vendedor.nome if getattr(r, "vendedor", None) else None
        qtd = len(r.itens) if r.itens else 0
        itens.append(
            base.model_copy(
                update={
                    "cliente_nome": (r.cliente.nome if r.cliente else None),
                    "destinatario_nome": (r.destinatario.nome if r.destinatario else None),
                    "vendedor_nome": vendedor_nome,
                    "qtd_itens": qtd,
                    "observacoes": r.observacoes,
                    "condicoes_pagamento": r.condicoes_pagamento,
                    "subtotal": r.subtotal,
                    "desconto": r.desconto,
                }
            )
        )
    return {"orcamentos": itens, "total": total, "skip": skip, "limit": limit}


@router.get("/{orcamento_id}", response_model=OrcamentoResponse)
async def obter_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Detalhe de um orçamento."""
    o = (
        db.query(Orcamento)
        .options(
            joinedload(Orcamento.itens),
            joinedload(Orcamento.cliente),
            joinedload(Orcamento.destinatario),
            joinedload(Orcamento.vendedor),
        )
        .filter(Orcamento.id == orcamento_id)
        .first()
    )
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    allowed = _allowed_ids(scope)
    if allowed is not None and o.cliente_id not in allowed:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    base = OrcamentoResponse.model_validate(o)
    return base.model_copy(
        update={
            "cliente_nome": (o.cliente.nome if o.cliente else None),
            "destinatario_nome": (o.destinatario.nome if o.destinatario else None),
            "vendedor_nome": (o.vendedor.nome if o.vendedor else None),
            "qtd_itens": len(o.itens) if o.itens else 0,
        }
    )


@router.post("", response_model=OrcamentoResponse, status_code=status.HTTP_201_CREATED)
async def criar_orcamento(
    body: OrcamentoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria orçamento em rascunho."""
    allowed = _allowed_ids(scope)
    if allowed is not None and body.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Cliente fora do escopo")
    numero = _proximo_numero_orcamento(db, body.cliente_id)
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
            "observacao_item": item.observacao_item,
        })
    total = subtotal
    orc = Orcamento(
        cliente_id=body.cliente_id,
        vendedor_id=current_user.id,
        destinatario_id=body.destinatario_id,
        numero_orcamento=numero,
        data_validade=body.data_validade,
        status="rascunho",
        subtotal=subtotal,
        desconto=Decimal("0"),
        acrescimo=Decimal("0"),
        total=total,
        observacoes=body.observacoes,
        condicoes_pagamento=body.condicoes_pagamento,
    )
    db.add(orc)
    db.flush()
    for i in itens_orm:
        db.add(OrcamentoItem(
            orcamento_id=orc.id,
            produto_cliente_id=i["produto_cliente_id"],
            codigo_produto=i["codigo_produto"],
            descricao_produto=i["descricao_produto"],
            quantidade=i["quantidade"],
            preco_unitario=i["preco_unitario"],
            desconto_percentual=i.get("desconto_percentual"),
            desconto_valor=i.get("desconto_valor"),
            total_item=i["total_item"],
            observacao_item=i.get("observacao_item"),
        ))
    db.commit()
    db.refresh(orc)
    return OrcamentoResponse.model_validate(orc)


@router.put("/{orcamento_id}", response_model=OrcamentoResponse)
async def atualizar_orcamento(
    orcamento_id: int,
    body: OrcamentoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza orçamento apenas se estiver em rascunho."""
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=True)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if o.status != "rascunho":
        raise HTTPException(status_code=400, detail="Só orçamento em rascunho pode ser editado")
    if body.destinatario_id is not None:
        o.destinatario_id = body.destinatario_id
    if body.data_validade is not None:
        o.data_validade = body.data_validade
    if body.observacoes is not None:
        o.observacoes = body.observacoes
    if body.condicoes_pagamento is not None:
        o.condicoes_pagamento = body.condicoes_pagamento
    if body.itens is not None:
        for existing in o.itens[:]:
            db.delete(existing)
        subtotal = Decimal("0")
        for item in body.itens:
            pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == item.produto_cliente_id).first()
            if not pc:
                raise HTTPException(status_code=404, detail=f"Produto {item.produto_cliente_id} não encontrado")
            if pc.cliente_id != o.cliente_id:
                raise HTTPException(status_code=400, detail="Produto não pertence ao estabelecimento")
            total_item = Decimal(str(item.quantidade * item.preco_unitario))
            if item.desconto_valor:
                total_item -= Decimal(str(item.desconto_valor))
            elif item.desconto_percentual:
                total_item -= total_item * Decimal(str(item.desconto_percentual)) / Decimal("100")
            subtotal += total_item
            db.add(
                OrcamentoItem(
                    orcamento_id=o.id,
                    produto_cliente_id=item.produto_cliente_id,
                    codigo_produto=pc.codigo,
                    descricao_produto=pc.nome,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    desconto_percentual=item.desconto_percentual,
                    desconto_valor=item.desconto_valor,
                    total_item=total_item,
                    observacao_item=item.observacao_item,
                )
            )
        o.subtotal = subtotal
        o.total = subtotal
    db.commit()
    db.refresh(o)
    return OrcamentoResponse.model_validate(o)


@router.delete("/{orcamento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Exclui orçamento apenas se estiver em rascunho."""
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=False)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if o.status != "rascunho":
        raise HTTPException(status_code=400, detail="Só orçamento em rascunho pode ser excluído")
    db.delete(o)
    db.commit()
    return None


@router.post("/{orcamento_id}/emitir", response_model=OrcamentoResponse)
async def emitir_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Altera status de rascunho para emitido."""
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=True)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if o.status != "rascunho":
        raise HTTPException(status_code=400, detail="Só orçamento em rascunho pode ser emitido")
    o.status = "emitido"
    db.commit()
    db.refresh(o)
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=True, load_clientes=True)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    base = OrcamentoResponse.model_validate(o)
    return base.model_copy(
        update={
            "cliente_nome": (o.cliente.nome if o.cliente else None),
            "destinatario_nome": (o.destinatario.nome if o.destinatario else None),
        }
    )


@router.post("/{orcamento_id}/converter", response_model=dict)
async def converter_orcamento_em_pedido(
    orcamento_id: int,
    body: OrcamentoConverterRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Converte orçamento emitido/aprovado em pedido. Opcionalmente reserva estoque."""
    from app.models import Pedido as PedidoModel
    def _proximo_numero_pedido(db: Session, cliente_id: int) -> str:
        ano = datetime.now().year
        patterns = doc_ref_like_patterns("PED", ano)
        rows = (
            db.query(PedidoModel.numero_pedido)
            .filter(
                PedidoModel.cliente_id == cliente_id,
                or_(*[PedidoModel.numero_pedido.like(p) for p in patterns]),
            )
            .all()
        )
        seq = next_seq_for_year((r[0] for r in rows), ano, prefix="PED")
        return build_doc_ref("PED", seq, ano)
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=True)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if o.status not in ("emitido", "aprovado"):
        raise HTTPException(status_code=400, detail="Só orçamento emitido ou aprovado pode ser convertido")
    if o.data_validade < date.today():
        raise HTTPException(status_code=400, detail="Orçamento expirado")
    if o.convertido_em_pedido_id or o.convertido_em_ordem_servico_id or o.convertido_em_venda_id:
        raise HTTPException(status_code=400, detail="Orçamento já convertido")
    numero_ped = _proximo_numero_pedido(db, o.cliente_id)
    ped = Pedido(
        orcamento_id=o.id,
        cliente_id=o.cliente_id,
        vendedor_id=o.vendedor_id or current_user.id,
        numero_pedido=numero_ped,
        status="liberado",
        reserva_estoque=body.reservar_estoque,
        subtotal=o.subtotal,
        desconto=o.desconto,
        acrescimo=o.acrescimo,
        total=o.total,
        observacoes=o.observacoes,
    )
    db.add(ped)
    db.flush()
    for item in o.itens:
        db.add(PedidoItem(
            pedido_id=ped.id,
            produto_cliente_id=item.produto_cliente_id,
            codigo_produto=item.codigo_produto,
            descricao_produto=item.descricao_produto,
            quantidade=item.quantidade,
            preco_unitario=item.preco_unitario,
            desconto_percentual=item.desconto_percentual,
            desconto_valor=item.desconto_valor,
            total_item=item.total_item,
            status="pendente",
        ))
    o.status = "convertido"
    o.convertido_em_pedido_id = ped.id
    o.data_conversao = datetime.utcnow()
    db.commit()
    db.refresh(ped)
    return {"message": "Orçamento convertido em pedido", "pedido_id": ped.id, "numero_pedido": ped.numero_pedido}


@router.post("/{orcamento_id}/converter-os", response_model=dict)
async def converter_orcamento_em_os(
    orcamento_id: int,
    body: OrcamentoConverterOsRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Converte orçamento emitido/aprovado em ordem de serviço. Exige consumidor (destinatário) e tipo_id."""
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=True)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if o.status not in ("emitido", "aprovado"):
        raise HTTPException(status_code=400, detail="Só orçamento emitido ou aprovado pode ser convertido")
    if o.data_validade < date.today():
        raise HTTPException(status_code=400, detail="Orçamento expirado")
    os_id, codigo = converter_orcamento_em_ordem_servico(db, o, body.tipo_id, current_user.id)
    audit_action(
        db,
        "orcamento_convertido_os",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="orcamento",
        recurso_id=orcamento_id,
        detalhes=f"ordem_servico_id={os_id} codigo={codigo}",
    )
    db.commit()
    return {"message": "Orçamento convertido em ordem de serviço", "ordem_servico_id": os_id, "codigo": codigo}


@router.post("/{orcamento_id}/converter-venda", response_model=dict)
async def converter_orcamento_em_venda_route(
    orcamento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Converte orçamento emitido/aprovado em venda pendente (sem baixa de estoque até finalização no PDV)."""
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=True)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    if o.status not in ("emitido", "aprovado"):
        raise HTTPException(status_code=400, detail="Só orçamento emitido ou aprovado pode ser convertido")
    if o.data_validade < date.today():
        raise HTTPException(status_code=400, detail="Orçamento expirado")
    vid, numero = converter_orcamento_em_venda_pendente(db, o, current_user.id)
    audit_action(
        db,
        "orcamento_convertido_venda",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="orcamento",
        recurso_id=orcamento_id,
        detalhes=f"venda_id={vid} numero={numero}",
    )
    db.commit()
    return {"message": "Orçamento convertido em venda pendente", "venda_id": vid, "numero_venda": numero}


def _dados_orcamento_para_pdf(o: Orcamento) -> dict:
    """Monta dicionário para geração de PDF do orçamento."""
    return {
        "numero_orcamento": o.numero_orcamento,
        "data_validade": o.data_validade,
        "status": o.status,
        "cliente_nome": (o.cliente.nome if o.cliente else ""),
        "destinatario_nome": (o.destinatario.nome if o.destinatario else "-"),
        "titulo_unidade": "Unidade (estabelecimento / catálogo)",
        "titulo_consumidor": "Consumidor",
        "subtotal": o.subtotal,
        "desconto": o.desconto,
        "total": o.total,
        "observacoes": o.observacoes or "",
        "condicoes_pagamento": o.condicoes_pagamento or "",
        "itens": [
            {
                "codigo_produto": i.codigo_produto,
                "descricao_produto": i.descricao_produto,
                "quantidade": i.quantidade,
                "preco_unitario": i.preco_unitario,
                "total_item": i.total_item,
            }
            for i in (o.itens or [])
        ],
    }


@router.get("/{orcamento_id}/pdf")
async def download_pdf_orcamento(
    orcamento_id: int,
    request: Request,
    db: Session = Depends(get_db),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Gera e retorna PDF do orçamento (template tenant ou fallback legado)."""
    o_full = db.query(Orcamento).options(
        joinedload(Orcamento.itens),
        joinedload(Orcamento.cliente),
        joinedload(Orcamento.destinatario),
        joinedload(Orcamento.vendedor),
    ).filter(Orcamento.id == orcamento_id).first()
    if not o_full:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    allowed = _allowed_ids(scope)
    if allowed is not None and o_full.cliente_id not in allowed:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    brand = getattr(request.state, "brand", None)
    tenant_id = tenant_id_do_vendedor(db, o_full.vendedor_id) if o_full.vendedor_id else None
    tpl = template_padrao_tenant(db, tenant_id, "orcamento") if tenant_id else None
    if tpl:
        try:
            pdf_bytes = gerar_pdf_orcamento_com_template(o_full, tpl, brand)
        except (ImportError, OSError) as e:
            raise HTTPException(status_code=503, detail=f"Geração PDF indisponível: {e}") from e
    else:
        dados = _dados_orcamento_para_pdf(o_full)
        pdf_bytes = gerar_pdf_orcamento(dados)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="orcamento-{o_full.numero_orcamento}.pdf"'})


@router.post("/expirar", response_model=dict)
async def expirar_orcamentos_route(
    cliente_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
    __: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Marca orçamentos vencidos como expirados. Opcionalmente restringe a cliente_id (estabelecimento)."""
    allowed = _allowed_ids(scope)
    if allowed is not None and cliente_id is not None and cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Cliente fora do escopo")
    n = expirar_orcamentos(db, cliente_id=cliente_id)
    return {"expirados": n}


class EnviarEmailBody(BaseModel):
    email: str
    mensagem: Optional[str] = None


@router.post("/{orcamento_id}/enviar-email", response_model=dict)
async def enviar_orcamento_email(
    orcamento_id: int,
    body: EnviarEmailBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Gera PDF do orçamento e envia por e-mail."""
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=True)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    from sqlalchemy.orm import joinedload
    o_full = db.query(Orcamento).options(
        joinedload(Orcamento.itens), joinedload(Orcamento.cliente), joinedload(Orcamento.destinatario),
    ).filter(Orcamento.id == orcamento_id).first()
    if not o_full or (scope.is_superadmin is False and scope.allowed_ids and o_full.cliente_id not in scope.allowed_ids):
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    import os
    import tempfile
    dados = _dados_orcamento_para_pdf(o_full)
    pdf_bytes = gerar_pdf_orcamento(dados)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(pdf_bytes)
    tmp.close()
    try:
        from app.services.email_service import EmailService
        svc = EmailService(db)
        body_text = body.mensagem or f"Segue em anexo o orçamento {o_full.numero_orcamento}."
        ok = svc.send_email(
            to=[body.email],
            subject=f"Orçamento {o_full.numero_orcamento}",
            body=body_text,
            attachments=[tmp.name],
            cliente_id=o_full.cliente_id,
        )
        if not ok:
            raise HTTPException(status_code=502, detail="Falha ao enviar e-mail")
        return {"message": "E-mail enviado com sucesso"}
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


class EnviarWhatsAppBody(BaseModel):
    telefone: str  # ex: 5511999999999


@router.post("/{orcamento_id}/enviar-whatsapp", response_model=dict)
async def enviar_orcamento_whatsapp(
    orcamento_id: int,
    body: EnviarWhatsAppBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Envia mensagem por WhatsApp com texto do orçamento (link para download pode ser implementado depois)."""
    o = _orcamento_no_escopo(db, orcamento_id, scope, load_itens=True)
    if not o:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    from app.services.whatsapp_service import enviar_mensagem_whatsapp
    texto = f"Orçamento {o.numero_orcamento} - Total R$ {o.total}. Acesse o sistema para visualizar ou baixar o PDF."
    result = enviar_mensagem_whatsapp(db, body.telefone, texto, current_user.id, getattr(current_user.role, "nome", None), o.cliente_id)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Falha ao enviar WhatsApp"))
    return {"message": "Mensagem enviada", "message_id": result.get("message_id")}
