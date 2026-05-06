# PDV Ibix - Criação de pedido marketplace a partir do body de checkout (reutilizável)
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    AnuncioPlataforma,
    ConsumidorMarketplace,
    LojaMarketplace,
    PedidoItemMarketplace,
    PedidoMarketplace,
    ProdutoCliente,
)
from app.schemas.marketplace import PedidoCheckoutCreate
from app.services.marketplace_frete_checkout import calcular_taxa_item_frete
from app.services.marketplace_guest_service import build_item_snapshots, emit_integration_event, generate_numero_pedido
from app.services.marketplace_cliente_crm_service import sync_cliente_crm_from_pedido_marketplace
from app.services.pedido_status_evento_service import registrar_pedido_status_evento


def criar_pedido_marketplace_checkout(
    db: Session,
    loja: LojaMarketplace,
    body: PedidoCheckoutCreate,
    comprador: ConsumidorMarketplace,
    consumidor_created: bool,
) -> PedidoMarketplace:
    """
    Persiste um PedidoMarketplace + itens + eventos (sem gateway, sem commit).
    Espera body.loja_id == loja.id e itens só dessa loja.
    """
    tenant_id = loja.cliente_id
    itens_agrupados: dict[int, int] = defaultdict(int)
    for item in body.itens:
        itens_agrupados[item.anuncio_id] += item.quantidade

    comprador_nome = (comprador.nome or body.comprador_nome or "").strip()[:200]
    comprador_email = (comprador.email or body.comprador_email or "").strip().lower()[:255]
    if not comprador_nome or not comprador_email:
        raise HTTPException(status_code=400, detail="Nome e e-mail do comprador são obrigatórios")
    comprador_telefone = body.comprador_telefone or comprador.telefone
    comprador_documento = body.comprador_documento or comprador.documento

    subtotal = Decimal("0")
    itens_validados = []
    for anuncio_id, qty in itens_agrupados.items():
        anuncio = (
            db.query(AnuncioPlataforma)
            .filter(
                AnuncioPlataforma.id == anuncio_id,
                AnuncioPlataforma.loja_id == body.loja_id,
                AnuncioPlataforma.status == "publicado",
            )
            .first()
        )
        if not anuncio:
            raise HTTPException(
                status_code=400,
                detail=f"Anúncio {anuncio_id} não encontrado ou não pertence à loja",
            )
        if anuncio.tipo_estoque == "sincronizado":
            if not anuncio.produto_ca_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Anúncio {anuncio_id} com estoque sincronizado exige produto vinculado (produto_ca_id).",
                )
            pc = (
                db.query(ProdutoCliente)
                .filter(
                    ProdutoCliente.id == anuncio.produto_ca_id,
                    ProdutoCliente.cliente_id == tenant_id,
                )
                .first()
            )
            if not pc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Produto do estabelecimento vinculado ao anúncio {anuncio_id} não encontrado.",
                )
            q_disp = float(pc.quantidade_atual or 0)
            anuncio.estoque_atual = q_disp
            if q_disp < float(qty):
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para o anúncio {anuncio_id} (disponível: {q_disp})",
                )
        preco = anuncio.preco_promocional if anuncio.preco_promocional is not None else anuncio.preco_original
        preco_total_item = Decimal(str(preco)) * qty
        subtotal += preco_total_item
        itens_validados.append((anuncio, qty, Decimal(str(preco)), preco_total_item))

    if getattr(body, "endereco_cep", None) and getattr(body, "endereco_logradouro", None):
        partes = [body.endereco_logradouro.strip()]
        if body.endereco_numero:
            partes[0] += f", {body.endereco_numero.strip()}"
        if body.endereco_complemento:
            partes.append(body.endereco_complemento.strip())
        if body.endereco_bairro:
            partes.append(body.endereco_bairro.strip())
        partes.append(f"CEP {body.endereco_cep.strip()}")
        if body.endereco_cidade:
            partes.append(f"{body.endereco_cidade.strip()}-{(body.endereco_uf or '').strip().upper()}")
        body.endereco_entrega = ", ".join(partes)

    tipo_ent = body.tipo_entrega or "retirada"
    taxa_entrega_validada = Decimal("0")
    formatos_snapshot = set()
    frete_snapshot_por_anuncio: dict[int, tuple[Decimal, str, str]] = {}
    for anuncio, qty, preco_unit, preco_total_item in itens_validados:
        taxa_item, formato_item, _origem_item = calcular_taxa_item_frete(
            db=db,
            loja=loja,
            anuncio=anuncio,
            subtotal_item=preco_total_item,
            tipo_entrega=tipo_ent,
            endereco_cidade=getattr(body, "endereco_cidade", None),
            endereco_uf=getattr(body, "endereco_uf", None),
        )
        taxa_entrega_validada += Decimal(str(taxa_item))
        formatos_snapshot.add(formato_item)
        frete_snapshot_por_anuncio[anuncio.id] = (Decimal(str(taxa_item)), formato_item, _origem_item)

    desconto_validado = Decimal("0")
    total = subtotal - desconto_validado + taxa_entrega_validada
    if total < 0:
        total = Decimal("0")

    destinatario_nome_raw = (getattr(body, "destinatario_nome", None) or "").strip()
    pedido = PedidoMarketplace(
        tenant_id=tenant_id,
        loja_id=body.loja_id,
        comprador_id=comprador.id,
        comprador_nome=comprador_nome[:200],
        comprador_email=comprador_email[:255],
        comprador_telefone=comprador_telefone[:20] if comprador_telefone else None,
        comprador_documento=comprador_documento[:20] if comprador_documento else None,
        destinatario_nome=destinatario_nome_raw[:200] if destinatario_nome_raw else None,
        numero_pedido="0-0",
        subtotal=subtotal,
        desconto=desconto_validado,
        taxa_entrega=taxa_entrega_validada,
        total=total,
        formato_frete_snapshot="item_misto"
        if len(formatos_snapshot) > 1
        else (next(iter(formatos_snapshot)) if formatos_snapshot else "sem_frete"),
        status_pedido="aguardando_pagamento",
        status_pagamento="pendente",
        status_entrega="pendente",
        endereco_entrega=body.endereco_entrega,
        tipo_entrega=tipo_ent,
        origem_pedido="checkout_guest",
        aceite_marketing_snapshot=getattr(body, "aceite_marketing", False),
        aceite_politica_privacidade_snapshot=body.aceite_politica_privacidade,
        canal_origem=getattr(body, "canal_origem", None),
        utm_source=(body.utm_source[:100] if body.utm_source else None),
        utm_medium=(body.utm_medium[:100] if body.utm_medium else None),
        utm_campaign=(body.utm_campaign[:150] if body.utm_campaign else None),
        observacoes_cliente=getattr(body, "observacoes_cliente", None),
        idempotency_key=getattr(body, "idempotency_key", None) and str(body.idempotency_key).strip() or None,
    )
    db.add(pedido)
    db.flush()
    pedido.numero_pedido = generate_numero_pedido(tenant_id, pedido.id)
    db.flush()

    for anuncio, qty, preco_unit, preco_total_item in itens_validados:
        nome_snap, cat_snap, marca_snap, sku_snap = build_item_snapshots(db, anuncio)
        taxa_item_snapshot, formato_item_snapshot, origem_item_snapshot = frete_snapshot_por_anuncio.get(
            anuncio.id, (Decimal("0"), "sem_frete", "loja")
        )
        db.add(
            PedidoItemMarketplace(
                tenant_id=tenant_id,
                pedido_id=pedido.id,
                loja_id=body.loja_id,
                anuncio_id=anuncio.id,
                produto_id=anuncio.produto_ca_id,
                quantidade=qty,
                preco_unitario=preco_unit,
                desconto_unitario=Decimal("0"),
                preco_total=preco_total_item,
                nome_produto_snapshot=nome_snap,
                categoria_snapshot=cat_snap,
                marca_snapshot=marca_snap,
                sku_snapshot=sku_snap,
                formato_frete_item_snapshot=formato_item_snapshot,
                origem_frete_item_snapshot=origem_item_snapshot,
                taxa_entrega_item=taxa_item_snapshot,
            )
        )
        db.flush()

    now = datetime.now(timezone.utc)
    if not comprador.primeira_compra_em:
        comprador.primeira_compra_em = now
    comprador.ultima_compra_em = now

    if consumidor_created:
        emit_integration_event(
            db,
            tenant_id=tenant_id,
            event_name="consumer.created",
            entity_type="consumer",
            entity_id=comprador.id,
            payload={
                "id": comprador.id,
                "email": comprador.email,
                "nome": comprador.nome,
                "tipo_consumidor": comprador.tipo_consumidor,
                "status_cadastro": comprador.status_cadastro,
                "aceite_marketing": comprador.aceite_marketing,
                "created_at": comprador.created_at.isoformat() if comprador.created_at else None,
            },
        )
    emit_integration_event(
        db,
        tenant_id=tenant_id,
        event_name="order.created",
        entity_type="order",
        entity_id=pedido.id,
        payload={
            "id": pedido.id,
            "numero_pedido": pedido.numero_pedido,
            "comprador_id": pedido.comprador_id,
            "total": float(pedido.total),
            "status_pedido": pedido.status_pedido,
            "created_at": pedido.created_at.isoformat() if pedido.created_at else None,
        },
    )
    registrar_pedido_status_evento(
        db,
        pedido_id=pedido.id,
        tipo_evento="pedido_criado",
        status_codigo="aguardando_pagamento",
        status_label="Pedido recebido",
        actor_type="sistema",
    )
    sync_cliente_crm_from_pedido_marketplace(
        db,
        loja,
        body,
        comprador_nome,
        comprador_email,
        comprador_telefone,
        comprador_documento,
        tenant_id,
    )
    return pedido


