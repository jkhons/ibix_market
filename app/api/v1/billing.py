# PDV Ibix - Billing (assinatura, pay-now, my-payments, webhook genérico)
# Mercado Pago: my-subscription, pay-now, my-payments; webhook MP em app.api.webhooks_mercadopago.
import hashlib
import hmac
import json
import os
import time
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.billing_config import get_valor_mensal_centavos
from ...core.logging import log_error, log_struct
from ...core.middleware import get_current_user
from ...core.scope import resolve_tenant_pagador
from ...database.connection import get_db
from ...models import BillingEvent, Module, Payment, SubscriptionBilling, Tenant, TenantEntitlement
from ...models.caixa import Caixa
from ...models.empresa import Empresa
from ...models.usuario import Usuario
from ...schemas.billing import MySubscriptionResponse, PaymentListItem, PayNowResponse, PrecoVigenteBillingResponse
from ...schemas.contrato_comercial import MeusLimitesResponse
from ...services import billing_service

router = APIRouter(prefix="/billing", tags=["Billing"])


class WebhookPayload(BaseModel):
    """Payload genérico do webhook (gateway)."""
    webhook_id: str
    event_type: Optional[str] = None
    payload: Optional[dict] = None


def _verify_signature(payload_body: bytes, signature: Optional[str], secret: Optional[str]) -> bool:
    """Verifica assinatura HMAC (ex.: HMAC-SHA256). Stub: se secret vazio, aceita."""
    if not secret:
        return True
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature) or hmac.compare_digest(expected, signature)


REPLAY_MAX_AGE_SEC = 300  # 5 min


def _today() -> date:
    return date.today()


def _get_tenant_subscription(db: Session, tenant_id: int) -> Optional[SubscriptionBilling]:
    return (
        db.query(SubscriptionBilling)
        .filter(SubscriptionBilling.tenant_id == tenant_id)
        .first()
    )


def _ensure_ca_tenant_and_subscription(
    db: Session,
    current_user: Usuario,
    brand_id: int,
) -> Optional[int]:
    """Se o usuário é CA sem tenant_id, cria Tenant e associa; se tenant não tem subscription, cria trial. Retorna tenant_id ou None."""
    from app.services.brand_scope_service import generate_unique_tenant_slug

    role_nome = current_user.role.nome if current_user.role else None
    tenant_id = resolve_tenant_pagador(db, current_user.id, role_nome)
    if role_nome == "Cliente Administrador" and tenant_id is None:
        user = db.query(Usuario).filter(Usuario.id == current_user.id).first()
        if not user:
            return None
        slug = generate_unique_tenant_slug(db, f"ca-{user.id}", brand_id)
        tenant = Tenant(
            nome=user.nome or "Assinante",
            slug=slug,
            brand_id=brand_id,
            ativo=True,
        )
        db.add(tenant)
        db.flush()
        user.tenant_id = tenant.id
        db.commit()
        db.refresh(user)
        tenant_id = tenant.id
    if tenant_id:
        sub = _get_tenant_subscription(db, tenant_id)
        if not sub:
            billing_service.create_trial_subscription(db, tenant_id)
            db.commit()
    return tenant_id


