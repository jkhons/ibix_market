# PDV Ibix - Serviço de cobrança (assinatura, grace policy, preference, webhook, notificações)
import json
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import (
    BillingNotificacao,
    ComissaoAdministrador,
    Empresa,
    Payment,
    SubscriptionBilling,
    Tenant,
    Usuario,
    WebhookEvent,
)
from app.models.codigo_desconto import CodigoDesconto
from app.models.divulgador import Divulgador
from app.models.divulgador_regra import DivulgadorRegra
from app.models.role import Role

# Injeção: cliente MP e app_url (definidos onde o serviço é usado)
_mp_client = None
_app_url = None

TRIAL_DAYS = 30
DEFAULT_GRACE_DAYS = 15
PLANO_CODIGO = "pdv_solumatica_490"
VALOR_MENSAL_CENTAVOS = 49000  # R$ 490,00


def set_billing_dependencies(mp_client: Any, app_url: str) -> None:
    """Injeta cliente Mercado Pago e URL base da aplicação."""
    global _mp_client, _app_url
    _mp_client = mp_client
    _app_url = app_url.rstrip("/") if app_url else ""


def _today() -> date:
    return datetime.utcnow().date()


def _get_mp_client(db: Optional[Session] = None):
    if _mp_client is None:
        from app.core.billing_config import get_mp_access_token
        from app.integrations.mercadopago import MercadoPagoClient
        token = get_mp_access_token(db) or os.getenv("MP_ACCESS_TOKEN") or ""
        return MercadoPagoClient(token)
    return _mp_client


def _get_app_url(db: Optional[Session] = None) -> str:
    from app.core.billing_config import get_app_url as _config_app_url
    return _app_url or _config_app_url(db) or os.getenv("APP_URL") or ""


def _tenant_tem_desconto(db: Session, tenant_id: int) -> bool:
    """Retorna True se o tenant está no escopo do desconto configurado (billing_config)."""
    from app.core.billing_config import (
        get_desconto_escopo,
        get_desconto_tenant_ids,
    )
    escopo = get_desconto_escopo(db)
    if escopo == "todos":
        return True
    if escopo == "especifico":
        return tenant_id in get_desconto_tenant_ids(db)
    if escopo == "ca":
        role_ca = db.query(Role).filter(Role.nome == "Cliente Administrador").first()
        if not role_ca:
            return False
        return db.query(Usuario).filter(
            Usuario.tenant_id == tenant_id,
            Usuario.role_id == role_ca.id,
        ).first() is not None
    if escopo == "admin_cliente":
        role_ac = db.query(Role).filter(Role.nome == "Administrador de Cliente").first()
        if not role_ac:
            return False
        return db.query(Usuario).filter(
            Usuario.tenant_id == tenant_id,
            Usuario.role_id == role_ac.id,
        ).first() is not None
    return False


def _valor_centavos_para_tenant(db: Session, tenant_id: int) -> int:
    """Retorna o valor em centavos a cobrar do tenant.
    Prioridade: contrato comercial ativo > configuração admin (com desconto)."""
    from app.models.contrato_comercial import ContratoComercial
    contrato = (
        db.query(ContratoComercial)
        .filter(ContratoComercial.tenant_id == tenant_id, ContratoComercial.status == "ativo")
        .first()
    )
    if contrato:
        return contrato.valor_mensal_centavos

    from app.core.billing_config import get_desconto_percent, get_valor_mensal_centavos
    base = get_valor_mensal_centavos(db)
    pct = get_desconto_percent(db)
    if pct <= 0 or not _tenant_tem_desconto(db, tenant_id):
        return base
    return max(1, int(round(base * (1 - pct / 100.0))))


def get_valor_centavos_para_tenant(db: Session, tenant_id: int) -> int:
    """Interface pública para obter valor mensal vigente do tenant."""
    return _valor_centavos_para_tenant(db, tenant_id)


