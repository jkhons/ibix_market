# PDV Ibix - Serviço de reserva de estoque (marketplace)
"""Checkout não deduz estoque; baixa ao confirmar pagamento (committed). Release ao cancelar/expirar (fluxo legado reserved)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    AnuncioPlataforma,
    PedidoItemMarketplace,
    PedidoMarketplace,
    ProdutoCliente,
    ReservaEstoqueMarketplace,
)

STATUS_RESERVED = "reserved"
STATUS_COMMITTED = "committed"
STATUS_RELEASED = "released"

# Minutos padrão para expiração da reserva (Pix/cartão)
DEFAULT_RESERVE_MINUTES = 30


def _mark_reserva_released_and_restore_stock(db: Session, r: ReservaEstoqueMarketplace, now: datetime) -> None:
    """Marca linha como released e devolve quantidade ao anúncio e ao produto_cliente (se estoque sincronizado)."""
    r.status = STATUS_RELEASED
    r.released_at = now
    anuncio = db.query(AnuncioPlataforma).filter(AnuncioPlataforma.id == r.anuncio_id).first()
    if anuncio is None or r.quantidade is None:
        return
    qty = float(r.quantidade)
    anuncio.estoque_atual = (float(anuncio.estoque_atual or 0)) + qty
    if anuncio.tipo_estoque == "sincronizado" and anuncio.produto_ca_id:
        prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio.produto_ca_id).first()
        if prod is not None and prod.quantidade_atual is not None:
            prod.quantidade_atual = float(prod.quantidade_atual) + qty


def reserve_for_order(
    db: Session,
    pedido_id: int,
    reserve_minutes: int = DEFAULT_RESERVE_MINUTES,
) -> List[ReservaEstoqueMarketplace]:
    """
    Cria reservas em status 'reserved' e deduz do estoque (fluxo legado).
    O checkout da vitrine não chama mais esta função; a baixa ocorre em commit_reservation no webhook.
    """
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        raise ValueError("Pedido não encontrado")
    items = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido_id).all()
    if not items:
        raise ValueError("Pedido sem itens")
    reserved_until = datetime.now(timezone.utc) + timedelta(minutes=reserve_minutes)
    created = []
    for item in items:
        anuncio = db.query(AnuncioPlataforma).filter(AnuncioPlataforma.id == item.anuncio_id).first()
        if not anuncio:
            raise ValueError(f"Anúncio {item.anuncio_id} não encontrado")
        qty = float(item.quantidade)
        if anuncio.estoque_atual is None or float(anuncio.estoque_atual) < qty:
            raise ValueError(
                f"Estoque insuficiente para anúncio {item.anuncio_id} (disponível: {anuncio.estoque_atual})"
            )
        reserva = ReservaEstoqueMarketplace(
            pedido_id=pedido_id,
            pedido_item_id=item.id,
            produto_cliente_id=anuncio.produto_ca_id,
            anuncio_id=anuncio.id,
            quantidade=Decimal(str(qty)),
            status=STATUS_RESERVED,
            reserved_until=reserved_until,
        )
        db.add(reserva)
        db.flush()
        created.append(reserva)
        anuncio.estoque_atual = float(anuncio.estoque_atual) - qty
        if anuncio.estoque_atual < 0:
            anuncio.estoque_atual = 0
        if anuncio.tipo_estoque == "sincronizado" and anuncio.produto_ca_id:
            prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio.produto_ca_id).first()
            if prod is not None and prod.quantidade_atual is not None:
                prod.quantidade_atual = max(0, float(prod.quantidade_atual) - qty)
    return created


def deduct_marketplace_pedido_stock_committed(db: Session, pedido_id: int) -> int:
    """
    Baixa estoque do anúncio (e produto sincronizado) e grava ReservaEstoqueMarketplace como committed.
    Usado no webhook (pagamento) e no checkout da vitrine **sem** gateway de pagamento (baixa imediata).
    """
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        raise ValueError("Pedido não encontrado")
    items = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido_id).all()
    if not items:
        raise ValueError("Pedido sem itens")
    now = datetime.now(timezone.utc)
    created = 0
    for item in items:
        anuncio = db.query(AnuncioPlataforma).filter(AnuncioPlataforma.id == item.anuncio_id).first()
        if not anuncio:
            raise ValueError(f"Anúncio {item.anuncio_id} não encontrado")
        qty = float(item.quantidade)
        if anuncio.tipo_estoque == "sincronizado" and anuncio.produto_ca_id:
            prod_sync = (
                db.query(ProdutoCliente)
                .filter(
                    ProdutoCliente.id == anuncio.produto_ca_id,
                    ProdutoCliente.cliente_id == pedido.tenant_id,
                )
                .first()
            )
            if prod_sync is not None and prod_sync.quantidade_atual is not None:
                anuncio.estoque_atual = float(prod_sync.quantidade_atual)
        if anuncio.estoque_atual is None or float(anuncio.estoque_atual) < qty:
            raise ValueError(
                f"Estoque insuficiente para anúncio {item.anuncio_id} (disponível: {anuncio.estoque_atual})"
            )
        db.add(
            ReservaEstoqueMarketplace(
                pedido_id=pedido_id,
                pedido_item_id=item.id,
                produto_cliente_id=anuncio.produto_ca_id,
                anuncio_id=anuncio.id,
                quantidade=Decimal(str(qty)),
                status=STATUS_COMMITTED,
                reserved_until=None,
                committed_at=now,
            )
        )
        db.flush()
        created += 1
        anuncio.estoque_atual = float(anuncio.estoque_atual) - qty
        if anuncio.estoque_atual < 0:
            anuncio.estoque_atual = 0
        if anuncio.tipo_estoque == "sincronizado" and anuncio.produto_ca_id:
            prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio.produto_ca_id).first()
            if prod is not None and prod.quantidade_atual is not None:
                prod.quantidade_atual = max(0, float(prod.quantidade_atual) - qty)
    return created


def commit_reservation(db: Session, pedido_id: int) -> int:
    """
    Idempotente: se já existir linha committed para o pedido, não altera nada.
    Se houver reservas em 'reserved' (legado), marca como committed (estoque já foi baixado na reserva).
    Caso contrário, baixa estoque agora e grava linhas committed.
    """
    has_committed = (
        db.query(ReservaEstoqueMarketplace.id)
        .filter(
            ReservaEstoqueMarketplace.pedido_id == pedido_id,
            ReservaEstoqueMarketplace.status == STATUS_COMMITTED,
        )
        .first()
    )
    if has_committed:
        return 0
    count = (
        db.query(ReservaEstoqueMarketplace)
        .filter(
            ReservaEstoqueMarketplace.pedido_id == pedido_id,
            ReservaEstoqueMarketplace.status == STATUS_RESERVED,
        )
        .update(
            {
                ReservaEstoqueMarketplace.status: STATUS_COMMITTED,
                ReservaEstoqueMarketplace.committed_at: datetime.now(timezone.utc),
            },
            synchronize_session="fetch",
        )
    )
    if count > 0:
        return int(count)
    return deduct_marketplace_pedido_stock_committed(db, pedido_id)


def _legacy_restore_marketplace_stock_from_itens_sem_reserva(db: Session, pedido_id: int) -> int:
    """
    Pedidos criados pelo checkout sem gateway antes de existir reserva: estoque foi baixado sem linhas.
    Devolve com base nos itens e grava linhas ``released`` para idempotência.
    """
    items = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido_id).all()
    if not items:
        return 0
    now = datetime.now(timezone.utc)
    done = 0
    for item in items:
        anuncio = db.query(AnuncioPlataforma).filter(AnuncioPlataforma.id == item.anuncio_id).first()
        if not anuncio:
            continue
        qty = float(item.quantidade)
        anuncio.estoque_atual = (float(anuncio.estoque_atual or 0)) + qty
        if anuncio.tipo_estoque == "sincronizado" and anuncio.produto_ca_id:
            prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio.produto_ca_id).first()
            if prod is not None and prod.quantidade_atual is not None:
                prod.quantidade_atual = float(prod.quantidade_atual) + qty
        db.add(
            ReservaEstoqueMarketplace(
                pedido_id=pedido_id,
                pedido_item_id=item.id,
                produto_cliente_id=anuncio.produto_ca_id,
                anuncio_id=anuncio.id,
                quantidade=Decimal(str(qty)),
                status=STATUS_RELEASED,
                reserved_until=None,
                released_at=now,
            )
        )
        done += 1
    return done


def release_reservation(db: Session, pedido_id: int) -> int:
    """Marca reservas como released e devolve quantidade ao estoque do anúncio/produto."""
    reservas = (
        db.query(ReservaEstoqueMarketplace)
        .filter(
            ReservaEstoqueMarketplace.pedido_id == pedido_id,
            ReservaEstoqueMarketplace.status == STATUS_RESERVED,
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for r in reservas:
        _mark_reserva_released_and_restore_stock(db, r, now)
    return len(reservas)


def restore_marketplace_pedido_stock(db: Session, pedido_id: int) -> int:
    """
    Idempotente: libera reservas 'reserved' e devolve ao estoque as baixas 'committed' do pedido
    (cancelamento manual, estorno ou cancelamento pelo consumidor). Não faz commit.

    Inclui fluxo legado: checkout sem gateway em que a baixa foi feita sem gravar reserva — nesse caso
    não há ``transaction_id`` e nenhuma linha em ``reserva_estoque_marketplace`` até o cancelamento;
    a devolução usa os itens do pedido e grava linhas ``released`` para não duplicar.
    """
    n = release_reservation(db, pedido_id)
    committed = (
        db.query(ReservaEstoqueMarketplace)
        .filter(
            ReservaEstoqueMarketplace.pedido_id == pedido_id,
            ReservaEstoqueMarketplace.status == STATUS_COMMITTED,
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for r in committed:
        _mark_reserva_released_and_restore_stock(db, r, now)
        n += 1
    if n > 0:
        return n
    total_linhas = (
        db.query(func.count(ReservaEstoqueMarketplace.id))
        .filter(ReservaEstoqueMarketplace.pedido_id == pedido_id)
        .scalar()
        or 0
    )
    if int(total_linhas) > 0:
        return n
    ped = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not ped:
        return n
    if (getattr(ped, "transaction_id", None) or "").strip():
        return n
    return n + _legacy_restore_marketplace_stock_from_itens_sem_reserva(db, pedido_id)


def expire_reservations(db: Session, older_than: Optional[datetime] = None) -> int:
    """Libera reservas com reserved_until vencido. Se older_than não informado, usa now()."""
    cutoff = older_than or datetime.now(timezone.utc)
    reservas = (
        db.query(ReservaEstoqueMarketplace)
        .filter(
            ReservaEstoqueMarketplace.status == STATUS_RESERVED,
            ReservaEstoqueMarketplace.reserved_until.isnot(None),
            ReservaEstoqueMarketplace.reserved_until < cutoff,
        )
        .all()
    )
    pedido_ids = list({r.pedido_id for r in reservas})
    count = 0
    for pid in pedido_ids:
        count += release_reservation(db, pid)
    return count


def get_reservas_ativas_por_pedido(db: Session, pedido_id: int) -> List[ReservaEstoqueMarketplace]:
    """Retorna reservas em status reserved do pedido."""
    return (
        db.query(ReservaEstoqueMarketplace)
        .filter(
            ReservaEstoqueMarketplace.pedido_id == pedido_id,
            ReservaEstoqueMarketplace.status == STATUS_RESERVED,
        )
        .all()
    )