@router.get("/my-subscription", response_model=MySubscriptionResponse)
def get_my_subscription(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Status da assinatura do tenant do usuário (CA ou tenant do CA para Subcliente/Técnico/Contador)."""
    from app.services.brand_scope_service import brand_id_from_request

    tenant_id = _ensure_ca_tenant_and_subscription(
        db, current_user, brand_id_from_request(request, db)
    )
    if not tenant_id:
        return MySubscriptionResponse(
            server_today=_today(),
            status="none",
            grace_days=15,
            trial_days_left=None,
            grace_days_left=None,
            is_in_trial=False,
            is_past_due=False,
            is_blocked=False,
            valor_mensal_centavos=None,
            valor_exibicao=None,
        )
    sub = _get_tenant_subscription(db, tenant_id)
    if not sub:
        return MySubscriptionResponse(
            server_today=_today(),
            status="none",
            grace_days=15,
            trial_days_left=None,
            grace_days_left=None,
            is_in_trial=False,
            is_past_due=False,
            is_blocked=False,
            valor_mensal_centavos=None,
            valor_exibicao=None,
        )
    today = _today()
    trial_days_left = None
    grace_days_left = None
    if sub.period_end:
        if sub.status == "trial":
            trial_days_left = max(0, (sub.period_end - today).days)
        if sub.status == "inadimplente" and sub.next_charge_at:
            grace_limit = sub.next_charge_at + timedelta(days=sub.grace_days or 15)
            grace_days_left = max(0, (grace_limit - today).days)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    is_blocked = tenant is not None and not tenant.ativo
    # Valor vigente: calculado (com desconto por escopo). Detalhe para exibir valor base, desconto e total.
    valor_centavos = billing_service.get_valor_centavos_para_tenant(db, tenant_id)
    valor_exibicao = "R$ {:.2f}".format(valor_centavos / 100.0)
    from ...core.billing_config import get_desconto_percent, get_valor_mensal_centavos
    valor_base = get_valor_mensal_centavos(db)
    pct = get_desconto_percent(db)
    tem_desconto = billing_service._tenant_tem_desconto(db, tenant_id) and pct and pct > 0
    valor_base_exibicao = "R$ {:.2f}".format(valor_base / 100.0) if valor_base else None
    desconto_percent = pct if tem_desconto else None
    valor_com_desconto_exibicao = valor_exibicao
    return MySubscriptionResponse(
        server_today=today,
        status=sub.status,
        period_end=sub.period_end,
        next_charge_at=sub.next_charge_at,
        grace_days=sub.grace_days or 15,
        trial_days_left=trial_days_left,
        grace_days_left=grace_days_left,
        is_in_trial=(sub.status == "trial"),
        is_past_due=(sub.status == "inadimplente"),
        is_blocked=is_blocked,
        valor_mensal_centavos=valor_centavos,
        valor_exibicao=valor_exibicao,
        valor_base_centavos=valor_base,
        valor_base_exibicao=valor_base_exibicao,
        desconto_percent=desconto_percent,
        valor_com_desconto_centavos=valor_centavos,
        valor_com_desconto_exibicao=valor_com_desconto_exibicao,
    )


@router.get("/meus-limites", response_model=MeusLimitesResponse)
def get_meus_limites(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna limites de PDVs contratados vs usados para o tenant do usuário."""
    from app.services.brand_scope_service import brand_id_from_request

    tenant_id = _ensure_ca_tenant_and_subscription(
        db, current_user, brand_id_from_request(request, db)
    )
    if not tenant_id:
        return MeusLimitesResponse(
            max_pdvs=0, pdvs_usados=0, pdvs_disponiveis=0,
            valor_mensal_centavos=0, valor_exibicao="R$ 0,00", pode_criar_pdv=False,
        )
    sub = _get_tenant_subscription(db, tenant_id)
    max_pdvs = sub.qtd_pdvs_contratados if sub else 1

    from ...core.scope import get_allowed_cliente_ids
    role_nome = current_user.role.nome if current_user.role else None
    cliente_ids = get_allowed_cliente_ids(db, current_user.id, role_nome)
    if not cliente_ids and role_nome == "Superadministrador":
        pdvs_usados = db.query(Caixa).count()
    elif cliente_ids:
        pdvs_usados = (
            db.query(Caixa)
            .join(Empresa, Empresa.id == Caixa.empresa_id)
            .filter(Empresa.cliente_id.in_(cliente_ids))
            .count()
        )
    else:
        pdvs_usados = 0

    valor = billing_service.get_valor_centavos_para_tenant(db, tenant_id)
    return MeusLimitesResponse(
        max_pdvs=max_pdvs,
        pdvs_usados=pdvs_usados,
        pdvs_disponiveis=max(0, max_pdvs - pdvs_usados),
        valor_mensal_centavos=valor,
        valor_exibicao="R$ {:.2f}".format(valor / 100.0) if valor else "R$ 0,00",
        pode_criar_pdv=True,
    )


@router.get("/preco-vigente", response_model=PrecoVigenteBillingResponse)
def get_preco_vigente(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Preço de referência para exibição em /planos. Mesma origem que /admin/billing/preco (billing_config)."""
    valor_base = get_valor_mensal_centavos(db)
    return PrecoVigenteBillingResponse(
        valor_base_centavos=valor_base,
        valor_pdv_adicional_centavos=0,
    )


@router.post("/pay-now", response_model=PayNowResponse)
def post_pay_now(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Gera preferência Checkout Pro e retorna init_point e preference_id. Mensalidade zero renova sem Mercado Pago."""
    from app.services.brand_scope_service import brand_id_from_request

    tenant_id = _ensure_ca_tenant_and_subscription(
        db, current_user, brand_id_from_request(request, db)
    )
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant de cobrança não identificado.")
    try:
        init_point, preference_id = billing_service.create_checkout_preference(
            db, tenant_id, payer_user_id=current_user.id, payer_email=current_user.email
        )
    except Exception as e:
        msg = str(e).strip() or "Falha ao conectar ao Mercado Pago."
        log_struct("pay_now_error", level="warning", error=msg, user_id=current_user.id)
        if "401" in msg or "token" in msg.lower() or "unauthorized" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Access Token do Mercado Pago inválido ou expirado. Configure em Cobranças (Admin) > Config.",
            )
        if "Mercado Pago" in msg:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=msg)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível gerar o link de pagamento. Verifique Cobranças (Admin) > Config (Access Token e APP_URL). Detalhe: " + msg[:150],
        )
    if not init_point and not preference_id and billing_service.get_valor_centavos_para_tenant(db, tenant_id) <= 0:
        from ...core.redis_cache import invalidate_subscription_blocked_all

        invalidate_subscription_blocked_all()
        return PayNowResponse(
            isento=True,
            message="Sua assinatura está isenta de mensalidade. O período foi renovado sem cobrança pelo Mercado Pago.",
        )
    return PayNowResponse(init_point=init_point or "", preference_id=preference_id or "")


