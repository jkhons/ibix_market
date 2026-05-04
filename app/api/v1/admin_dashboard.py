# PDV Ibix - Admin Dashboard: Super Admin (clientes, logins, pagamentos) e Administrador (CAs, % participação, comissões)
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.middleware import require_superadmin_or_admin
from app.database.connection import get_db
from app.models import (
    AccessLog,
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
from app.models.subscription_billing import ComissaoAdministrador

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])

# Vitrine pública: o middleware grava path completo (/loja, /loja/produto/…); filtrar prefixo /loja.
TZ_BR = ZoneInfo("America/Sao_Paulo")

# Status considerado pago (Mercado Pago)
PAYMENT_STATUS_PAID = ("approved", "authorized")
LOGIN_ACAO = "login_sucesso"
LISTA_CLIENTES_NOVOS_LIMIT = 15
LISTA_CADASTROS_NOVOS_LIMIT = 15
ULTIMOS_LOGINS_LIMIT = 15
PAGAMENTOS_RECENTES_LIMIT = 10


def _filtro_path_vitrine():
    """Acessos HTML da vitrine: home e qualquer subrota /loja/… (API /api/ não entra no access_log)."""
    return or_(AccessLog.path == "/loja", AccessLog.path.startswith("/loja/"))


def _visitantes_vitrine_por_tipo(db: Session, since_utc: datetime) -> dict[str, int]:
    rows = (
        db.query(AccessLog.tipo_visitante, func.count(func.distinct(AccessLog.ip)))
        .filter(AccessLog.created_at >= since_utc, _filtro_path_vitrine())
        .group_by(AccessLog.tipo_visitante)
        .all()
    )
    counts = {row[0]: row[1] for row in rows}
    return {
        "humanos": int(counts.get("HUMANO", 0)),
        "bots": int(counts.get("BOT", 0)),
        "cloud": int(counts.get("CLOUD", 0)),
    }


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
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin_or_admin()),
) -> dict[str, Any]:
    """Super Admin: clientes novos, logins, pagamentos. Administrador: listagem CAs, % participação, resumo comissões."""
    if current_user.role and getattr(current_user.role, "nome", None) == "Administrador":
        return _dashboard_administrador(db, current_user.id)

    # Super Admin: lógica existente
    today = date.today()
    delta_7d = today - timedelta(days=7)
    delta_30d = today - timedelta(days=30)

    # Clientes novos (tenants por created_at)
    tenants_7d = (
        db.query(Tenant)
        .filter(Tenant.created_at >= delta_7d)
        .count()
    )
    tenants_30d = (
        db.query(Tenant)
        .filter(Tenant.created_at >= delta_30d)
        .count()
    )
    lista_clientes_novos = (
        db.query(Tenant.id, Tenant.nome, Tenant.created_at)
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
            }
            for t in lista_clientes_novos
        ],
    }

    # Cadastros novos (usuários criados recentemente)
    usuarios_7d = db.query(Usuario).filter(Usuario.created_at >= delta_7d).count()
    usuarios_30d = db.query(Usuario).filter(Usuario.created_at >= delta_30d).count()
    lista_cadastros_novos = (
        db.query(Usuario.id, Usuario.nome, Usuario.email, Usuario.created_at, Role.nome.label("role_nome"))
        .outerjoin(Role, Role.id == Usuario.role_id)
        .order_by(Usuario.created_at.desc())
        .limit(LISTA_CADASTROS_NOVOS_LIMIT)
        .all()
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
        payments_mes = (
            db.query(
                func.count(Payment.id).label("total"),
                func.coalesce(func.sum(Payment.amount_centavos), 0).label("valor_centavos"),
            )
            .filter(
                Payment.status.in_(PAYMENT_STATUS_PAID),
                Payment.paid_at.isnot(None),
                func.date(Payment.paid_at) >= month_start,
            )
            .one()
        )
        total_mes = int(payments_mes.total or 0)
        valor_mes_centavos = int(payments_mes.valor_centavos or 0)
    except Exception:
        total_mes = 0
        valor_mes_centavos = 0

    recentes_query = (
        db.query(Payment.id, Payment.amount_centavos, Payment.paid_at, Tenant.nome)
        .join(SubscriptionBilling, SubscriptionBilling.id == Payment.subscription_id)
        .join(Tenant, Tenant.id == SubscriptionBilling.tenant_id)
        .filter(
            Payment.status.in_(PAYMENT_STATUS_PAID),
            Payment.paid_at.isnot(None),
        )
        .order_by(Payment.paid_at.desc())
        .limit(PAGAMENTOS_RECENTES_LIMIT)
        .all()
    )
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
    subs_vencidas = (
        db.query(SubscriptionBilling, Tenant)
        .join(Tenant, Tenant.id == SubscriptionBilling.tenant_id)
        .filter(
            SubscriptionBilling.next_charge_at.isnot(None),
            SubscriptionBilling.next_charge_at < today,
            SubscriptionBilling.status.in_(["inadimplente", "ativa"]),
        )
        .all()
    )
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
    subs_proximas = (
        db.query(SubscriptionBilling, Tenant)
        .join(Tenant, Tenant.id == SubscriptionBilling.tenant_id)
        .filter(
            SubscriptionBilling.next_charge_at.isnot(None),
            SubscriptionBilling.next_charge_at >= today,
            SubscriptionBilling.next_charge_at <= end_15d,
        )
        .order_by(SubscriptionBilling.next_charge_at.asc())
        .all()
    )
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

    # Visitantes vitrine /loja — IPs únicos por tipo (HUMANO, BOT, CLOUD). Calendário "hoje" em America/Sao_Paulo.
    now_utc = datetime.now(timezone.utc)
    today_br = now_utc.astimezone(TZ_BR).date()
    inicio_hoje_br = datetime.combine(today_br, datetime.min.time()).replace(tzinfo=TZ_BR).astimezone(timezone.utc)
    since_7d = now_utc - timedelta(days=7)
    since_30d = now_utc - timedelta(days=30)

    visitantes_hoje_dict = _visitantes_vitrine_por_tipo(db, inicio_hoje_br)
    visitantes_vitrine = {
        "hoje": visitantes_hoje_dict,
        "ultimos_7_dias": _visitantes_vitrine_por_tipo(db, since_7d),
        "ultimos_30_dias": _visitantes_vitrine_por_tipo(db, since_30d),
    }

    return {
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
