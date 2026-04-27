# PDV Ibix - Reparacao retroativa de comprador_id em pedidos marketplace
"""
Reatribui `PedidoMarketplace.comprador_id` quando aponta para um consumidor "guest"
duplicado (mesmo email + mesmo tenant) cujo email coincide com um consumidor registrado.

Cenario: pedidos criados antes da fix em `resolve_comprador_para_loja` ficaram com
`comprador_id` apontando para um guest no checkout, e o consumidor logado nao ve esses
pedidos em `GET /api/v1/loja/meus-pedidos`. Este servico identifica esses pares e
reatribui `comprador_id` para o consumidor registrado, sem deletar o guest (historico
preservado, append-only).

Operacao por tenant, com `dry_run` por padrao. Auditoria em `audit_log` (registro unico
por execucao no modo apply) e evento timeline por pedido reatribuido em `pedido_status_evento`.
"""
import json
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditLog, ConsumidorMarketplace, PedidoMarketplace
from app.schemas.marketplace import ReparacaoCompradorPar, ReparacaoCompradorResultado
from app.services.pedido_status_evento_service import registrar_pedido_status_evento

MOTIVO_NENHUM_PEDIDO = "no_orders"
MOTIVO_MULTIPLE_REGISTERED = "multiple_registered"
MOTIVO_DRY_RUN = "dry_run"


