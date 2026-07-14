# PDV Ibix - Admin Billing (Super Admin): tenants, tenant detail, create-charge, block, unblock, config, comissões
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.audit import audit_action
from app.core.convite_lojista_email_template import (
    get_convite_lojista_template_effective_html,
    set_convite_lojista_template_html,
)
from app.core.billing_config import (
    CHAVE_APP_URL,
    CHAVE_DESCONTO_ESCOPO,
    CHAVE_DESCONTO_PERCENT,
    CHAVE_DESCONTO_TENANT_IDS,
    CHAVE_MP_ACCESS_TOKEN,
    CHAVE_MP_WEBHOOK_SECRET,
    CHAVE_PLATAFORMA_PAGARME_SECRET_KEY,
    CHAVE_PLATAFORMA_PAGBANK_ACCESS_TOKEN,
    CHAVE_VALOR_APLICAR_A,
    CHAVE_VALOR_MENSAL_CENTAVOS,
    get_app_url,
    get_desconto_escopo,
    get_desconto_percent,
    get_desconto_tenant_ids,
    get_mp_access_token,
    get_mp_webhook_secret,
    get_plataforma_pagarme_secret_key,
    get_plataforma_pagbank_access_token,
    get_valor_aplicar_a,
    get_valor_mensal_centavos,
)
from app.core.middleware import require_superadmin
from app.core.platform_novo_ca_config import (
    CHAVE_NOVO_CA_EMAIL_ENABLED,
    CHAVE_NOVO_CA_IN_APP_ENABLED,
    get_novo_ca_email_enabled,
    get_novo_ca_in_app_enabled,
    upsert_config_bool,
)
from app.core.payment_gateway_policy import (
    CHAVE_PAYMENT_LOJAS_GATEWAY_SELF_SERVICE,
    payment_lojas_gateway_self_service_enabled,
)
from app.core.scope import get_cliente_ids_for_tenant
from app.database.connection import get_db
from app.integrations.mercadopago import MercadoPagoClient
from app.models import Brand, Caixa, Configuracao, Empresa, MarketplaceTaxaRegra, Payment, SubscriptionBilling, Tenant, Usuario
from app.models.codigo_desconto import CodigoDesconto
from app.models.contrato_comercial import ContratoComercial
from app.models.subscription_billing import ComissaoAdministrador
from app.schemas.billing import (
    AdminBillingConfigRequest,
    AdminBillingConfigResponse,
    AdminBillingConfigValidateResponse,
    AdminBillingPrecoRequest,
    AdminBillingPrecoResponse,
    AdminTenantBillingListItem,
    PayNowResponse,
)
from app.schemas.marketplace_taxa import (
    MarketplaceTaxaRegraAdminResponse,
    MarketplaceTaxaRegraCreateRequest,
    MarketplaceTaxaRegraUpdateRequest,
    payload_from_db_str,
    payload_to_json_str,
)
from app.services import billing_service
from app.services.brand_scope_service import assert_tenant_in_admin_brand_scope, resolve_admin_brand_scope
from app.services.platform_novo_ca_notify_service import enviar_convite_cadastro_lojista
from app.services.marketplace_taxa_service import (
    validar_unica_geral_ativa,
    validar_unico_tenant_ativo,
)


def _normalize_billing_app_url(value: str) -> str:
    """Garante esquema http(s) para APP_URL (URLs absolutas sem esquema são inválidas para convites e gateways)."""
    raw = (value or "").strip().rstrip("/")
    if not raw:
        return ""
    low = raw.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        raw = "https://" + raw.lstrip("/")
    return raw.rstrip("/")


router = APIRouter(prefix="/admin/billing", tags=["Admin Billing"])


class LimitePdvsRequest(BaseModel):
    """Body para PATCH limite de PDVs do tenant."""

    qtd_pdvs_contratados: int = Field(..., ge=1, description="Quantidade de PDVs contratados")


def _get_sub(db: Session, tenant_id: int) -> Optional[SubscriptionBilling]:
    return (
        db.query(SubscriptionBilling)
        .filter(SubscriptionBilling.tenant_id == tenant_id)
        .first()
    )


def _require_tenant_in_admin_scope(db: Session, tenant_id: int, request: Request) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    assert_tenant_in_admin_brand_scope(db, tenant, request)
    return tenant


def _pdvs_em_uso_tenant(db: Session, tenant_id: int) -> int:
    """Contagem de caixas lógicos dos estabelecimentos do tenant (substitui PDVs físicos)."""
    cliente_ids = get_cliente_ids_for_tenant(db, tenant_id)
    if not cliente_ids:
        return 0
    return (
        db.query(Caixa)
        .join(Empresa, Empresa.id == Caixa.empresa_id)
        .filter(Empresa.cliente_id.in_(cliente_ids))
        .count()
    )