@router.get("/my-payments", response_model=List[PaymentListItem])
def get_my_payments(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista pagamentos da assinatura do tenant (somente leitura)."""
    role_nome = current_user.role.nome if current_user.role else None
    tenant_id = resolve_tenant_pagador(db, current_user.id, role_nome)
    if not tenant_id:
        return []
    sub = _get_tenant_subscription(db, tenant_id)
    if not sub:
        return []
    rows = (
        db.query(Payment)
        .filter(Payment.subscription_id == sub.id)
        .order_by(Payment.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [
        PaymentListItem(
            id=p.id,
            mp_payment_id=p.mp_payment_id,
            status=p.status,
            amount_centavos=p.amount_centavos,
            paid_at=p.paid_at,
            created_at=p.created_at,
        )
        for p in rows
    ]


@router.post("/webhook")
async def billing_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_id: Optional[str] = Header(None, alias="X-Webhook-Id"),
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_webhook_timestamp: Optional[str] = Header(None, alias="X-Webhook-Timestamp"),
):
    """
    Recebe webhook do gateway de pagamento.
    Idempotência por X-Webhook-Id; assinatura por X-Webhook-Signature ou X-Hub-Signature-256; replay por X-Webhook-Timestamp.
    """
    body = await request.body()
    signature = x_webhook_signature or x_hub_signature_256
    webhook_id = x_webhook_id
    if not webhook_id and body:
        try:
            import json
            data = json.loads(body)
            webhook_id = data.get("webhook_id") or data.get("id") or data.get("event_id")
        except Exception:
            pass
    if not webhook_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="webhook_id ou X-Webhook-Id obrigatório")

    # Idempotência
    existing = db.query(BillingEvent).filter(BillingEvent.webhook_id == webhook_id).first()
    if existing:
        return {"status": "already_processed", "webhook_id": webhook_id}

    # Replay protection (timestamp opcional)
    if x_webhook_timestamp:
        try:
            ts = int(x_webhook_timestamp)
            if abs(time.time() - ts) > REPLAY_MAX_AGE_SEC:
                log_struct(
                    "webhook replay ou timestamp inválido",
                    level="warning",
                    request_id=getattr(request.state, "request_id", None),
                    webhook_id=webhook_id,
                )
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="timestamp fora da janela")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Webhook-Timestamp inválido")

    secret = os.getenv("WEBHOOK_BILLING_SECRET")
    if not _verify_signature(body, signature, secret):
        event = BillingEvent(
            webhook_id=webhook_id,
            payload=body.decode("utf-8", errors="replace")[:2000],
            assinatura_recebida=(signature[:256] if signature else None),
            status="erro",
            erro_detalhe="assinatura inválida",
        )
        db.add(event)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida")

    event = BillingEvent(
        webhook_id=webhook_id,
        payload=body.decode("utf-8", errors="replace")[:2000],
        assinatura_recebida=(signature[:256] if signature else None),
        status="recebido",
    )
    db.add(event)
    db.commit()

    # Atualizar tenant / entitlements conforme payload (melhores práticas: não falhar resposta do webhook)
    try:
        _process_billing_payload(db, body, webhook_id, request)
    except Exception as e:
        log_struct(
            "billing webhook process payload error",
            level="error",
            webhook_id=webhook_id,
            error=str(e),
        )
        log_error("billing webhook payload process", exc_info=e)

    return {"status": "received", "webhook_id": webhook_id}


def _process_billing_payload(db: Session, body: bytes, webhook_id: str, request: Request) -> None:
    """
    Interpreta payload do gateway e atualiza Tenant + TenantEntitlement.
    Convenção de payload (gateway):
      - external_id (str): ID do tenant no gateway; ou tenant_id (int) para tenant existente.
      - tenant_name (str, opcional): nome do tenant ao criar.
      - plan_id (int, opcional): ID do plano.
      - module_ids (list[int]): IDs dos módulos a ativar.
      - event_type (str, opcional): ex. subscription.activated, subscription.updated.
    Se external_id não existir, cria Tenant. Para cada module_id, upsert TenantEntitlement (ativo).
    """
    if not body:
        return
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return
    external_id = data.get("external_id")
    tenant_id = data.get("tenant_id")
    tenant_name = data.get("tenant_name") or "Tenant"
    plan_id = data.get("plan_id")
    module_ids = data.get("module_ids") or []
    if not isinstance(module_ids, list):
        module_ids = []

    tenant = None
    if tenant_id is not None and isinstance(tenant_id, int):
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None and external_id:
        tenant = db.query(Tenant).filter(Tenant.external_id == external_id).first()
        if tenant is None:
            from app.services.brand_scope_service import generate_unique_tenant_slug, get_ibix_brand_id

            ibix_brand_id = get_ibix_brand_id(db)
            slug_base = (external_id or "").replace(".", "_")[:100] or "tenant"
            slug = generate_unique_tenant_slug(db, slug_base, ibix_brand_id)
            tenant = Tenant(
                nome=tenant_name[:255],
                slug=slug,
                brand_id=ibix_brand_id,
                external_id=external_id[:128] if isinstance(external_id, str) else str(external_id),
                ativo=True,
                plan_id=plan_id,
            )
            db.add(tenant)
            db.flush()
            try:
                from ...services import billing_service
                billing_service.create_trial_subscription(db, tenant.id)
            except Exception:
                pass
        elif plan_id is not None:
            tenant.plan_id = plan_id

    if tenant is None:
        return

    today = date.today()
    for mid in module_ids:
        if not isinstance(mid, int):
            continue
        if db.query(Module).filter(Module.id == mid).first() is None:
            continue
        ent = (
            db.query(TenantEntitlement)
            .filter(
                TenantEntitlement.tenant_id == tenant.id,
                TenantEntitlement.module_id == mid,
            )
            .first()
        )
        if ent:
            ent.status = "ativo"
            ent.vigencia_inicio = ent.vigencia_inicio or today
        else:
            db.add(
                TenantEntitlement(
                    tenant_id=tenant.id,
                    module_id=mid,
                    status="ativo",
                    vigencia_inicio=today,
                )
            )
    db.commit()
