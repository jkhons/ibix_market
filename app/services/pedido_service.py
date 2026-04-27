# PDV Ibix - Serviço de Pedido (Módulo Orçamento e Pedido)
"""Reserva de estoque, liberação e faturamento (parcial/total) do pedido."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Empresa,
    NotaFiscal,
    NotaFiscalItem,
    Pedido,
    PedidoFaturamento,
    PedidoHistorico,
    PedidoItem,
    ProdutoCliente,
    ReservaEstoque,
)
from app.models.nota_fiscal import OrigemDocumentoFiscalEnum, StatusNotaEnum, TipoNotaEnum


def reservar_estoque(db: Session, pedido_id: int, usuario_id: int | None = None) -> tuple[bool, str]:
    """
    Cria reservas de estoque para todos os itens do pedido (quantidade_reservada = quantidade do item).
    Verifica se há estoque disponível (quantidade_atual - reservas existentes >= quantidade).
    Atualiza pedido.reserva_estoque = True e pedido.data_reserva.
    Retorna (True, "") em sucesso, (False, "motivo") em falha.
    """
    ped = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not ped:
        return False, "Pedido não encontrado"
    if ped.status == "cancelado":
        return False, "Pedido cancelado"
    if ped.reserva_estoque:
        return False, "Pedido já possui reserva de estoque"

    # Verificar estoque disponível por produto (considerando outras reservas do mesmo produto)
    for item in ped.itens:
        pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == item.produto_cliente_id).first()
        if not pc:
            return False, f"Produto {item.produto_cliente_id} não encontrado"
        qtd_pedido = Decimal(str(item.quantidade))
        # Reservas já existentes para este produto (outros pedidos)
        outras_reservas = (
            db.query(func.coalesce(func.sum(ReservaEstoque.quantidade_reservada), 0))
            .filter(
                ReservaEstoque.produto_cliente_id == item.produto_cliente_id,
                ReservaEstoque.pedido_id != pedido_id,
            )
            .scalar()
        ) or Decimal("0")
        disponivel = (pc.quantidade_atual or Decimal("0")) - outras_reservas
        if disponivel < qtd_pedido:
            return False, f"Estoque insuficiente para produto {pc.codigo or pc.nome} (disponível: {disponivel})"

    # Criar reservas
    for item in ped.itens:
        db.add(
            ReservaEstoque(
                pedido_id=pedido_id,
                produto_cliente_id=item.produto_cliente_id,
                quantidade_reservada=item.quantidade,
            )
        )
    ped.reserva_estoque = True
    ped.data_reserva = datetime.now(timezone.utc)
    db.commit()
    return True, ""


def liberar_reserva(db: Session, pedido_id: int) -> tuple[bool, str]:
    """Remove todas as reservas de estoque do pedido e marca pedido.reserva_estoque = False."""
    ped = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not ped:
        return False, "Pedido não encontrado"
    if not ped.reserva_estoque:
        return True, ""  # já sem reserva
    db.query(ReservaEstoque).filter(ReservaEstoque.pedido_id == pedido_id).delete()
    ped.reserva_estoque = False
    ped.data_reserva = None
    db.commit()
    return True, ""


def _proximo_numero_nf(db: Session, empresa_id: int, serie: str = "1") -> str:
    """Retorna próximo número de NF para a empresa/série (simplificado)."""
    rows = db.query(NotaFiscal.numero).filter(NotaFiscal.empresa_id == empresa_id, NotaFiscal.serie == serie).all()
    nums = []
    for (n,) in rows:
        try:
            nums.append(int(str(n).strip()))
        except (ValueError, TypeError):
            pass
    return str((max(nums) + 1) if nums else 1)


def faturar_pedido(
    db: Session,
    pedido_id: int,
    itens_faturar: list[tuple[int, Decimal]],
    usuario_id: int,
) -> tuple[bool, str, int | None]:
    """
    Faturamento (parcial ou total) do pedido.
    itens_faturar: lista de (pedido_item_id, quantidade_a_faturar).
    Cria NotaFiscal (rascunho) + PedidoFaturamento, atualiza pedido_itens.quantidade_faturada e status do item.
    Retorna (True, "", nota_fiscal_id) ou (False, "motivo", None).
    """
    ped = db.query(Pedido).options(
        joinedload(Pedido.itens).joinedload(PedidoItem.produto_cliente),
    ).filter(Pedido.id == pedido_id).first()
    if not ped:
        return False, "Pedido não encontrado", None
    if ped.status == "cancelado":
        return False, "Pedido cancelado", None

    empresa = db.query(Empresa).filter(Empresa.cliente_id == ped.cliente_id).first()
    if not empresa:
        return False, "Estabelecimento não possui empresa fiscal configurada para emissão de NF", None

    # Validar itens e quantidades
    item_ids = {pi.id: pi for pi in ped.itens}
    valor_total_nf = Decimal("0")
    updates = []
    for pid, qtd in itens_faturar:
        if pid not in item_ids:
            return False, f"Item de pedido {pid} não pertence ao pedido", None
        pi = item_ids[pid]
        qtd_faturar = Decimal(str(qtd))
        restante = (pi.quantidade or Decimal("0")) - (pi.quantidade_faturada or Decimal("0"))
        if qtd_faturar <= 0 or qtd_faturar > restante:
            return False, f"Quantidade a faturar inválida para item {pi.id} (restante: {restante})", None
        total_item = (pi.total_item or Decimal("0")) * (qtd_faturar / (pi.quantidade or Decimal("1")))
        valor_total_nf += total_item
        updates.append((pi, qtd_faturar, total_item))

    # Série padrão da empresa (NF-e)
    serie = (getattr(empresa, "serie_padrao_nfe", None) or "").strip() or "1"
    numero = _proximo_numero_nf(db, empresa.id, serie)
    now = datetime.now(timezone.utc)
    # Origem do documento: orçamento, venda balcão ou manual
    if getattr(ped, "orcamento_id", None):
        origem_doc = OrigemDocumentoFiscalEnum.ORCAMENTO
    elif getattr(ped, "venda_id", None):
        origem_doc = OrigemDocumentoFiscalEnum.VENDA_BALCAO
    else:
        origem_doc = OrigemDocumentoFiscalEnum.MANUAL
    nf = NotaFiscal(
        numero=numero,
        serie=serie,
        tipo=TipoNotaEnum.NFE,
        modelo="55",
        data_emissao=now,
        empresa_id=empresa.id,
        cliente_id=ped.cliente_id,
        pedido_id=pedido_id,
        emitido_por_id=usuario_id,
        origem_documento=origem_doc,
        valor_total=valor_total_nf,
        valor_produtos=valor_total_nf,
        status=StatusNotaEnum.RASCUNHO,
    )
    db.add(nf)
    db.flush()

    item_num = 1
    for pi, qtd_faturar, total_item in updates:
        pc = getattr(pi, "produto_cliente", None)
        ncm_item = (pc and getattr(pc, "ncm", None)) and (pc.ncm or "").strip() or None
        unidade_item = (pc and getattr(pc, "unidade_medida", None)) and (pc.unidade_medida or "").strip() or "UN"
        cfop_item = (pc and getattr(pc, "cfop_padrao", None)) and (pc.cfop_padrao or "").strip() or None
        cest_item = (pc and getattr(pc, "cest", None)) and (pc.cest or "").strip() or None
        extipi_item = (pc and getattr(pc, "extipi", None)) and (pc.extipi or "").strip() or None
        origem_item = (pc and getattr(pc, "origem_mercadoria", None)) is not None and 0 <= pc.origem_mercadoria <= 8 and pc.origem_mercadoria or None
        db.add(
            NotaFiscalItem(
                nota_id=nf.id,
                produto_cliente_id=pi.produto_cliente_id,
                item_numero=item_num,
                descricao=pi.descricao_produto or "",
                codigo_produto=pi.codigo_produto,
                unidade=unidade_item[:10] if unidade_item else "UN",
                quantidade=qtd_faturar,
                valor_unitario=(pi.preco_unitario or 0),
                valor_total=total_item,
                ncm=ncm_item,
                cfop=cfop_item,
                cest=cest_item,
                extipi=extipi_item,
                origem=origem_item,
            )
        )
        item_num += 1
        pi.quantidade_faturada = (pi.quantidade_faturada or Decimal("0")) + qtd_faturar
        if pi.quantidade_faturada >= (pi.quantidade or 0):
            pi.status = "faturado"
        else:
            pi.status = "parcial"

    db.add(
        PedidoFaturamento(
            pedido_id=pedido_id,
            nota_fiscal_id=nf.id,
            data_faturamento=now,
            valor_faturado=valor_total_nf,
        )
    )

    # Atualizar status do pedido se todos os itens faturados
    status_anterior = ped.status
    todos_faturados = all((pi.quantidade_faturada or 0) >= (pi.quantidade or 0) for pi in ped.itens)
    if todos_faturados:
        ped.status = "faturado_total"
    else:
        ped.status = "faturado_parcial"

    db.add(
        PedidoHistorico(
            pedido_id=pedido_id,
            status_anterior=status_anterior,
            status_novo=ped.status,
            usuario_id=usuario_id,
            observacao="Faturamento parcial/total",
        )
    )
    db.commit()
    return True, "", nf.id
