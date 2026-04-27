# PDV Ibix - Serviço checkout guest e integração CRM
"""get_or_create_consumidor, numero_pedido, emit_integration_event, snapshots de itens."""
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import (
    AnuncioPlataforma,
    CategoriaPlataforma,
    ConsumidorMarketplace,
    IntegrationEvent,
    ProdutoCliente,
)


def get_or_create_consumidor(
    db: Session,
    tenant_id: int,
    email: str,
    nome: str,
    telefone: Optional[str] = None,
    documento: Optional[str] = None,
    aceite_marketing: bool = False,
    canal_origem: Optional[str] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
    is_guest: bool = True,
) -> Tuple[ConsumidorMarketplace, bool]:
    """
    Busca consumidor por tenant_id + email (LOWER). Se não existir, cria como GUEST (ou REGISTERED se não is_guest).
    Retorna (consumidor, created).
    """
    email_norm = email.strip().lower()
    consumidor = (
        db.query(ConsumidorMarketplace)
        .filter(
            ConsumidorMarketplace.tenant_id == tenant_id,
            func.lower(ConsumidorMarketplace.email) == email_norm,
            ConsumidorMarketplace.deleted_at.is_(None),
        )
        .first()
    )
    if consumidor:
        return consumidor, False

    tipo = "GUEST" if is_guest else "REGISTERED"
    status_cadastro = "INCOMPLETO" if is_guest else "COMPLETO"
    consumidor = ConsumidorMarketplace(
        tenant_id=tenant_id,
        email=email_norm,
        senha_hash=None,
        nome=nome.strip()[:200],
        telefone=telefone[:20] if telefone else None,
        documento=documento[:20] if documento else None,
        aceite_termos=False,
        ativo=True,
        tipo_consumidor=tipo,
        status_cadastro=status_cadastro,
        aceite_marketing=aceite_marketing,
        aceite_marketing_em=datetime.now(timezone.utc) if aceite_marketing else None,
        origem_cadastro="checkout_guest" if is_guest else "cadastro_loja",
        canal_origem=canal_origem,
        utm_source=utm_source[:150] if utm_source else None,
        utm_medium=utm_medium[:150] if utm_medium else None,
        utm_campaign=utm_campaign[:150] if utm_campaign else None,
    )
    db.add(consumidor)
    db.flush()
    return consumidor, True


def generate_numero_pedido(tenant_id: int, pedido_id: int) -> str:
    """Formato único: tenant_id-pedido_id (ex: 5-123)."""
    return f"{tenant_id}-{pedido_id}"


def emit_integration_event(
    db: Session,
    tenant_id: int,
    event_name: str,
    entity_type: str,
    entity_id: int,
    payload: dict[str, Any],
) -> IntegrationEvent:
    """Registra evento para consumo pela API de integração (CRM)."""
    ev = IntegrationEvent(
        tenant_id=tenant_id,
        event_name=event_name,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload,
        status="pending",
    )
    db.add(ev)
    db.flush()
    return ev


def build_item_snapshots(
    db: Session,
    anuncio: AnuncioPlataforma,
) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """
    Retorna (nome_produto_snapshot, categoria_snapshot, marca_snapshot, sku_snapshot).
    Nome do item: prioriza cadastro do produto (estabelecimento); fallback título do anúncio.
    """
    categoria_snapshot = None
    if anuncio.categoria_id:
        cat = db.query(CategoriaPlataforma).filter(CategoriaPlataforma.id == anuncio.categoria_id).first()
        if cat:
            categoria_snapshot = (cat.nome or "")[:120]
    marca_snapshot = None
    sku_snapshot = None
    nome = (anuncio.titulo or "")[:255]
    prod = None
    if anuncio.produto_ca_id:
        prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio.produto_ca_id).first()
    if prod:
        if (prod.nome or "").strip():
            nome = (prod.nome or "").strip()[:255]
        marca_snapshot = (prod.fabricante or prod.fornecedor or "")[:120] or None
        sku_snapshot = (prod.codigo or prod.referencia or "")[:120] or None
    return nome, categoria_snapshot, marca_snapshot, sku_snapshot