def reparar_comprador_pedidos(
    db: Session,
    *,
    tenant_id: int,
    email: Optional[str] = None,
    dry_run: bool = True,
    actor_user_id: Optional[int] = None,
    request_ip: Optional[str] = None,
) -> ReparacaoCompradorResultado:
    """Reatribui `comprador_id` de pedidos antigos para o consumidor registrado.

    Match: para cada (tenant_id, email_normalizado), procura exatamente um consumidor
    REGISTERED ativo e um ou mais consumidores GUEST. Pedidos cujo `comprador_id` aponta
    para algum dos guests sao reatribuidos para o registered.

    Conflito: se houver mais de um REGISTERED ativo para o mesmo (tenant, email), o par
    e listado mas nao aplicado (motivo `multiple_registered`).

    Sem efeito quando `dry_run=True`: retorna apenas o relatorio.
    """
    if not tenant_id:
        raise ValueError("tenant_id obrigatorio")

    email_norm: Optional[str] = None
    if email:
        email_norm = email.strip().lower()
        if not email_norm:
            email_norm = None

    pares: list[ReparacaoCompradorPar] = []
    total_aplicados = 0
    total_conflitos = 0

    grouped = (
        db.query(
            func.lower(ConsumidorMarketplace.email).label("email_norm"),
        )
        .filter(ConsumidorMarketplace.tenant_id == tenant_id)
        .filter(ConsumidorMarketplace.deleted_at.is_(None))
    )
    if email_norm:
        grouped = grouped.filter(func.lower(ConsumidorMarketplace.email) == email_norm)
    grouped = grouped.group_by(func.lower(ConsumidorMarketplace.email)).having(
        func.count(ConsumidorMarketplace.id) > 1,
    )

    for (email_grp,) in grouped.all():
        consumidores = (
            db.query(ConsumidorMarketplace)
            .filter(
                ConsumidorMarketplace.tenant_id == tenant_id,
                ConsumidorMarketplace.deleted_at.is_(None),
                func.lower(ConsumidorMarketplace.email) == email_grp,
            )
            .all()
        )
        registereds = [c for c in consumidores if (c.tipo_consumidor or "").upper() != "GUEST"]
        guests = [c for c in consumidores if (c.tipo_consumidor or "").upper() == "GUEST"]
        if not registereds or not guests:
            continue

        if len(registereds) > 1:
            for guest in guests:
                pedidos_ids = _pedidos_do_guest_no_tenant(db, tenant_id=tenant_id, guest_id=guest.id)
                if not pedidos_ids:
                    continue
                pares.append(
                    ReparacaoCompradorPar(
                        registered_id=registereds[0].id,
                        guest_id=guest.id,
                        email=email_grp,
                        pedidos_afetados=pedidos_ids,
                        aplicado=False,
                        motivo_skip=MOTIVO_MULTIPLE_REGISTERED,
                    )
                )
                total_conflitos += 1
            continue

        registered = registereds[0]
        for guest in guests:
            pedidos_ids = _pedidos_do_guest_no_tenant(db, tenant_id=tenant_id, guest_id=guest.id)
            if not pedidos_ids:
                pares.append(
                    ReparacaoCompradorPar(
                        registered_id=registered.id,
                        guest_id=guest.id,
                        email=email_grp,
                        pedidos_afetados=[],
                        aplicado=False,
                        motivo_skip=MOTIVO_NENHUM_PEDIDO,
                    )
                )
                continue

            if dry_run:
                pares.append(
                    ReparacaoCompradorPar(
                        registered_id=registered.id,
                        guest_id=guest.id,
                        email=email_grp,
                        pedidos_afetados=pedidos_ids,
                        aplicado=False,
                        motivo_skip=MOTIVO_DRY_RUN,
                    )
                )
                continue

            (
                db.query(PedidoMarketplace)
                .filter(
                    PedidoMarketplace.tenant_id == tenant_id,
                    PedidoMarketplace.id.in_(pedidos_ids),
                )
                .update({PedidoMarketplace.comprador_id: registered.id}, synchronize_session=False)
            )
            for pid in pedidos_ids:
                registrar_pedido_status_evento(
                    db,
                    pedido_id=pid,
                    tipo_evento="reatribuicao_comprador",
                    status_codigo="reatribuicao_comprador",
                    status_label="Comprador reatribuído (reparação)",
                    actor_type="super_admin",
                    actor_id=actor_user_id,
                )
            db.flush()
            total_aplicados += len(pedidos_ids)
            pares.append(
                ReparacaoCompradorPar(
                    registered_id=registered.id,
                    guest_id=guest.id,
                    email=email_grp,
                    pedidos_afetados=pedidos_ids,
                    aplicado=True,
                    motivo_skip=None,
                )
            )

    total_candidatos = sum(len(p.pedidos_afetados) for p in pares if p.motivo_skip != MOTIVO_NENHUM_PEDIDO)

    resultado = ReparacaoCompradorResultado(
        tenant_id=tenant_id,
        dry_run=dry_run,
        total_candidatos=total_candidatos,
        total_aplicados=total_aplicados,
        total_conflitos=total_conflitos,
        pares=pares,
    )

    if not dry_run and total_aplicados > 0:
        db.add(
            AuditLog(
                user_id=actor_user_id,
                tenant_id=tenant_id,
                recurso_tipo="pedido_marketplace",
                recurso_id=None,
                acao="reatribuir_comprador_pedidos",
                ip=request_ip,
                detalhes=json.dumps(
                    {
                        "tenant_id": tenant_id,
                        "email_filtro": email_norm,
                        "total_candidatos": total_candidatos,
                        "total_aplicados": total_aplicados,
                        "total_conflitos": total_conflitos,
                        "pares": [
                            {
                                "registered_id": p.registered_id,
                                "guest_id": p.guest_id,
                                "email": p.email,
                                "pedidos_afetados": p.pedidos_afetados,
                                "aplicado": p.aplicado,
                                "motivo_skip": p.motivo_skip,
                            }
                            for p in pares
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
        )
        db.flush()

    return resultado


def _pedidos_do_guest_no_tenant(db: Session, *, tenant_id: int, guest_id: int) -> list[int]:
    """IDs de pedidos do tenant cujo comprador_id e o guest informado."""
    rows = (
        db.query(PedidoMarketplace.id)
        .filter(
            PedidoMarketplace.tenant_id == tenant_id,
            PedidoMarketplace.comprador_id == guest_id,
        )
        .order_by(PedidoMarketplace.id.asc())
        .all()
    )
    return [r[0] for r in rows]
