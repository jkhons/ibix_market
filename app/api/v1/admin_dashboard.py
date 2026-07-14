# PDV Ibix - Admin Dashboard: Super Admin (clientes, logins, pagamentos) e Administrador (CAs, % participação, comissões)
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.middleware import require_superadmin_or_admin
from app.services.vitrine_access_analytics_service import (
    build_visitantes_vitrine_analytics,
    periodo_to_since_utc,
    visitantes_vitrine_por_tipo,
)
from app.database.connection import get_db
from app.models import (
    AuditLog,
    Payment,
    Role,
    SubscriptionBilling,
    Tenant,
    Usuario,
)
from app.models.administrador_cliente_administrador import AdministradorClienteAdministrador
from app.models.divulgador import Divulgador
from app.models.divulgador_regra import DivulgadorRegra
from app.models.brand import Brand
from app.models.subscription_billing import ComissaoAdministrador
from app.services.brand_scope_service import brand_scope_meta, resolve_admin_brand_scope

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])

# Status considerado pago (Mercado Pago)
PAYMENT_STATUS_PAID = ("approved", "authorized")
LOGIN_ACAO = "login_sucesso"
LISTA_CLIENTES_NOVOS_LIMIT = 15
LISTA_CADASTROS_NOVOS_LIMIT = 15
ULTIMOS_LOGINS_LIMIT = 15
PAGAMENTOS_RECENTES_LIMIT = 10


def _filter_tenants_by_brand(query, brand_id: Optional[int]):
    if brand_id is not None:
        return query.filter(Tenant.brand_id == brand_id)
    return query


def _filter_usuarios_by_brand(query, brand_id: Optional[int]):
    if brand_id is not None:
        return query.join(Tenant, Tenant.id == Usuario.tenant_id).filter(Tenant.brand_id == brand_id)
    return query


def _get_sub(db: Session, tenant_id: int) -> SubscriptionBilling | None:
    return (
        db.query(SubscriptionBilling)
        .filter(SubscriptionBilling.tenant_id == tenant_id)
        .first()
    )


def _dashboard_administrador(db: Session, usuario_id: int) -> dict[str, Any]:
    """Payload do dashboard para role Administrador: CAs vinculados, % participação, resumo comissões."""
    # Listagem de CAs (AdministradorClienteAdministrador + Usuario + Tenant/Subscription)
    vinculos = (
        db.query(AdministradorClienteAdministrador, Usuario)
        .join(Usuario, Usuario.id == AdministradorClienteAdministrador.usuario_id_cliente_administrador)
        .filter(AdministradorClienteAdministrador.usuario_id_administrador == usuario_id)
        .all()
    )
    cas = []
    for aca, u in vinculos:
        sub = _get_sub(db, u.tenant_id) if u.tenant_id else None
        cas.append({
            "id": u.id,
            "nome": u.nome or "",
            "email": u.email or "",
            "tenant_id": u.tenant_id,
            "subscription_status": sub.status if sub else None,
        })

    # % de participação: Divulgador (usuario_id = admin) -> DivulgadorRegra (mais recente)
    divulgador = db.query(Divulgador).filter(Divulgador.usuario_id == usuario_id).first()
    percentual_participacao = None
    divulgador_regra_id = None
    if divulgador:
        regra = (
            db.query(DivulgadorRegra)
            .filter(DivulgadorRegra.divulgador_id == divulgador.id)
            .order_by(DivulgadorRegra.id.desc())
            .first()
        )
        if regra:
            percentual_participacao = regra.percentual_comissao
            divulgador_regra_id = regra.id

    # Resumo comissões (ComissaoAdministrador por status)
    agg = (
        db.query(ComissaoAdministrador.status, func.sum(ComissaoAdministrador.valor_comissao_centavos), func.count(ComissaoAdministrador.id))
        .filter(ComissaoAdministrador.usuario_id_administrador == usuario_id)
        .group_by(ComissaoAdministrador.status)
        .all()
    )
    pendente_centavos = 0
    pago_centavos = 0
    total_pendente = 0
    total_pago = 0
    for row in agg:
        status_val, soma, qtd = row[0], int(row[1] or 0), int(row[2] or 0)
        if status_val == "pendente":
            pendente_centavos = soma
            total_pendente = qtd
        elif status_val == "pago":
            pago_centavos = soma
            total_pago = qtd

    return {
        "tipo": "administrador",
        "percentual_participacao": percentual_participacao,
        "divulgador_regra_id": divulgador_regra_id,
        "cas": cas,
        "resumo_comissoes": {
            "pendente_centavos": pendente_centavos,
            "pago_centavos": pago_centavos,
            "total_pendente": total_pendente,
            "total_pago": total_pago,
        },
    }


