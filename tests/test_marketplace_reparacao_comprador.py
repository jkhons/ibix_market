"""Reparacao retroativa de comprador_id em pedidos marketplace.

Cenarios cobertos:
- 1:1: um REGISTERED + um GUEST com pedidos => dry_run lista; apply reatribui e gera audit_log + eventos.
- Conflito: dois REGISTERED com mesmo email => par marcado motivo_skip="multiple_registered" (sem aplicar).
- Filtro por email restringe a um par.
- Tenant sem matches retorna total_candidatos=0.
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models import (
    AuditLog,
    ConsumidorMarketplace,
    PedidoMarketplace,
    PedidoStatusEvento,
)
from app.services.marketplace_reparacao_comprador_service import (
    MOTIVO_DRY_RUN,
    MOTIVO_MULTIPLE_REGISTERED,
    MOTIVO_NENHUM_PEDIDO,
    reparar_comprador_pedidos,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            ConsumidorMarketplace.__table__,
            PedidoMarketplace.__table__,
            PedidoStatusEvento.__table__,
            AuditLog.__table__,
        ],
    )
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _criar_consumidor(
    db,
    *,
    tenant_id,
    email,
    tipo_consumidor,
    nome="Comprador Teste",
):
    c = ConsumidorMarketplace(
        tenant_id=tenant_id,
        email=email,
        nome=nome,
        tipo_consumidor=tipo_consumidor,
        status_cadastro="COMPLETO" if tipo_consumidor != "GUEST" else "PENDENTE",
        aceite_termos=True,
        ativo=True,
        aceite_marketing=False,
        email_verificado=False,
    )
    db.add(c)
    db.flush()
    return c


def _criar_pedido(db, *, tenant_id, loja_id, comprador_id, numero):
    p = PedidoMarketplace(
        tenant_id=tenant_id,
        loja_id=loja_id,
        comprador_id=comprador_id,
        numero_pedido=numero,
        comprador_nome="Comprador Teste",
        comprador_email="comprador@x.com",
        subtotal=Decimal("10.00"),
        desconto=Decimal("0.00"),
        taxa_entrega=Decimal("0.00"),
        total=Decimal("10.00"),
        status_pedido="aguardando_pagamento",
        status_pagamento="pendente",
        status_entrega="pendente",
        tipo_entrega="retirada",
        origem_pedido="checkout_guest",
        aceite_marketing_snapshot=False,
        aceite_politica_privacidade_snapshot=True,
    )
    db.add(p)
    db.flush()
    return p


def test_dry_run_lista_par_sem_aplicar(db_session):
    reg = _criar_consumidor(db_session, tenant_id=42, email="comprador@x.com", tipo_consumidor="REGISTERED")
    guest = _criar_consumidor(db_session, tenant_id=42, email="comprador@x.com", tipo_consumidor="GUEST")
    p1 = _criar_pedido(db_session, tenant_id=42, loja_id=1, comprador_id=guest.id, numero="42-1")

    resultado = reparar_comprador_pedidos(db_session, tenant_id=42, dry_run=True, actor_user_id=99)

    assert resultado.dry_run is True
    assert resultado.total_candidatos == 1
    assert resultado.total_aplicados == 0
    assert resultado.total_conflitos == 0
    assert len(resultado.pares) == 1
    par = resultado.pares[0]
    assert par.registered_id == reg.id
    assert par.guest_id == guest.id
    assert par.email == "comprador@x.com"
    assert par.pedidos_afetados == [p1.id]
    assert par.aplicado is False
    assert par.motivo_skip == MOTIVO_DRY_RUN

    db_session.refresh(p1)
    assert p1.comprador_id == guest.id
    assert db_session.query(AuditLog).count() == 0
    assert db_session.query(PedidoStatusEvento).count() == 0


def test_apply_reatribui_e_grava_audit_log(db_session):
    reg = _criar_consumidor(db_session, tenant_id=42, email="comprador@x.com", tipo_consumidor="REGISTERED")
    guest = _criar_consumidor(db_session, tenant_id=42, email="comprador@x.com", tipo_consumidor="GUEST")
    p1 = _criar_pedido(db_session, tenant_id=42, loja_id=1, comprador_id=guest.id, numero="42-1")
    p2 = _criar_pedido(db_session, tenant_id=42, loja_id=1, comprador_id=guest.id, numero="42-2")

    resultado = reparar_comprador_pedidos(
        db_session,
        tenant_id=42,
        dry_run=False,
        actor_user_id=99,
        request_ip="10.0.0.1",
    )

    assert resultado.dry_run is False
    assert resultado.total_candidatos == 2
    assert resultado.total_aplicados == 2
    assert resultado.total_conflitos == 0
    par = resultado.pares[0]
    assert par.aplicado is True
    assert par.motivo_skip is None
    assert sorted(par.pedidos_afetados) == sorted([p1.id, p2.id])

    db_session.refresh(p1)
    db_session.refresh(p2)
    assert p1.comprador_id == reg.id
    assert p2.comprador_id == reg.id

    eventos = db_session.query(PedidoStatusEvento).all()
    assert len(eventos) == 2
    assert all(ev.tipo_evento == "reatribuicao_comprador" for ev in eventos)
    assert all(ev.actor_type == "super_admin" for ev in eventos)
    assert all(ev.actor_id == 99 for ev in eventos)

    audits = db_session.query(AuditLog).all()
    assert len(audits) == 1
    audit = audits[0]
    assert audit.acao == "reatribuir_comprador_pedidos"
    assert audit.tenant_id == 42
    assert audit.user_id == 99
    assert audit.ip == "10.0.0.1"
    assert audit.recurso_tipo == "pedido_marketplace"


def test_conflito_multiplos_registered_nao_aplica(db_session):
    reg1 = _criar_consumidor(db_session, tenant_id=42, email="comprador@x.com", tipo_consumidor="REGISTERED", nome="A")
    _criar_consumidor(db_session, tenant_id=42, email="comprador@x.com", tipo_consumidor="REGISTERED", nome="B")
    guest = _criar_consumidor(db_session, tenant_id=42, email="comprador@x.com", tipo_consumidor="GUEST")
    p1 = _criar_pedido(db_session, tenant_id=42, loja_id=1, comprador_id=guest.id, numero="42-1")

    resultado = reparar_comprador_pedidos(db_session, tenant_id=42, dry_run=False, actor_user_id=99)

    assert resultado.total_aplicados == 0
    assert resultado.total_conflitos == 1
    par = resultado.pares[0]
    assert par.aplicado is False
    assert par.motivo_skip == MOTIVO_MULTIPLE_REGISTERED

    db_session.refresh(p1)
    assert p1.comprador_id == guest.id
    assert db_session.query(AuditLog).count() == 0


def test_filtro_email_restringe_pares(db_session):
    reg_a = _criar_consumidor(db_session, tenant_id=42, email="a@x.com", tipo_consumidor="REGISTERED")
    guest_a = _criar_consumidor(db_session, tenant_id=42, email="a@x.com", tipo_consumidor="GUEST")
    _criar_consumidor(db_session, tenant_id=42, email="b@x.com", tipo_consumidor="REGISTERED")
    guest_b = _criar_consumidor(db_session, tenant_id=42, email="b@x.com", tipo_consumidor="GUEST")
    p_a = _criar_pedido(db_session, tenant_id=42, loja_id=1, comprador_id=guest_a.id, numero="42-A")
    p_b = _criar_pedido(db_session, tenant_id=42, loja_id=1, comprador_id=guest_b.id, numero="42-B")

    resultado = reparar_comprador_pedidos(
        db_session,
        tenant_id=42,
        email="A@X.com",
        dry_run=False,
        actor_user_id=99,
    )

    assert resultado.total_aplicados == 1
    assert len(resultado.pares) == 1
    par = resultado.pares[0]
    assert par.email == "a@x.com"
    assert par.registered_id == reg_a.id

    db_session.refresh(p_a)
    db_session.refresh(p_b)
    assert p_a.comprador_id == reg_a.id
    assert p_b.comprador_id == guest_b.id


def test_tenant_sem_matches_retorna_zero(db_session):
    _criar_consumidor(db_session, tenant_id=42, email="x@x.com", tipo_consumidor="REGISTERED")

    resultado = reparar_comprador_pedidos(db_session, tenant_id=42, dry_run=False)

    assert resultado.total_candidatos == 0
    assert resultado.total_aplicados == 0
    assert resultado.total_conflitos == 0
    assert resultado.pares == []
    assert db_session.query(AuditLog).count() == 0


def test_guest_sem_pedidos_e_skipado(db_session):
    _criar_consumidor(db_session, tenant_id=42, email="x@x.com", tipo_consumidor="REGISTERED")
    _criar_consumidor(db_session, tenant_id=42, email="x@x.com", tipo_consumidor="GUEST")

    resultado = reparar_comprador_pedidos(db_session, tenant_id=42, dry_run=False)

    assert resultado.total_aplicados == 0
    assert resultado.total_candidatos == 0
    assert len(resultado.pares) == 1
    assert resultado.pares[0].motivo_skip == MOTIVO_NENHUM_PEDIDO
    assert resultado.pares[0].pedidos_afetados == []


def test_tenant_id_zero_levanta_erro(db_session):
    with pytest.raises(ValueError):
        reparar_comprador_pedidos(db_session, tenant_id=0)