@router.get("/tenants", response_model=List[AdminTenantBillingListItem])
def admin_list_tenants(
    request: Request,
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
    brand_id: Optional[int] = Query(None, description="Recorte por marca (tenants.brand_id)"),
    page: int = 1,
    per_page: int = 50,
    apenas_com_ca: bool = False,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Lista tenants com status de assinatura (Super Admin).
    apenas_com_ca=True: apenas tenants que possuem pelo menos um usuário com role Cliente Administrador (C);
    exclui tenants sem CA (evita listar CF ou outros). Usado no select 'Específico' da página Valor e descontos."""
    effective_brand = resolve_admin_brand_scope(request, db, brand_id)
    today = date.today()
    query = db.query(Tenant).order_by(Tenant.id)
    if effective_brand is not None:
        query = query.filter(Tenant.brand_id == effective_brand)
    if q:
        query = query.filter(Tenant.nome.ilike(f"%{q}%"))
    if apenas_com_ca:
        from app.models.role import Role
        role_ca = db.query(Role).filter(Role.nome == "Cliente Administrador").first()
        if role_ca:
            subq = (
                db.query(Usuario.tenant_id)
                .filter(Usuario.tenant_id.isnot(None), Usuario.role_id == role_ca.id)
                .distinct()
            )
            query = query.filter(Tenant.id.in_(subq))
        # Lista completa para select Específico (apenas C, sem CF)
        limit_especifico = min(per_page, 10000) if per_page else 10000
        tenants = query.limit(limit_especifico).all()
    else:
        tenants = query.offset((page - 1) * per_page).limit(per_page).all()
    out = []
    for t in tenants:
        sub = _get_sub(db, t.id)
        sub_status = sub.status if sub else "none"
        if status_filter and sub_status != status_filter:
            continue
        period_end = sub.period_end if sub else None
        next_charge = sub.next_charge_at if sub else None
        days_overdue = None
        if next_charge and sub and sub.status in ("inadimplente", "ativa"):
            days_overdue = (today - next_charge).days if today > next_charge else 0
        out.append(
            AdminTenantBillingListItem(
                tenant_id=t.id,
                tenant_nome=t.nome or "",
                subscription_status=sub_status,
                period_end=period_end,
                next_charge_at=next_charge,
                days_overdue=days_overdue,
                ativo=t.ativo,
            )
        )
    return out


@router.get("/tenant/{tenant_id}")
def admin_tenant_detail(
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Detalhe do tenant: assinatura e pagamentos."""
    tenant = _require_tenant_in_admin_scope(db, tenant_id, request)
    sub = _get_sub(db, tenant_id)
    pdvs_em_uso = _pdvs_em_uso_tenant(db, tenant_id)
    payments = []
    if sub:
        payments = (
            db.query(Payment)
            .filter(Payment.subscription_id == sub.id)
            .order_by(Payment.created_at.desc())
            .limit(50)
            .all()
        )
    return {
        "tenant_id": tenant.id,
        "tenant_nome": tenant.nome,
        "ativo": tenant.ativo,
        "subscription": {
            "id": sub.id,
            "status": sub.status,
            "period_end": sub.period_end.isoformat() if sub.period_end else None,
            "next_charge_at": sub.next_charge_at.isoformat() if sub.next_charge_at else None,
            "grace_days": sub.grace_days,
            "qtd_pdvs_contratados": sub.qtd_pdvs_contratados if sub else 1,
            "valor_mensal_centavos": sub.valor_mensal_centavos if sub else 0,
            "pdvs_em_uso": pdvs_em_uso,
        } if sub else {
            "id": None,
            "status": "none",
            "period_end": None,
            "next_charge_at": None,
            "grace_days": None,
            "qtd_pdvs_contratados": 1,
            "valor_mensal_centavos": 0,
            "pdvs_em_uso": pdvs_em_uso,
        },
        "payments": [
            {
                "id": p.id,
                "mp_payment_id": p.mp_payment_id,
                "status": p.status,
                "amount_centavos": p.amount_centavos,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            }
            for p in payments
        ],
    }


@router.patch("/tenant/{tenant_id}/limite-pdvs")
def admin_patch_limite_pdvs(
    tenant_id: int,
    request: Request,
    body: LimitePdvsRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Altera o limite de PDVs contratados do tenant (SuperAdmin). Não permite reduzir abaixo de pdvs_em_uso."""
    _require_tenant_in_admin_scope(db, tenant_id, request)
    pdvs_em_uso = _pdvs_em_uso_tenant(db, tenant_id)
    if body.qtd_pdvs_contratados < pdvs_em_uso:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível reduzir o limite abaixo de {pdvs_em_uso} (PDVs em uso).",
        )
    sub = _get_sub(db, tenant_id)
    if not sub:
        sub = billing_service.create_trial_subscription(db, tenant_id)
    sub.qtd_pdvs_contratados = body.qtd_pdvs_contratados
    db.commit()
    db.refresh(sub)
    audit_action(
        db,
        "limite_pdvs_alterado",
        user_id=current_user.id,
        tenant_id=tenant_id,
        recurso_tipo="subscription",
        recurso_id=sub.id,
        detalhes=f"qtd_pdvs_contratados={body.qtd_pdvs_contratados}",
    )
    return {
        "tenant_id": tenant_id,
        "qtd_pdvs_contratados": sub.qtd_pdvs_contratados,
        "pdvs_em_uso": pdvs_em_uso,
    }


@router.post("/tenant/{tenant_id}/create-charge", response_model=PayNowResponse)
def admin_create_charge(
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Gera preferência Checkout Pro para o tenant (copiar link)."""
    _require_tenant_in_admin_scope(db, tenant_id, request)
    init_point, preference_id = billing_service.create_checkout_preference(db, tenant_id)
    if not init_point and not preference_id and billing_service.get_valor_centavos_para_tenant(db, tenant_id) <= 0:
        return PayNowResponse(
            isento=True,
            message="Tenant com mensalidade zero; período renovado sem Mercado Pago.",
        )
    return PayNowResponse(init_point=init_point or "", preference_id=preference_id or "")


@router.post("/tenant/{tenant_id}/block")
def admin_block_tenant(
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Seta subscription.status = bloqueada e Tenant.ativo = False."""
    from datetime import datetime
    tenant = _require_tenant_in_admin_scope(db, tenant_id, request)
    sub = _get_sub(db, tenant_id)
    if sub:
        sub.status = "bloqueada"
        sub.blocked_at = datetime.utcnow()
    tenant.ativo = False
    db.commit()
    audit_action(
        db,
        "tenant_bloqueado",
        user_id=current_user.id,
        tenant_id=tenant_id,
        recurso_tipo="tenant",
        recurso_id=tenant_id,
        detalhes=f"tenant_nome={tenant.nome or ''}",
    )
    from app.core.redis_cache import invalidate_subscription_blocked_all
    invalidate_subscription_blocked_all()
    return {"status": "ok", "message": "Tenant bloqueado"}


@router.post("/tenant/{tenant_id}/unblock")
def admin_unblock_tenant(
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Seta Tenant.ativo = True e subscription.status = inadimplente ou ativa."""
    tenant = _require_tenant_in_admin_scope(db, tenant_id, request)
    sub = _get_sub(db, tenant_id)
    if sub and sub.status == "bloqueada":
        sub.status = "inadimplente"
        sub.blocked_at = None
    tenant.ativo = True
    db.commit()
    audit_action(
        db,
        "tenant_desbloqueado",
        user_id=current_user.id,
        tenant_id=tenant_id,
        recurso_tipo="tenant",
        recurso_id=tenant_id,
        detalhes=f"tenant_nome={tenant.nome or ''}",
    )
    from app.core.redis_cache import invalidate_subscription_blocked_all
    invalidate_subscription_blocked_all()
    return {"status": "ok", "message": "Tenant desbloqueado"}


def _upsert_config(db: Session, chave: str, valor: str, descricao: str = "") -> None:
    from app.core.billing_secrets import encrypt_stored_secret, is_billing_secret_key

    stored = valor
    if is_billing_secret_key(chave):
        stored = encrypt_stored_secret(valor)
    row = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if row:
        row.valor = stored
        if descricao:
            row.descricao = descricao
    else:
        db.add(Configuracao(chave=chave, valor=stored, descricao=descricao or chave))


def _mask_secret(value: Optional[str], prefix_len: int = 8, suffix_len: int = 4) -> Optional[str]:
    """Retorna valor mascarado (ex.: APP_US***...***730) para exibição no front."""
    if not value or not str(value).strip():
        return None
    s = str(value).strip()
    if len(s) <= prefix_len + suffix_len:
        return "••••••" if s else None
    return f"{s[:prefix_len]}...{s[-suffix_len:]}"


def _billing_config_response(db: Session) -> AdminBillingConfigResponse:
    """Monta resposta de config billing — segredos só mascarados (Fase 4 LGPD)."""
    from app.core.pagbank_config import get_pagbank_client_id, get_pagbank_client_secret, is_pagbank_sandbox

    token = get_mp_access_token(db)
    secret = get_mp_webhook_secret(db)
    app_url = get_app_url(db)
    try:
        pb_client_id = get_pagbank_client_id(db)
    except ValueError:
        pb_client_id = ""
    try:
        pb_client_secret = get_pagbank_client_secret(db)
    except ValueError:
        pb_client_secret = ""
    pb_sandbox = is_pagbank_sandbox(db)
    plat_pb = get_plataforma_pagbank_access_token(db)
    plat_pg = get_plataforma_pagarme_secret_key(db)
    lojas_gateway = payment_lojas_gateway_self_service_enabled(db)
    return AdminBillingConfigResponse(
        mp_configured=bool(token),
        app_url=app_url or None,
        mp_access_token_masked=_mask_secret(token),
        mp_webhook_secret_masked=_mask_secret(secret),
        mp_access_token=None,
        mp_webhook_secret=None,
        pagbank_configured=bool(pb_client_id and pb_client_secret),
        pagbank_client_id_masked=_mask_secret(pb_client_id),
        pagbank_client_id=pb_client_id or None,
        pagbank_client_secret_masked=_mask_secret(pb_client_secret),
        pagbank_sandbox=pb_sandbox,
        plataforma_pagbank_configured=bool(plat_pb),
        plataforma_pagbank_access_token_masked=_mask_secret(plat_pb),
        plataforma_pagbank_access_token=None,
        plataforma_pagarme_configured=bool(plat_pg),
        plataforma_pagarme_secret_key_masked=_mask_secret(plat_pg),
        plataforma_pagarme_secret_key=None,
        payment_lojas_gateway_self_service=lojas_gateway,
    )


@router.get("/config", response_model=AdminBillingConfigResponse)
def admin_get_config(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Retorna status, app_url e valores mascarados de tokens (segredos nunca em claro na resposta)."""
    return _billing_config_response(db)


@router.get("/config/validate", response_model=AdminBillingConfigValidateResponse)
async def admin_validate_mp_config(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Valida o token do Mercado Pago com uma chamada real à API. Só 'Conectado' quando mp_valid=True."""
    token = get_mp_access_token(db)
    if not token:
        return AdminBillingConfigValidateResponse(mp_valid=False, mp_message="Token não configurado")
    client = MercadoPagoClient(access_token=token)
    valid, message = await client.validate_token()
    return AdminBillingConfigValidateResponse(mp_valid=valid, mp_message=message or None)


@router.post("/config", response_model=AdminBillingConfigResponse)
def admin_post_config(
    body: AdminBillingConfigRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_superadmin()),
):
    """Salva configuração na tabela configuracoes (chaves billing_* e payment_pagbank_*). Valores em branco removem o override (passa a usar .env)."""
    from app.core.pagbank_config import get_pagbank_client_id, get_pagbank_client_secret, is_pagbank_sandbox
    CHAVE_PB_CLIENT_ID = "payment_pagbank_connect_client_id"
    CHAVE_PB_CLIENT_SECRET = "payment_pagbank_connect_client_secret"
    CHAVE_PB_SANDBOX = "payment_pagbank_connect_sandbox"

    if body.mp_access_token is not None:
        if body.mp_access_token.strip():
            _upsert_config(db, CHAVE_MP_ACCESS_TOKEN, body.mp_access_token.strip(), "Mercado Pago Access Token (billing)")
        else:
            db.query(Configuracao).filter(Configuracao.chave == CHAVE_MP_ACCESS_TOKEN).delete()
    if body.mp_webhook_secret is not None:
        if body.mp_webhook_secret.strip():
            _upsert_config(db, CHAVE_MP_WEBHOOK_SECRET, body.mp_webhook_secret.strip(), "Mercado Pago Webhook Secret (billing)")
        else:
            db.query(Configuracao).filter(Configuracao.chave == CHAVE_MP_WEBHOOK_SECRET).delete()
    if body.app_url is not None:
        norm_url = _normalize_billing_app_url(body.app_url)
        if norm_url:
            _upsert_config(db, CHAVE_APP_URL, norm_url, "URL base da aplicação (billing)")
        else:
            db.query(Configuracao).filter(Configuracao.chave == CHAVE_APP_URL).delete()
    if body.pagbank_client_id is not None:
        if body.pagbank_client_id.strip():
            _upsert_config(db, CHAVE_PB_CLIENT_ID, body.pagbank_client_id.strip(), "PagBank Connect Client ID (OAuth)")
        else:
            db.query(Configuracao).filter(Configuracao.chave == CHAVE_PB_CLIENT_ID).delete()
    if body.pagbank_client_secret is not None:
        if body.pagbank_client_secret.strip():
            _upsert_config(db, CHAVE_PB_CLIENT_SECRET, body.pagbank_client_secret.strip(), "PagBank Connect Client Secret (OAuth)")
        else:
            db.query(Configuracao).filter(Configuracao.chave == CHAVE_PB_CLIENT_SECRET).delete()
    if body.pagbank_sandbox is not None:
        _upsert_config(db, CHAVE_PB_SANDBOX, "true" if body.pagbank_sandbox else "false", "PagBank Connect Sandbox mode")
    if body.plataforma_pagbank_access_token is not None:
        if body.plataforma_pagbank_access_token.strip():
            _upsert_config(
                db,
                CHAVE_PLATAFORMA_PAGBANK_ACCESS_TOKEN,
                body.plataforma_pagbank_access_token.strip(),
                "PagBank access token (checkout marketplace modo plataforma)",
            )
        else:
            db.query(Configuracao).filter(Configuracao.chave == CHAVE_PLATAFORMA_PAGBANK_ACCESS_TOKEN).delete()
    if body.plataforma_pagarme_secret_key is not None:
        if body.plataforma_pagarme_secret_key.strip():
            _upsert_config(
                db,
                CHAVE_PLATAFORMA_PAGARME_SECRET_KEY,
                body.plataforma_pagarme_secret_key.strip(),
                "Pagar.me secret key (checkout marketplace modo plataforma)",
            )
        else:
            db.query(Configuracao).filter(Configuracao.chave == CHAVE_PLATAFORMA_PAGARME_SECRET_KEY).delete()
    if body.payment_lojas_gateway_self_service is not None:
        _upsert_config(
            db,
            CHAVE_PAYMENT_LOJAS_GATEWAY_SELF_SERVICE,
            "true" if body.payment_lojas_gateway_self_service else "false",
            "Liberado para lojas: Mercado Pago, PagBank e Pagar.me em Recebíveis (CA / Administrador)",
        )
    db.commit()
    audit_action(
        db,
        "billing_config_alterada",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="configuracao",
        detalhes="billing secrets atualizados (valores cifrados em repouso)",
    )
    return _billing_config_response(db)


@router.get("/preco", response_model=AdminBillingPrecoResponse)
def admin_get_preco(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Retorna valor mensal e configuração de descontos (Super Admin)."""
    return AdminBillingPrecoResponse(
        valor_mensal_centavos=get_valor_mensal_centavos(db),
        valor_aplicar_a=get_valor_aplicar_a(db),
        desconto_percent=get_desconto_percent(db),
        desconto_escopo=get_desconto_escopo(db),
        desconto_tenant_ids=get_desconto_tenant_ids(db),
    )


@router.post("/preco", response_model=AdminBillingPrecoResponse)
def admin_post_preco(
    body: AdminBillingPrecoRequest,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Salva valor mensal e descontos (Super Admin)."""
    if body.valor_mensal_centavos is not None and body.valor_mensal_centavos >= 0:
        _upsert_config(
            db, CHAVE_VALOR_MENSAL_CENTAVOS, str(body.valor_mensal_centavos),
            "Valor mensalidade (centavos) - billing",
        )
    if body.valor_aplicar_a is not None and body.valor_aplicar_a in ("todos", "novos"):
        _upsert_config(db, CHAVE_VALOR_APLICAR_A, body.valor_aplicar_a, "Aplicar valor a: todos ou novos - billing")
    if body.desconto_percent is not None:
        pct = max(0, min(100, body.desconto_percent))
        _upsert_config(db, CHAVE_DESCONTO_PERCENT, str(pct), "Desconto % - billing")
    if body.desconto_escopo is not None and body.desconto_escopo in ("todos", "ca", "admin_cliente", "especifico"):
        _upsert_config(db, CHAVE_DESCONTO_ESCOPO, body.desconto_escopo, "Escopo desconto - billing")
    if body.desconto_tenant_ids is not None:
        _upsert_config(
            db, CHAVE_DESCONTO_TENANT_IDS, ",".join(str(x) for x in body.desconto_tenant_ids),
            "Tenant IDs com desconto (escopo=especifico) - billing",
        )
    db.commit()
    return AdminBillingPrecoResponse(
        valor_mensal_centavos=get_valor_mensal_centavos(db),
        valor_aplicar_a=get_valor_aplicar_a(db),
        desconto_percent=get_desconto_percent(db),
        desconto_escopo=get_desconto_escopo(db),
        desconto_tenant_ids=get_desconto_tenant_ids(db),
    )


class AplicarValorTodosRequest(BaseModel):
    """Body para POST /preco/aplicar-valor-todos."""

    respeitar_codigos_promocionais: bool = Field(
        True,
        description="True: aplica desconto de código nas assinaturas que têm codigo_desconto_id. False: substitui o valor em todas (ignora códigos).",
    )


@router.post("/preco/aplicar-valor-todos")
def admin_aplicar_valor_todos(
    body: AplicarValorTodosRequest = AplicarValorTodosRequest(),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Atualiza valor_mensal_centavos de todas as assinaturas para o valor configurado (com desconto por escopo).
    respeitar_codigos_promocionais=True: assinaturas com codigo_desconto_id mantêm o desconto sobre o novo base.
    respeitar_codigos_promocionais=False: todas recebem o mesmo valor (ignora códigos). Contrato comercial ativo sempre prevalece."""
    count = 0
    respeitar_codigos = body.respeitar_codigos_promocionais
    for sub in db.query(SubscriptionBilling).all():
        base = billing_service._valor_centavos_para_tenant(db, sub.tenant_id)
        has_contrato = (
            db.query(ContratoComercial)
            .filter(
                ContratoComercial.tenant_id == sub.tenant_id,
                ContratoComercial.status == "ativo",
            )
            .first()
            is not None
        )
        if has_contrato:
            novo_valor = base
        elif respeitar_codigos and getattr(sub, "codigo_desconto_id", None):
            cod = db.query(CodigoDesconto).filter(CodigoDesconto.id == sub.codigo_desconto_id).first()
            if cod and (cod.desconto_mensalidade_percent or 0) > 0:
                pct = cod.desconto_mensalidade_percent
                if pct >= 100:
                    novo_valor = 0
                else:
                    novo_valor = max(1, int(round(base * (1 - pct / 100.0))))
            else:
                novo_valor = base
        else:
            novo_valor = base
        if sub.valor_mensal_centavos != novo_valor:
            sub.valor_mensal_centavos = novo_valor
            count += 1
    if count:
        db.commit()
    return {"status": "ok", "atualizadas": count, "message": f"Atualizadas {count} assinatura(s)."}


# ── Comissões do Administrador (Super Admin) ────────────────────────────────────


class ComissaoAdministradorListItem(BaseModel):
    """Item da listagem de comissões para Super Admin."""

    id: int
    payment_id: int
    usuario_id_administrador: int
    administrador_nome: Optional[str] = None
    valor_mensalidade_centavos: int
    percentual_comissao: int
    valor_comissao_centavos: int
    status: str
    created_at: Optional[str] = None
    pago_em: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/comissoes", response_model=List[ComissaoAdministradorListItem])
def admin_list_comissoes(
    status_filter: Optional[str] = Query(None, description="pendente | pago"),
    usuario_id_administrador: Optional[int] = Query(None, description="Filtrar por Administrador"),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Lista comissões do Administrador (Super Admin). Filtros opcionais: status, usuario_id_administrador."""
    q = db.query(ComissaoAdministrador).order_by(ComissaoAdministrador.created_at.desc())
    if status_filter in ("pendente", "pago"):
        q = q.filter(ComissaoAdministrador.status == status_filter)
    if usuario_id_administrador is not None:
        q = q.filter(ComissaoAdministrador.usuario_id_administrador == usuario_id_administrador)
    rows = q.all()
    admin_ids = list({r.usuario_id_administrador for r in rows})
    admin_names = {}
    if admin_ids:
        for u in db.query(Usuario.id, Usuario.nome).filter(Usuario.id.in_(admin_ids)).all():
            admin_names[u.id] = u.nome
    out = []
    for r in rows:
        out.append(
            ComissaoAdministradorListItem(
                id=r.id,
                payment_id=r.payment_id,
                usuario_id_administrador=r.usuario_id_administrador,
                administrador_nome=admin_names.get(r.usuario_id_administrador),
                valor_mensalidade_centavos=r.valor_mensalidade_centavos,
                percentual_comissao=r.percentual_comissao,
                valor_comissao_centavos=r.valor_comissao_centavos,
                status=r.status,
                created_at=r.created_at.isoformat() if getattr(r, "created_at", None) else None,
                pago_em=r.pago_em.isoformat() if getattr(r, "pago_em", None) else None,
            )
        )
    return out


class ComissaoMarcarPagoRequest(BaseModel):
    """Body opcional para PATCH comissão (marcar como pago)."""

    status: str = Field("pago", description="Deve ser 'pago' para marcar como pago.")


@router.patch("/comissoes/{comissao_id}", response_model=ComissaoAdministradorListItem)
def admin_marcar_comissao_pago(
    comissao_id: int,
    body: Optional[ComissaoMarcarPagoRequest] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Marca comissão como paga (status=pago, pago_em=now). Apenas Super Admin."""
    reg = db.query(ComissaoAdministrador).filter(ComissaoAdministrador.id == comissao_id).first()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comissão não encontrada")
    reg.status = "pago"
    reg.pago_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(reg)
    audit_action(
        db,
        "comissao_administrador_marcada_pago",
        user_id=current_user.id,
        tenant_id=None,
        recurso_tipo="comissao_administrador",
        recurso_id=reg.id,
    )
    admin_nome = None
    u = db.query(Usuario).filter(Usuario.id == reg.usuario_id_administrador).first()
    if u:
        admin_nome = u.nome
    return ComissaoAdministradorListItem(
        id=reg.id,
        payment_id=reg.payment_id,
        usuario_id_administrador=reg.usuario_id_administrador,
        administrador_nome=admin_nome,
        valor_mensalidade_centavos=reg.valor_mensalidade_centavos,
        percentual_comissao=reg.percentual_comissao,
        valor_comissao_centavos=reg.valor_comissao_centavos,
        status=reg.status,
        created_at=reg.created_at.isoformat() if getattr(reg, "created_at", None) else None,
        pago_em=reg.pago_em.isoformat() if reg.pago_em else None,
    )


def _taxa_regra_admin_response(row: MarketplaceTaxaRegra) -> MarketplaceTaxaRegraAdminResponse:
    return MarketplaceTaxaRegraAdminResponse(
        id=row.id,
        nome=row.nome,
        ativo=bool(row.ativo),
        escopo=row.escopo,
        tenant_id=row.tenant_id,
        payload=payload_from_db_str(row.payload),
    )


@router.get("/marketplace-taxas/regras", response_model=List[MarketplaceTaxaRegraAdminResponse])
def admin_list_marketplace_taxa_regras(
    ativo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Lista regras de taxas marketplace (Super Admin)."""
    q = db.query(MarketplaceTaxaRegra).order_by(MarketplaceTaxaRegra.id.desc())
    if ativo is not None:
        q = q.filter(MarketplaceTaxaRegra.ativo.is_(ativo))
    return [_taxa_regra_admin_response(r) for r in q.all()]


@router.post("/marketplace-taxas/regras", response_model=MarketplaceTaxaRegraAdminResponse, status_code=status.HTTP_201_CREATED)
def admin_create_marketplace_taxa_regra(
    body: MarketplaceTaxaRegraCreateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    if body.escopo == "geral" and body.tenant_id is not None:
        raise HTTPException(status_code=400, detail="Regra Geral não deve ter tenant_id.")
    if body.escopo == "tenant" and body.tenant_id is None:
        raise HTTPException(status_code=400, detail="Regra por tenant exige tenant_id.")
    try:
        validar_unica_geral_ativa(db, body.escopo, body.ativo)
        validar_unico_tenant_ativo(db, body.escopo, body.tenant_id, body.ativo)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    row = MarketplaceTaxaRegra(
        nome=body.nome.strip(),
        ativo=body.ativo,
        escopo=body.escopo,
        tenant_id=body.tenant_id,
        payload=payload_to_json_str(body.payload),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _taxa_regra_admin_response(row)


@router.patch("/marketplace-taxas/regras/{regra_id}", response_model=MarketplaceTaxaRegraAdminResponse)
def admin_patch_marketplace_taxa_regra(
    regra_id: int,
    body: MarketplaceTaxaRegraUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    row = db.query(MarketplaceTaxaRegra).filter(MarketplaceTaxaRegra.id == regra_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    dump = body.model_dump(exclude_unset=True)

    if "nome" in dump and dump["nome"] is not None:
        row.nome = dump["nome"].strip()
    if "ativo" in dump:
        row.ativo = bool(dump["ativo"])
    if "payload" in dump and dump["payload"] is not None:
        row.payload = payload_to_json_str(dump["payload"])

    try:
        validar_unica_geral_ativa(db, row.escopo, bool(row.ativo), exclude_id=regra_id)
        validar_unico_tenant_ativo(db, row.escopo, row.tenant_id, bool(row.ativo), exclude_id=regra_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    db.commit()
    db.refresh(row)
    return _taxa_regra_admin_response(row)


@router.delete("/marketplace-taxas/regras/{regra_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_marketplace_taxa_regra(
    regra_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    """Remove regra (hard delete). Preferível desativar via PATCH ativo=false."""
    row = db.query(MarketplaceTaxaRegra).filter(MarketplaceTaxaRegra.id == regra_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Onboarding plataforma: notificações de novo CA + convite por e-mail ---


class NovoCaNotificacoesConfigResponse(BaseModel):
    """Espelho do que o front de Superadmin exibe (switches)."""

    email_enabled: bool
    in_app_enabled: bool


class NovoCaNotificacoesConfigUpdate(BaseModel):
    email_enabled: bool
    in_app_enabled: bool


_DESCR_NOVO_CA_EMAIL = (
    "Quando true, envia e-mail aos Superadministradores ao concluir cadastro público de lojista (CA)."
)
_DESCR_NOVO_CA_IN_APP = (
    "Quando true, grava notificação no sino (usuario_notificacoes) para cada Superadministrador."
)


@router.get("/onboarding/novo-ca-notificacoes", response_model=NovoCaNotificacoesConfigResponse)
def get_novo_ca_notificacoes_config(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    return NovoCaNotificacoesConfigResponse(
        email_enabled=get_novo_ca_email_enabled(db),
        in_app_enabled=get_novo_ca_in_app_enabled(db),
    )


@router.patch("/onboarding/novo-ca-notificacoes", response_model=NovoCaNotificacoesConfigResponse)
def patch_novo_ca_notificacoes_config(
    body: NovoCaNotificacoesConfigUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    upsert_config_bool(db, CHAVE_NOVO_CA_EMAIL_ENABLED, body.email_enabled, _DESCR_NOVO_CA_EMAIL)
    upsert_config_bool(db, CHAVE_NOVO_CA_IN_APP_ENABLED, body.in_app_enabled, _DESCR_NOVO_CA_IN_APP)
    db.commit()
    return NovoCaNotificacoesConfigResponse(
        email_enabled=get_novo_ca_email_enabled(db),
        in_app_enabled=get_novo_ca_in_app_enabled(db),
    )


class ConviteLojistaTemplateResponse(BaseModel):
    """HTML efetivo do e-mail (arquivo padrão ou override em configuracoes)."""

    html: str
    is_custom: bool


class ConviteLojistaTemplatePatch(BaseModel):
    """Salvar HTML customizado ou restaurar o arquivo padrão."""

    reset_to_default: bool = False
    html: Optional[str] = None


@router.get("/onboarding/convite-lojista-template", response_model=ConviteLojistaTemplateResponse)
def get_convite_lojista_template(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    html, is_custom = get_convite_lojista_template_effective_html(db)
    return ConviteLojistaTemplateResponse(html=html or "", is_custom=is_custom)


@router.patch("/onboarding/convite-lojista-template", response_model=ConviteLojistaTemplateResponse)
def patch_convite_lojista_template(
    body: ConviteLojistaTemplatePatch,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Grava override em `configuracoes` ou remove quando `reset_to_default=true`."""
    try:
        if body.reset_to_default:
            set_convite_lojista_template_html(db, None)
        elif body.html is not None:
            set_convite_lojista_template_html(db, body.html)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe html (string) ou reset_to_default=true.",
            )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    audit_action(
        db,
        "convite_lojista_template_atualizado",
        user_id=current_user.id,
        tenant_id=None,
        recurso_tipo="email_template",
        detalhes="reset" if body.reset_to_default else "custom",
    )
    html, is_custom = get_convite_lojista_template_effective_html(db)
    return ConviteLojistaTemplateResponse(html=html or "", is_custom=is_custom)


class ConviteLojistaRequest(BaseModel):
    """Convite de captação de lojistas (lead): apenas dados do e-mail; link sempre para /cadastro sem código promocional."""

    email: EmailStr
    nome_destinatario: Optional[str] = Field(None, max_length=120)
    mensagem: Optional[str] = Field(None, max_length=2000)


class ConviteLojistaResponse(BaseModel):
    ok: bool
    email: str
    cadastro_url: str


@router.post("/onboarding/convite-lojista", response_model=ConviteLojistaResponse)
def post_convite_lojista(
    body: ConviteLojistaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Envia e-mail de convite com link para /cadastro (captação de lojistas—sem código promocional na URL)."""
    base = (get_app_url(db) or "").strip()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure a URL base da aplicação (APP_URL) em Cobranças > Config antes de enviar convites.",
        )

    ok, cadastro_url, err = enviar_convite_cadastro_lojista(
        db,
        destinatario_email=str(body.email).strip().lower(),
        nome_destinatario=body.nome_destinatario,
        mensagem_personalizada=body.mensagem,
        codigo_promocional=None,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=err or "Falha ao enviar e-mail.")

    audit_action(
        db,
        "convite_cadastro_lojista",
        user_id=current_user.id,
        tenant_id=None,
        recurso_tipo="email",
        detalhes=f"para={str(body.email).strip().lower()}",
    )
    return ConviteLojistaResponse(ok=True, email=str(body.email).strip().lower(), cadastro_url=cadastro_url)
