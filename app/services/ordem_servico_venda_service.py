"""Criação de Venda a partir de Ordem de Serviço (fluxo Enviar para vendas)."""
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.nota_servico import NotaServico
from app.models.ordem_servico import OrdemServico
from app.models.venda import StatusVenda, Venda, VendaItem
from app.services.conversao_venda_service import orcamento_raiz_da_os, registrar_origem_ordem_servico
from app.services.venda_numero import gerar_numero_venda


def criar_venda_a_partir_da_os(
    db: Session,
    ordem_id: int,
    usuario_id: int,
) -> Venda:
    """
    Cria uma Venda a partir de uma OS concluída (Enviar para vendas / Finalizar venda).
    Valida: status concluida, sem venda já vinculada, pelo menos um item na OS.
    Itens sem produto_cliente_id viram linhas de venda apenas com descrição em observacoes
    (nome/código da OS), para peças e serviços digitados na ordem.
    Vincula nota_servico (rascunho NFS-e da OS) se existir.
    """
    ordem = (
        db.query(OrdemServico)
        .options(selectinload(OrdemServico.itens))
        .filter(OrdemServico.id == ordem_id)
        .first()
    )
    if not ordem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordem de serviço não encontrada",
        )
    if ordem.status != "concluida":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A ordem de serviço deve estar com status 'concluida' para enviar para vendas.",
        )
    venda_existente = (
        db.query(Venda).filter(Venda.ordem_servico_id == ordem_id).first()
    )
    if venda_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ordem de serviço já enviada para vendas.",
        )
    itens = ordem.itens or []
    if not itens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A ordem de serviço não possui itens para enviar para vendas.",
        )

    # NFS-e rascunho vinculada à OS (criada ao concluir a OS); filtrar por ordem_servico_id e status em Python para evitar envio de enum em maiúsculo ao PostgreSQL
    notas_da_os = (
        db.query(NotaServico)
        .filter(NotaServico.ordem_servico_id == ordem_id)
        .all()
    )
    nota_servico = next(
        (n for n in notas_da_os if (getattr(n.status, "value", n.status) or "").lower() == "rascunho"),
        None,
    )
    nota_servico_id = nota_servico.id if nota_servico else None

    subtotal = sum(Decimal(str(getattr(i, "valor_total") or 0)) for i in itens)
    data_venda = datetime.now()
    numero_venda = gerar_numero_venda(db)

    header_obs = f"Pedido {numero_venda} — Origem OS {ordem.codigo}"
    corpo_os = (ordem.observacoes or "").strip()
    observacoes_venda = f"{header_obs}\n\n{corpo_os}" if corpo_os else header_obs

    orcamento_raiz = orcamento_raiz_da_os(db, ordem)
    orcamento_id_venda = orcamento_raiz.id if orcamento_raiz else None

    venda = Venda(
        numero_venda=numero_venda,
        data_venda=data_venda,
        status=StatusVenda.PENDENTE.value,
        cliente_id=ordem.cliente_id,
        vendedor_id=usuario_id,
        subtotal=subtotal,
        desconto=Decimal("0"),
        acrescimo=Decimal("0"),
        total=subtotal,
        tipo_pagamento=None,
        valor_pago=Decimal("0"),
        troco=Decimal("0"),
        observacoes=observacoes_venda,
        ordem_servico_id=ordem_id,
        orcamento_id=orcamento_id_venda,
        nota_servico_id=nota_servico_id,
    )
    db.add(venda)
    db.flush()

    for item_os in itens:
        valor_total = Decimal(str(getattr(item_os, "valor_total") or 0))
        quantidade = Decimal(str(getattr(item_os, "quantidade") or 0))
        valor_unitario = Decimal(str(getattr(item_os, "valor_unitario") or 0))
        desconto_item = Decimal(str(getattr(item_os, "desconto") or 0))
        obs_orig = getattr(item_os, "observacao", None)
        pc_id = getattr(item_os, "produto_cliente_id", None)
        if pc_id:
            obs_linha = obs_orig
        else:
            partes = []
            if getattr(item_os, "codigo", None):
                partes.append(str(item_os.codigo).strip())
            if getattr(item_os, "nome", None):
                partes.append(str(item_os.nome).strip())
            desc = " — ".join(partes) if partes else "Peça/serviço (ordem de serviço)"
            obs_linha = f"{desc} | {obs_orig}" if obs_orig else desc
        item_venda = VendaItem(
            venda_id=venda.id,
            produto_cliente_id=pc_id,
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_total=valor_total,
            desconto_item=desconto_item,
            observacoes=obs_linha,
        )
        db.add(item_venda)

    registrar_origem_ordem_servico(db, venda, ordem, usuario_id, orcamento_raiz=orcamento_raiz)
    db.commit()
    db.refresh(venda)
    venda_completa = (
        db.query(Venda)
        .options(selectinload(Venda.itens))
        .filter(Venda.id == venda.id)
        .first()
    )
    return venda_completa or venda
