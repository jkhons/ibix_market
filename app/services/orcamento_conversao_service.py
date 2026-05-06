# PDV Ibix — Conversão de orçamento em OS ou venda (rastreio tenant / escopo).
from datetime import datetime
from decimal import Decimal
from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Orcamento, ProdutoCliente
from app.models.venda import StatusVenda, Venda, VendaItem
from app.schemas.ordem_servico import (
    OrdemServicoCreate,
    OrdemServicoItemCreate,
    OrdemServicoPrioridadeEnum,
    OrdemServicoStatusEnum,
)
from app.services.ordem_servico_service import OrdemServicoService
from app.services.venda_numero import gerar_numero_venda


def _ja_convertido(o: Orcamento) -> bool:
    return bool(
        o.convertido_em_pedido_id or o.convertido_em_ordem_servico_id or o.convertido_em_venda_id
    )


def converter_orcamento_em_ordem_servico(
    db: Session,
    o: Orcamento,
    tipo_id: int,
    usuario_id: int,
) -> Tuple[int, str]:
    """
    Converte orçamento emitido/aprovado em OS. Consumidor do orçamento = cliente_id da OS.
    Delega criação a OrdemServicoService.criar_ordem (commit interno).
    """
    if _ja_convertido(o):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Orçamento já convertido")
    if not o.destinatario_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o consumidor no orçamento para converter em ordem de serviço.",
        )
    if not o.itens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Orçamento sem itens não pode gerar ordem de serviço.",
        )

    itens_create: list[OrdemServicoItemCreate] = []
    for oi in o.itens:
        pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == oi.produto_cliente_id).first()
        nome = (oi.descricao_produto or (pc.nome if pc else None) or "Item").strip()[:255]
        unidade = None
        if pc and pc.unidade_medida:
            unidade = str(pc.unidade_medida).strip()[:20]
        if not unidade:
            unidade = "UN"
        q = Decimal(str(oi.quantidade))
        pu = Decimal(str(oi.preco_unitario))
        desconto = Decimal(str(oi.desconto_valor or 0))
        itens_create.append(
            OrdemServicoItemCreate(
                produto_cliente_id=oi.produto_cliente_id,
                codigo=oi.codigo_produto,
                nome=nome,
                unidade=unidade,
                quantidade=q,
                valor_unitario=pu,
                desconto=desconto,
            )
        )

    blocos = [f"Convertido do orçamento {o.numero_orcamento}."]
    if o.observacoes:
        blocos.append(str(o.observacoes).strip())
    observacoes_os = "\n\n".join(blocos)

    dados_os = OrdemServicoCreate(
        cliente_id=o.destinatario_id,
        tipo_id=tipo_id,
        prioridade=OrdemServicoPrioridadeEnum.media,
        status=OrdemServicoStatusEnum.aberta,
        observacoes=observacoes_os,
        itens=itens_create,
    )

    os_obj = OrdemServicoService.criar_ordem(db, dados_os, usuario_id)

    o2 = db.query(Orcamento).filter(Orcamento.id == o.id).first()
    if not o2:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Orçamento não encontrado após criar OS")
    o2.status = "convertido"
    o2.convertido_em_ordem_servico_id = os_obj.id
    o2.data_conversao = datetime.utcnow()
    db.commit()
    db.refresh(os_obj)
    return os_obj.id, os_obj.codigo


def converter_orcamento_em_venda_pendente(
    db: Session,
    o: Orcamento,
    usuario_id: int,
) -> Tuple[int, str]:
    """
    Cria venda em status PENDENTE a partir do orçamento, sem movimentar estoque nem exigir caixa aberto.
    """
    if _ja_convertido(o):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Orçamento já convertido")
    if not o.itens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Orçamento sem itens não pode gerar venda.",
        )

    numero = gerar_numero_venda(db)
    obs_parts = [f"Origem: orçamento {o.numero_orcamento} (conversão)."]
    if o.observacoes:
        obs_parts.append(str(o.observacoes).strip())
    observacoes = "\n\n".join(obs_parts)

    subtotal = Decimal(str(o.subtotal or 0))
    desconto = Decimal(str(o.desconto or 0))
    acrescimo = Decimal(str(o.acrescimo or 0))
    total = Decimal(str(o.total or 0))

    v = Venda(
        numero_venda=numero,
        data_venda=datetime.now(),
        status=StatusVenda.PENDENTE.value,
        cliente_id=o.destinatario_id,
        vendedor_id=usuario_id,
        subtotal=subtotal,
        desconto=desconto,
        acrescimo=acrescimo,
        total=total,
        tipo_pagamento=None,
        valor_pago=Decimal("0"),
        troco=Decimal("0"),
        observacoes=observacoes,
        abertura_caixa_id=None,
        orcamento_id=o.id,
    )
    db.add(v)
    db.flush()

    for oi in o.itens:
        db.add(
            VendaItem(
                venda_id=v.id,
                produto_cliente_id=oi.produto_cliente_id,
                quantidade=Decimal(str(oi.quantidade)),
                valor_unitario=Decimal(str(oi.preco_unitario)),
                valor_total=Decimal(str(oi.total_item)),
                desconto_item=Decimal(str(oi.desconto_valor or 0)),
                observacoes=None,
            )
        )

    o.status = "convertido"
    o.convertido_em_venda_id = v.id
    o.data_conversao = datetime.utcnow()
    db.commit()
    db.refresh(v)
    return v.id, v.numero_venda