def apply_grace_policy(db: Session) -> int:
    """
    Job diário: para assinaturas ativa/inadimplente, se hoje > next_charge_at + grace_days,
    seta status = bloqueada, blocked_at = now e Tenant.ativo = False.
    Retorna quantidade de assinaturas alteradas.
    """
    today = _today()
    subs = (
        db.query(SubscriptionBilling)
        .filter(SubscriptionBilling.status.in_(["ativa", "inadimplente"]))
        .filter(SubscriptionBilling.next_charge_at.isnot(None))
        .all()
    )
    changed = 0
    for sub in subs:
        grace_limit = sub.next_charge_at + timedelta(days=sub.grace_days or 15)
        if today > grace_limit:
            sub.status = "bloqueada"
            sub.blocked_at = datetime.utcnow()
            tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
            if tenant:
                tenant.ativo = False
            changed += 1
    if changed:
        db.commit()
    return changed


def create_trial_subscription(
    db: Session,
    tenant_id: int,
    plano_codigo: str = PLANO_CODIGO,
    valor_centavos: Optional[int] = None,
) -> SubscriptionBilling:
    """
    Cria assinatura em trial (30 dias). Se já existir subscription para o tenant, retorna a existente.
    valor_centavos: se None, usa valor configurado em billing (com desconto por escopo).
    """
    if valor_centavos is None:
        valor_centavos = _valor_centavos_para_tenant(db, tenant_id)
    existing = (
        db.query(SubscriptionBilling)
        .filter(SubscriptionBilling.tenant_id == tenant_id)
        .first()
    )
    if existing:
        return existing
    today = _today()
    period_end = today + timedelta(days=TRIAL_DAYS)
    sub = SubscriptionBilling(
        tenant_id=tenant_id,
        plano_codigo=plano_codigo,
        valor_mensal_centavos=valor_centavos,
        status="trial",
        grace_days=DEFAULT_GRACE_DAYS,
        period_start=today,
        period_end=period_end,
        next_charge_at=period_end,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def _ensure_subscription(
    db: Session,
    tenant_id: int,
    plano_codigo: str = PLANO_CODIGO,
    valor_centavos: Optional[int] = None,
) -> SubscriptionBilling:
    """Garante que o tenant tenha uma subscription (cria trial se não existir). Valor vem da config + desconto se None."""
    sub = (
        db.query(SubscriptionBilling)
        .filter(SubscriptionBilling.tenant_id == tenant_id)
        .first()
    )
    if sub:
        return sub
    return create_trial_subscription(db, tenant_id, plano_codigo, valor_centavos or _valor_centavos_para_tenant(db, tenant_id))


def _split_payer_name(nome: Optional[str]) -> Tuple[str, str]:
    """Divide nome em first_name e last_name para o payer do MP. Uma única palavra vai em first_name."""
    if not nome or not str(nome).strip():
        return "", ""
    parts = str(nome).strip().split(None, 1)
    first = parts[0] if parts else ""
    last = parts[1].strip() if len(parts) > 1 else ""
    return first, last


def _normalize_cpf_for_mp(cpf: Optional[str]) -> Optional[str]:
    """Retorna CPF apenas com dígitos para payer.identification.number, ou None se inválido."""
    if not cpf:
        return None
    digits = "".join(c for c in str(cpf) if c.isdigit())
    if len(digits) != 11:
        return None
    return digits


def _get_empresa_for_tenant(db: Session, tenant_id: int) -> Optional[Empresa]:
    """Retorna a Empresa padrão do tenant (default_empresa) quando existir."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant or not tenant.default_empresa_id:
        return None
    return db.query(Empresa).filter(Empresa.id == tenant.default_empresa_id).first()


def _build_payer_phone(telefone: Optional[str]) -> Optional[Dict[str, str]]:
    """Monta objeto phone no formato MP: area_code (2 dígitos) e number. Telefone só dígitos."""
    if not telefone:
        return None
    digits = "".join(c for c in str(telefone) if c.isdigit())
    if len(digits) < 10:
        return None
    # DDD 2 dígitos; resto é o número
    area_code = digits[:2]
    number = digits[2:]
    return {"area_code": area_code, "number": number}


def _build_payer_address(empresa: Optional[Empresa]) -> Optional[Dict[str, Any]]:
    """Monta objeto address no formato MP a partir da Empresa (zip_code, street_name, street_number, etc.)."""
    if not empresa:
        return None
    has_zip = bool(empresa.cep and str(empresa.cep).strip())
    has_street = bool(empresa.endereco and str(empresa.endereco).strip())
    if not has_zip and not has_street:
        return None
    addr: Dict[str, Any] = {}
    if has_zip:
        addr["zip_code"] = str(empresa.cep).strip().replace("-", "")[:16]
    if has_street:
        addr["street_name"] = str(empresa.endereco).strip()[:256]
    if empresa.numero and str(empresa.numero).strip():
        addr["street_number"] = str(empresa.numero).strip()[:20]
    if empresa.cidade and str(empresa.cidade).strip():
        addr["city_name"] = str(empresa.cidade).strip()[:100]
    if empresa.uf and str(empresa.uf).strip():
        addr["state_name"] = str(empresa.uf).strip()[:50]
    return addr if addr else None


def create_checkout_preference(
    db: Session,
    tenant_id: int,
    plano_codigo: str = PLANO_CODIGO,
    valor_centavos: Optional[int] = None,
    payer_user_id: Optional[int] = None,
    payer_email: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Gera preferência Checkout Pro no MP. Retorna (init_point, preference_id).
    valor_centavos: se None, usa valor configurado em admin (com desconto por escopo).
    payer_email: pré-preenche o pagador e pode habilitar o botão Pagar na tela de revisão.
    """
    sub = _ensure_subscription(db, tenant_id, plano_codigo, valor_centavos)
    valor_cobrar = _valor_centavos_para_tenant(db, tenant_id)
    sub.valor_mensal_centavos = valor_cobrar
    db.commit()
    app_url = _get_app_url(db)
    # source_news=webhooks garante receber apenas Webhooks assinados (não IPN)
    notification_url = f"{app_url}/api/webhooks/mercadopago?source_news=webhooks" if app_url else ""
    back_success = f"{app_url}/billing/success" if app_url else ""
    back_failure = f"{app_url}/billing/failure" if app_url else ""
    back_pending = f"{app_url}/billing/pending" if app_url else ""

    unit_price = round(valor_cobrar / 100.0, 2)
    item_id = f"sub-{sub.id}"
    payload = {
        "items": [
            {
                "id": item_id,
                "title": "PDV Ibix - Assinatura mensal",
                "description": "Assinatura mensal do PDV Ibix",
                "category_id": "services",
                "quantity": 1,
                "unit_price": unit_price,
                "currency_id": "BRL",
            }
        ],
        "back_urls": {
            "success": back_success,
            "failure": back_failure,
            "pending": back_pending,
        },
        "auto_return": "approved",
        "notification_url": notification_url or None,
        "external_reference": str(sub.id),
    }
    # Payer: recomendações MP para aprovação (first_name, last_name, identification; opcional: phone, address)
    payer: Dict[str, Any] = {}
    if payer_email and payer_email.strip():
        payer["email"] = payer_email.strip()
    if payer_user_id:
        usuario = db.query(Usuario).filter(Usuario.id == payer_user_id).first()
        if usuario:
            if not payer.get("email") and usuario.email:
                payer["email"] = usuario.email.strip()[:100]
            first_name, last_name = _split_payer_name(usuario.nome)
            if first_name:
                payer["first_name"] = first_name[:256]
            if last_name:
                payer["last_name"] = last_name[:256]
            cpf_digits = _normalize_cpf_for_mp(usuario.cpf)
            if cpf_digits:
                payer["identification"] = {"type": "CPF", "number": cpf_digits}
            empresa = _get_empresa_for_tenant(db, tenant_id)
            if empresa:
                phone_obj = _build_payer_phone(empresa.telefone)
                if phone_obj:
                    payer["phone"] = phone_obj
                addr_obj = _build_payer_address(empresa)
                if addr_obj:
                    payer["address"] = addr_obj
    if payer:
        payload["payer"] = payer

    client = _get_mp_client(db)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(client.create_preference(payload))

    preference_id = result.get("id") or ""
    init_point = result.get("init_point") or result.get("sandbox_init_point") or ""

    sub.mp_preference_id = preference_id
    sub.last_payer_user_id = payer_user_id
    db.commit()

    return init_point, preference_id


def _register_webhook_event(
    db: Session,
    event_key: str,
    raw_body: Optional[str] = None,
    provider: str = "mercadopago",
) -> Optional[WebhookEvent]:
    """
    Registra evento no webhook_events (idempotência). Retorna o registro se inserido; None se já existir.
    """
    existing = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.provider == provider,
            WebhookEvent.event_key == event_key,
        )
        .first()
    )
    if existing:
        return None
    now = datetime.utcnow()
    ev = WebhookEvent(
        provider=provider,
        event_key=event_key,
        received_at=now,
        raw_json=raw_body[:10000] if raw_body else None,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def process_payment_webhook(
    db: Session,
    payment_id: int,
    raw_body: Optional[str] = None,
) -> bool:
    """
    Idempotente: busca pagamento no MP, cria Payment se não existir, atualiza Subscription e Tenant.ativo.
    Retorna True se processou (criou/atualizou), False se já processado ou pagamento não aprovado.
    """
    event_key = f"payment:{payment_id}"
    ev = _register_webhook_event(db, event_key, raw_body, "mercadopago")
    if ev is None:
        return False  # já processado

    client = _get_mp_client(db)
    try:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        data = loop.run_until_complete(client.fetch_payment(payment_id))
    except Exception:
        ev.processed_at = datetime.utcnow()
        db.commit()
        return False

    status = (data.get("status") or "").lower()
    if status not in ("approved", "authorized"):
        ev.processed_at = datetime.utcnow()
        db.commit()
        return False

    external_ref = data.get("external_reference")
    subscription_id = None
    if external_ref:
        try:
            subscription_id = int(external_ref)
        except (ValueError, TypeError):
            pass

    if not subscription_id:
        ev.processed_at = datetime.utcnow()
        db.commit()
        return False

    sub = db.query(SubscriptionBilling).filter(SubscriptionBilling.id == subscription_id).first()
    if not sub:
        ev.processed_at = datetime.utcnow()
        db.commit()
        return False

    # Evitar duplicar Payment pelo mesmo mp_payment_id
    mp_id = data.get("id")
    if isinstance(mp_id, (int, float)):
        mp_id = int(mp_id)
    else:
        mp_id = int(mp_id) if mp_id else 0
    existing_payment = (
        db.query(Payment).filter(Payment.mp_payment_id == mp_id).first()
    )
    amount_centavos = 0
    if not existing_payment:
        transaction_amount = data.get("transaction_amount") or 0
        amount_centavos = int(round(float(transaction_amount) * 100)) if transaction_amount else 0
        date_approved = data.get("date_approved")
        paid_at = None
        if date_approved:
            try:
                # ISO format e.g. 2025-02-12T10:00:00.000-04:00
                if isinstance(date_approved, str) and "T" in date_approved:
                    paid_at = datetime.fromisoformat(date_approved.replace("Z", "+00:00"))
                else:
                    paid_at = datetime.utcnow()
            except Exception:
                pass
        new_payment = Payment(
            subscription_id=sub.id,
            mp_payment_id=mp_id,
            status=status,
            amount_centavos=amount_centavos,
            paid_at=paid_at,
            external_reference=external_ref,
            raw_json=json.dumps(data)[:10000] if data else None,
        )
        db.add(new_payment)
        db.flush()
        payment_id_for_comissao = new_payment.id
        amount_centavos = new_payment.amount_centavos
    else:
        payment_id_for_comissao = existing_payment.id
        amount_centavos = existing_payment.amount_centavos

    now_dt = datetime.utcnow()
    today = _today()
    sub.status = "ativa"
    sub.last_paid_at = now_dt
    sub.blocked_at = None
    sub.period_end = today + timedelta(days=TRIAL_DAYS)
    sub.next_charge_at = sub.period_end

    tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
    if tenant:
        tenant.ativo = True

    # Comissão do Administrador (idempotente: uma por payment_id)
    if getattr(sub, "codigo_desconto_id", None):
        cod = db.query(CodigoDesconto).filter(CodigoDesconto.id == sub.codigo_desconto_id).first()
        if cod and cod.divulgador_id:
            div = db.query(Divulgador).filter(Divulgador.id == cod.divulgador_id).first()
            if div and div.usuario_id:
                regra = (
                    db.query(DivulgadorRegra)
                    .filter(DivulgadorRegra.divulgador_id == div.id)
                    .order_by(DivulgadorRegra.id.desc())
                    .first()
                )
                percentual = (regra.percentual_comissao if regra else 0) or 0
                if percentual > 0:
                    existe = db.query(ComissaoAdministrador).filter(
                        ComissaoAdministrador.payment_id == payment_id_for_comissao
                    ).first()
                    if not existe:
                        valor_comissao = int(round(amount_centavos * percentual / 100.0))
                        db.add(
                            ComissaoAdministrador(
                                payment_id=payment_id_for_comissao,
                                usuario_id_administrador=div.usuario_id,
                                valor_mensalidade_centavos=amount_centavos,
                                percentual_comissao=percentual,
                                valor_comissao_centavos=valor_comissao,
                                status="pendente",
                            )
                        )

    ev.processed_at = now_dt
    db.commit()
    return True


def _tenant_billing_emails(db: Session, tenant_id: int) -> List[str]:
    """Retorna lista de e-mails para notificações de billing (CA do tenant primeiro)."""
    role_ca = db.query(Role).filter(Role.nome == "Cliente Administrador").first()
    q = (
        db.query(Usuario.email)
        .filter(Usuario.tenant_id == tenant_id, Usuario.email.isnot(None), Usuario.email != "")
    )
    if role_ca:
        # preferir usuários CA
        ca_rows = db.query(Usuario.id).filter(Usuario.tenant_id == tenant_id, Usuario.role_id == role_ca.id).limit(5).all()
        ca_ids = [r[0] for r in ca_rows]
        if ca_ids:
            emails = db.query(Usuario.email).filter(Usuario.id.in_(ca_ids), Usuario.email.isnot(None)).distinct().all()
            out = [e[0] for e in emails if e[0]]
            if out:
                return out
    emails = q.distinct().limit(10).all()
    return [e[0] for e in emails if e[0]]


def process_billing_notifications(db: Session) -> int:
    """
    Job diário: envia e-mails trial_d7, trial_d3, trial_d1, trial_d0 (e D0 seta inadimplente),
    pastdue_d1, pastdue_d7, pastdue_d14, pastdue_d15. Respeita billing_notificacoes (anti-spam).
    Retorna quantidade de notificações enviadas.
    """
    today = _today()
    app_url = _get_app_url(db)
    link_pagar = f"{app_url}/financeiro/assinatura" if app_url else "/financeiro/assinatura"
    sent = 0

    # Trial: subs com status trial e period_end definido
    subs_trial = (
        db.query(SubscriptionBilling)
        .filter(SubscriptionBilling.status == "trial", SubscriptionBilling.period_end.isnot(None))
        .all()
    )
    for sub in subs_trial:
        period_end = sub.period_end
        if not period_end:
            continue
        days_left = (period_end - today).days
        # D0: último dia do trial -> inadimplente
        if days_left <= 0:
            sub.status = "inadimplente"
            tipo = "trial_d0"
            if (
                db.query(BillingNotificacao)
                .filter(BillingNotificacao.tenant_id == sub.tenant_id, BillingNotificacao.tipo == tipo)
                .first()
            ) is None:
                emails = _tenant_billing_emails(db, sub.tenant_id)
                if emails:
                    _send_billing_email(db, sub.tenant_id, tipo, emails, link_pagar, "Trial encerrado - regularize sua assinatura")
                _record_billing_notification(db, sub.tenant_id, tipo)
                sent += 1
            db.commit()
            continue
        if days_left == 7:
            tipo = "trial_d7"
        elif days_left == 3:
            tipo = "trial_d3"
        elif days_left == 1:
            tipo = "trial_d1"
        else:
            continue
        if (
            db.query(BillingNotificacao)
            .filter(BillingNotificacao.tenant_id == sub.tenant_id, BillingNotificacao.tipo == tipo)
            .first()
        ) is not None:
            continue
        emails = _tenant_billing_emails(db, sub.tenant_id)
        if emails:
            _send_billing_email(db, sub.tenant_id, tipo, emails, link_pagar, f"Faltam {days_left} dias para o fim do trial - PDV Ibix")
        _record_billing_notification(db, sub.tenant_id, tipo)
        sent += 1

    # Past due: inadimplente; next_charge_at já passou
    subs_past = (
        db.query(SubscriptionBilling)
        .filter(
            SubscriptionBilling.status == "inadimplente",
            SubscriptionBilling.next_charge_at.isnot(None),
        )
        .all()
    )
    for sub in subs_past:
        due = sub.next_charge_at
        if not due:
            continue
        days_past = (today - due).days
        if days_past == 1:
            tipo = "pastdue_d1"
        elif days_past == 7:
            tipo = "pastdue_d7"
        elif days_past == 14:
            tipo = "pastdue_d14"
        elif days_past >= 15:
            tipo = "pastdue_d15"
        else:
            continue
        if (
            db.query(BillingNotificacao)
            .filter(BillingNotificacao.tenant_id == sub.tenant_id, BillingNotificacao.tipo == tipo)
            .first()
        ) is not None:
            continue
        emails = _tenant_billing_emails(db, sub.tenant_id)
        if emails:
            _send_billing_email(db, sub.tenant_id, tipo, emails, link_pagar, f"Assinatura em atraso ({days_past} dias) - PDV Ibix")
        _record_billing_notification(db, sub.tenant_id, tipo)
        sent += 1

    if sent:
        db.commit()
    return sent


def _record_billing_notification(db: Session, tenant_id: int, tipo: str, canal: str = "email") -> None:
    existing = (
        db.query(BillingNotificacao)
        .filter(BillingNotificacao.tenant_id == tenant_id, BillingNotificacao.tipo == tipo)
        .first()
    )
    if existing:
        return
    db.add(
        BillingNotificacao(
            tenant_id=tenant_id,
            tipo=tipo,
            sent_at=datetime.utcnow(),
            canal=canal,
        )
    )


def _send_billing_email(
    db: Session,
    tenant_id: int,
    tipo: str,
    to_emails: List[str],
    link_pagar: str,
    subject: str,
) -> None:
    try:
        from app.services.email_service import EmailService
        body = f"Olá,\n\nAcesse o link para regularizar sua assinatura PDV Ibix: {link_pagar}\n\nPDV Ibix."
        svc = EmailService(db)
        svc.send_email(to=to_emails, subject=subject, body=body)
    except Exception:
        pass