@router.get("", response_model=dict)
def get_admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin_or_admin()),
    incluir_analytics: bool = Query(False, description="Inclui rankings de páginas/produtos (Super Admin)"),
    periodo: str = Query("hoje", description="hoje | ultimos_7_dias | ultimos_30_dias"),
    tipo_visitante: str = Query("HUMANO", description="HUMANO | BOT | CLOUD | TODOS (tabelas analytics)"),
    brand_id: Optional[int] = Query(None, description="Recorte por marca (tenants.brand_id) — Super Admin"),
) -> dict[str, Any]:
    """Super Admin: clientes novos, logins, pagamentos. Administrador: listagem CAs, % participação, resumo comissões."""
    if current_user.role and getattr(current_user.role, "nome", None) == "Administrador":
        return _dashboard_administrador(db, current_user.id)

    effective_brand = resolve_admin_brand_scope(request, db, brand_id)

    # Super Admin: lógica existente
    today = date.today()
    delta_7d = today - timedelta(days=7)
    delta_30d = today - timedelta(days=30)

    # Clientes novos (tenants por created_at)
    tenants_7d = _filter_tenants_by_brand(
        db.query(Tenant).filter(Tenant.created_at >= delta_7d),
        effective_brand,
    ).count()
    tenants_30d = _filter_tenants_by_brand(
        db.query(Tenant).filter(Tenant.created_at >= delta_30d),
        effective_brand,
    ).count()
    lista_clientes_novos = (
        _filter_tenants_by_brand(
            db.query(Tenant.id, Tenant.nome, Tenant.created_at, Tenant.brand_id),
            effective_brand,
        )
        .order_by(Tenant.created_at.desc())
        .limit(LISTA_CLIENTES_NOVOS_LIMIT)
        .all()
    )
    clientes_novos = {
        "total_7d": tenants_7d,
        "total_30d": tenants_30d,
        "lista": [
            {
                "id": t.id,
                "nome": t.nome or "",
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "brand_id": t.brand_id,
            }
            for t in lista_clientes_novos
        ],
    }

    # Cadastros novos (usuários criados recentemente)
    usuarios_7d = _filter_usuarios_by_brand(
        db.query(Usuario).filter(Usuario.created_at >= delta_7d),
        effective_brand,
    ).count()
    usuarios_30d = _filter_usuarios_by_brand(
        db.query(Usuario).filter(Usuario.created_at >= delta_30d),
        effective_brand,
    ).count()
    cadastros_q = (
        db.query(Usuario.id, Usuario.nome, Usuario.email, Usuario.created_at, Role.nome.label("role_nome"))
        .outerjoin(Role, Role.id == Usuario.role_id)
    )
    if effective_brand is not None:
        cadastros_q = cadastros_q.join(Tenant, Tenant.id == Usuario.tenant_id).filter(
            Tenant.brand_id == effective_brand
        )
    lista_cadastros_novos = (
        cadastros_q.order_by(Usuario.created_at.desc()).limit(LISTA_CADASTROS_NOVOS_LIMIT).all()
    )
    cadastros_novos = {
        "total_7d": usuarios_7d,
        "total_30d": usuarios_30d,
        "lista": [
            {
                "id": r.id,
                "nome": r.nome or "",
                "email": r.email or "",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "role_nome": r.role_nome or "-",
            }
            for r in lista_cadastros_novos
        ],
    }

    # Usuários ativos nas últimas 24h (distinct user_id com login_sucesso)
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    _usuarios_24h = (
        db.query(func.count(func.distinct(AuditLog.user_id)))
        .filter(
            AuditLog.acao == LOGIN_ACAO,
            AuditLog.created_at >= since_24h,
            AuditLog.user_id.isnot(None),
        )
        .scalar()
    )
    usuarios_ativos_24h = int(_usuarios_24h) if _usuarios_24h is not None else 0

    # Últimos logins (AuditLog + Usuario)
    ultimos_logins_rows = (
        db.query(AuditLog.user_id, AuditLog.created_at, Usuario.nome, Usuario.email)
        .outerjoin(Usuario, Usuario.id == AuditLog.user_id)
        .filter(AuditLog.acao == LOGIN_ACAO, AuditLog.user_id.isnot(None))
        .order_by(AuditLog.created_at.desc())
        .limit(ULTIMOS_LOGINS_LIMIT)
        .all()
    )
    ultimos_logins = [
        {
            "usuario_id": r.user_id,
            "nome": r.nome or "-",
            "email": r.email or "-",
            "data_hora": r.created_at.isoformat() if r.created_at else None,
        }
        for r in ultimos_logins_rows
    ]

    # Pagamentos realizados (mês atual: paid_at no mês, status approved/authorized)
    month_start = today.replace(day=1)
    try:
        pay_mes_q = (
            db.query(
                func.count(Payment.id).label("total"),
                func.coalesce(func.sum(Payment.amount_centavos), 0).label("valor_centavos"),
            )
            .join(SubscriptionBilling, SubscriptionBilling.id == Payment.subscription_id)
            .join(Tenant, Tenant.id == SubscriptionBilling.tenant_id)
            .filter(
                Payment.status.in_(PAYMENT_STATUS_PAID),
                Payment.paid_at.isnot(None),
                func.date(Payment.paid_at) >= month_start,
            )
        )
        if effective_brand is not None:
            pay_mes_q = pay_mes_q.filter(Tenant.brand_id == effective_brand)
        payments_mes = pay_mes_q.one()
        total_mes = int(payments_mes.total or 0)
        valor_mes_centavos = int(payments_mes.valor_centavos or 0)
    except Exception:
        total_mes = 0
        valor_mes_centavos = 0

    recentes_q = (
        db.query(Payment.id, Payment.amount_centavos, Payment.paid_at, Tenant.nome, Tenant.brand_id)
        .join(SubscriptionBilling, SubscriptionBilling.id == Payment.subscription_id)
        .join(Tenant, Tenant.id == SubscriptionBilling.tenant_id)
        .filter(
            Payment.status.in_(PAYMENT_STATUS_PAID),
            Payment.paid_at.isnot(None),
        )
    )
    if effective_brand is not None:
        recentes_q = recentes_q.filter(Tenant.brand_id == effective_brand)
    recentes_query = recentes_q.order_by(Payment.paid_at.desc()).limit(PAGAMENTOS_RECENTES_LIMIT).all()
    pagamentos_realizados = {
        "total_mes": total_mes,
        "valor_mes_centavos": valor_mes_centavos,
        "recentes": [
            {
                "id": p.id,
                "tenant_nome": p.nome or "",
                "amount_centavos": p.amount_centavos,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            }
            for p in recentes_query
        ],
    }

    # Pagamentos vencidos (next_charge_at < hoje, status inadimplente ou ativa)
    subs_vencidas_q = (
        db.query(SubscriptionBilling, Tenant)
        .join(Tenant, Tenant.id == SubscriptionBilling.tenant_id)
        .filter(
            SubscriptionBilling.next_charge_at.isnot(None),
            SubscriptionBilling.next_charge_at < today,
            SubscriptionBilling.status.in_(["inadimplente", "ativa"]),
        )
    )
    if effective_brand is not None:
        subs_vencidas_q = subs_vencidas_q.filter(Tenant.brand_id == effective_brand)
    subs_vencidas = subs_vencidas_q.all()
    pagamentos_vencidos = {
        "total": len(subs_vencidas),
        "lista": [
            {
                "tenant_id": t.id,
                "tenant_nome": t.nome or "",
                "next_charge_at": sub.next_charge_at.isoformat() if sub.next_charge_at else None,
                "dias_atraso": (today - sub.next_charge_at).days if sub.next_charge_at else 0,
                "status": sub.status,
            }
            for sub, t in subs_vencidas
        ],
    }

    # Próximos pagamentos (next_charge_at entre hoje e hoje+15)
    end_15d = today + timedelta(days=15)
    subs_proximas_q = (
        db.query(SubscriptionBilling, Tenant)
        .join(Tenant, Tenant.id == SubscriptionBilling.tenant_id)
        .filter(
            SubscriptionBilling.next_charge_at.isnot(None),
            SubscriptionBilling.next_charge_at >= today,
            SubscriptionBilling.next_charge_at <= end_15d,
        )
    )
    if effective_brand is not None:
        subs_proximas_q = subs_proximas_q.filter(Tenant.brand_id == effective_brand)
    subs_proximas = subs_proximas_q.order_by(SubscriptionBilling.next_charge_at.asc()).all()
    proximos_pagamentos_15d = {
        "lista": [
            {
                "tenant_id": t.id,
                "tenant_nome": t.nome or "",
                "next_charge_at": sub.next_charge_at.isoformat() if sub.next_charge_at else None,
                "status": sub.status,
            }
            for sub, t in subs_proximas
        ],
    }

    # Visitantes vitrine pública — IPs únicos por tipo. Calendário "hoje" em America/Sao_Paulo.
    now_utc = datetime.now(timezone.utc)
    inicio_hoje_br = periodo_to_since_utc("hoje", now_utc)
    since_7d = periodo_to_since_utc("ultimos_7_dias", now_utc)
    since_30d = periodo_to_since_utc("ultimos_30_dias", now_utc)

    visitantes_hoje_dict = visitantes_vitrine_por_tipo(db, inicio_hoje_br)
    visitantes_vitrine = {
        "hoje": visitantes_hoje_dict,
        "ultimos_7_dias": visitantes_vitrine_por_tipo(db, since_7d),
        "ultimos_30_dias": visitantes_vitrine_por_tipo(db, since_30d),
    }

    marcas = [
        {"id": b.id, "slug": b.slug, "nome": b.nome_exibicao or b.slug}
        for b in db.query(Brand).filter(Brand.ativo.is_(True)).order_by(Brand.id.asc()).all()
    ]

    payload: dict[str, Any] = {
        "brand_id_filtro": effective_brand,
        "brand_scope": brand_scope_meta(request, db, effective_brand),
        "marcas": marcas,
        "clientes_novos": clientes_novos,
        "cadastros_novos": cadastros_novos,
        "usuarios_ativos_24h": {"total": usuarios_ativos_24h},
        "ultimos_logins": ultimos_logins,
        "pagamentos_realizados": pagamentos_realizados,
        "pagamentos_vencidos": pagamentos_vencidos,
        "proximos_pagamentos_15d": proximos_pagamentos_15d,
        "visitantes_hoje": visitantes_hoje_dict,
        "visitantes_vitrine": visitantes_vitrine,
    }
    if incluir_analytics:
        payload["visitantes_vitrine_analytics"] = build_visitantes_vitrine_analytics(
            db,
            periodo=periodo,
            tipo_visitante=tipo_visitante,
            now_utc=now_utc,
        )
    return payload