def resolve_comprador_para_loja(
    db: Session,
    loja: LojaMarketplace,
    body: PedidoCheckoutCreate,
    consumidor_sessao: Optional[ConsumidorMarketplace],
) -> Tuple[ConsumidorMarketplace, bool]:
    """Comprador para o tenant da loja: reutiliza sessão se o e-mail do body coincidir e o tenant
    da loja bater com o da sessão, ou a sessão for legada (tenant_id nulo). Caso contrário, guest.
    """
    from app.services.marketplace_guest_service import get_or_create_consumidor

    tenant_id = loja.cliente_id
    comprador_nome = body.comprador_nome.strip()
    comprador_email = body.comprador_email.strip().lower()
    if not comprador_nome or not comprador_email:
        raise HTTPException(status_code=400, detail="Nome e e-mail do comprador são obrigatórios")

    if consumidor_sessao:
        sess_email = (getattr(consumidor_sessao, "email", None) or "").strip().lower()
        if sess_email == comprador_email and (
            consumidor_sessao.tenant_id == tenant_id
            or consumidor_sessao.tenant_id is None
        ):
            return consumidor_sessao, False

    return get_or_create_consumidor(
        db,
        tenant_id=tenant_id,
        email=comprador_email,
        nome=comprador_nome,
        telefone=body.comprador_telefone,
        documento=body.comprador_documento,
        aceite_marketing=getattr(body, "aceite_marketing", False),
        canal_origem=getattr(body, "canal_origem", None),
        utm_source=getattr(body, "utm_source", None),
        utm_medium=getattr(body, "utm_medium", None),
        utm_campaign=getattr(body, "utm_campaign", None),
        is_guest=True,
    )
