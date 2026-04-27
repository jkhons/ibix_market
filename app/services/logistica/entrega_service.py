# PDV Ibix - Service: criar, publicar e cancelar entrega
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ...core.constants.entrega_status import (
    ACEITA,
    AGUARDANDO_PUBLICACAO,
    CANCELADA,
    DISPONIVEL,
    EXPIRADA,
)
from ...models import EntregaEvento, EntregaMarketplace, LojaMarketplace, PedidoMarketplace


def _registrar_evento(
    db: Session,
    entrega_id: int,
    tipo_evento: str,
    actor_type: str,
    actor_id: Optional[int] = None,
    payload: Optional[dict] = None,
) -> None:
    ev = EntregaEvento(
        entrega_id=entrega_id,
        tipo_evento=tipo_evento,
        actor_type=actor_type,
        actor_id=actor_id,
        payload_json=payload,
    )
    db.add(ev)


def criar_entrega(
    db: Session,
    pedido_id: int,
    tenant_id: int,
    valor_frete: float,
    tipo_veiculo_aceito: Optional[str] = None,
    observacoes: Optional[str] = None,
    aceita_ate_em: Optional[datetime] = None,
    actor_user_id: Optional[int] = None,
) -> EntregaMarketplace:
    """Cria registro de entrega a partir do pedido. Status inicial: aguardando_publicacao."""
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        raise ValueError("Pedido não encontrado")
    if pedido.tenant_id != tenant_id:
        raise ValueError("Pedido não pertence ao tenant")
    existente = db.query(EntregaMarketplace).filter(EntregaMarketplace.pedido_id == pedido_id).first()
    if existente:
        raise ValueError("Já existe entrega para este pedido")

    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == pedido.loja_id).first()
    nome_retirada = loja.nome_loja if loja else None
    endereco_retirada = None
    endereco_entrega = None
    if pedido.endereco_entrega:
        endereco_entrega = {"endereco_texto": pedido.endereco_entrega}

    entrega = EntregaMarketplace(
        pedido_id=pedido_id,
        tenant_id=tenant_id,
        status=AGUARDANDO_PUBLICACAO,
        valor_frete=valor_frete,
        tipo_veiculo_aceito=tipo_veiculo_aceito,
        nome_retirada=nome_retirada,
        telefone_retirada=pedido.comprador_telefone,
        endereco_retirada_json=endereco_retirada,
        nome_destinatario=pedido.comprador_nome,
        telefone_destinatario=pedido.comprador_telefone,
        endereco_entrega_json=endereco_entrega,
        observacoes=observacoes,
        aceita_ate_em=aceita_ate_em,
    )
    db.add(entrega)
    db.flush()

    # Preencher custo_frete/lucro_frete no pedido (formato plataforma: valida margem)
    from decimal import Decimal
    fmt = getattr(pedido, "formato_frete_snapshot", None) or "sem_frete"
    custo = Decimal(str(valor_frete))
    pedido.custo_frete = custo
    if fmt == "plataforma":
        taxa_cobrada = pedido.taxa_entrega or Decimal("0")
        if custo > taxa_cobrada:
            raise ValueError("Custo do frete excede o valor cobrado do cliente")
        pedido.lucro_frete = taxa_cobrada - custo
    else:
        pedido.lucro_frete = None

    _registrar_evento(
        db, entrega.id, "entrega_criada",
        "tenant_usuario", actor_id=actor_user_id,
        payload={"pedido_id": pedido_id, "valor_frete": float(valor_frete)},
    )
    db.commit()
    db.refresh(entrega)
    return entrega


def publicar_entrega(db: Session, entrega_id: int, actor_user_id: Optional[int] = None) -> EntregaMarketplace:
    """Muda status para disponivel e seta publicada_em."""
    entrega = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
    if not entrega:
        raise ValueError("Entrega não encontrada")
    if entrega.status != AGUARDANDO_PUBLICACAO:
        raise ValueError("Entrega já publicada ou estado inválido")

    agora = datetime.now(timezone.utc)
    entrega.status = DISPONIVEL
    entrega.publicada_em = agora
    _registrar_evento(db, entrega.id, "entrega_publicada", "tenant_usuario", actor_id=actor_user_id)
    db.commit()
    db.refresh(entrega)
    return entrega


def marcar_entregas_expiradas(db: Session) -> int:
    """
    Regra de expiração: se aceita_ate_em < now() e status ainda é disponivel,
    marca a entrega como expirada e registra evento.
    Pode ser chamada por job periódico ou sob demanda (ex.: na listagem de disponíveis).
    Retorna a quantidade de entregas marcadas como expiradas.
    """
    agora = datetime.now(timezone.utc)
    rows = (
        db.query(EntregaMarketplace)
        .filter(
            EntregaMarketplace.status == DISPONIVEL,
            EntregaMarketplace.aceita_ate_em.isnot(None),
            EntregaMarketplace.aceita_ate_em < agora,
        )
        .all()
    )
    for entrega in rows:
        entrega.status = EXPIRADA
        _registrar_evento(
            db,
            entrega.id,
            "entrega_expirada",
            "sistema",
            payload={"aceita_ate_em": entrega.aceita_ate_em.isoformat() if entrega.aceita_ate_em else None},
        )
    if rows:
        db.commit()
    return len(rows)


def cancelar_entrega(db: Session, entrega_id: int, actor_user_id: Optional[int] = None) -> EntregaMarketplace:
    """Marca entrega como cancelada."""
    entrega = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
    if not entrega:
        raise ValueError("Entrega não encontrada")
    if entrega.status not in (AGUARDANDO_PUBLICACAO, DISPONIVEL, ACEITA):
        raise ValueError("Entrega não pode ser cancelada neste estado")

    agora = datetime.now(timezone.utc)
    entrega.status = CANCELADA
    entrega.cancelada_em = agora
    _registrar_evento(db, entrega.id, "entrega_cancelada", "tenant_usuario", actor_id=actor_user_id)
    db.commit()
    db.refresh(entrega)
    return entrega
