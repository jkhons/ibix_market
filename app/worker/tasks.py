# PDV Ibix - Tasks do Worker (E1.5/E1.6 confirmação de impl.)
# Geração de PDF (certificados/relatórios) e tarefas pesadas no Worker.
from datetime import datetime, timedelta, timezone

from .celery_app import celery_app


@celery_app.task(bind=True, name="app.worker.tasks.gerar_pdf_certificado")
def gerar_pdf_certificado(self, certificado_id: int, snapshot_json: dict):
    """
    No-op: módulo de certificados removido. Mantido para compatibilidade de task.
    """
    return {"certificado_id": certificado_id, "status": "skipped", "reason": "certificados module removed"}


@celery_app.task(bind=True, name="app.worker.tasks.gerar_pdf_relatorio")
def gerar_pdf_relatorio(self, relatorio_tipo: str, parametros: dict):
    """
    Gera PDF de relatório (agregações pesadas). Placeholder.
    """
    return {"relatorio_tipo": relatorio_tipo, "status": "queued", "task_id": self.request.id}


@celery_app.task(bind=True, name="app.worker.tasks.outbox_dispatch")
def outbox_dispatch(self):
    """
    Stub para compatibilidade: task enviada por beat/outro app no mesmo broker.
    PDV Ibix não usa outbox de mensagens; não faz nada.
    """
    return {"status": "skipped", "reason": "outbox not used in pdv_solumatica"}


@celery_app.task(name="app.worker.tasks.generate_report")
def generate_report_task(job_id: str):
    """
    Gera relatório assíncrono (E-Relatórios). Carrega job, executa handler do registry,
    salva artefato em storage e atualiza status.
    """
    import uuid

    from app.database.connection import SessionLocal
    from app.models.report_job import ReportArtifact, ReportJob
    from app.services.relatorios import get_report, save_bytes

    db = SessionLocal()
    try:
        uid = uuid.UUID(job_id)
        job = db.get(ReportJob, uid)
        if not job:
            return

        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)

        runtime = get_report(job.report_key)
        ctx = {
            "db": db,
            "cliente_id": job.cliente_id,
            "user_id": job.user_id,
            "output_format": job.output_format,
        }
        content, filename, mime = runtime.handler(job.params_json, ctx)

        scope_key = str(job.cliente_id) if job.cliente_id else str(job.user_id)
        storage_path, size, checksum = save_bytes(scope_key, str(job.id), filename, content)

        art = ReportArtifact(
            job_id=job.id,
            cliente_id=job.cliente_id,
            filename=filename,
            mime_type=mime,
            file_size=size,
            checksum_sha256=checksum,
            storage_path=storage_path,
        )
        db.add(art)

        job.status = "DONE"
        job.progress = 100
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except KeyError as e:
        try:
            uid = uuid.UUID(job_id)
            job = db.get(ReportJob, uid)
        except (ValueError, NameError):
            job = None
        if job:
            job.status = "FAILED"
            job.error_message = str(e)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise
    except Exception as e:
        try:
            uid = uuid.UUID(job_id)
            job = db.get(ReportJob, uid)
        except (ValueError, NameError):
            job = None
        if job:
            job.status = "FAILED"
            job.error_message = str(e)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.apply_billing_grace_policy")
def apply_billing_grace_policy():
    """
    Job diário: aplica política de carência (apply_grace_policy).
    Seta assinaturas ativa/inadimplente como bloqueada e tenant.ativo = False
    quando hoje > next_charge_at + grace_days.
    """
    from app.database.connection import SessionLocal
    from app.services.billing_service import apply_grace_policy as svc_apply_grace_policy

    db = SessionLocal()
    try:
        changed = svc_apply_grace_policy(db)
        return {"changed": changed}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.log_access_task")
def log_access_task(ip: str, user_agent: str, tipo_visitante: str, path: str | None = None):
    """
    Registra acesso em access_log (classificação HUMANO/BOT/CLOUD).
    Executada de forma assíncrona via Celery; não bloqueia requisições HTTP.
    """
    from app.database.connection import SessionLocal
    from app.models.access_log import AccessLog

    try:
        db = SessionLocal()
        try:
            entry = AccessLog(
                ip=ip or None,
                user_agent=(user_agent or None)[:500] if user_agent else None,
                tipo_visitante=tipo_visitante or "HUMANO",
                path=(path or None)[:512] if path else None,
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


@celery_app.task(name="app.worker.tasks.billing_daily_job")
def billing_daily_job():
    """
    Job diário (03:00): apply_grace_policy + process_billing_notifications.
    Notificações por e-mail (trial_d7…pastdue_d15) e D0 trial→inadimplente.
    Invalida cache Redis de subscription_blocked após alterar tenants.
    """
    from app.core.redis_cache import invalidate_subscription_blocked_all
    from app.database.connection import SessionLocal
    from app.services import billing_service

    db = SessionLocal()
    try:
        changed = billing_service.apply_grace_policy(db)
        if changed:
            invalidate_subscription_blocked_all()
        sent = billing_service.process_billing_notifications(db)
        return {"grace_changed": changed, "notifications_sent": sent}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.certificado_expirando_alert_task")
def certificado_expirando_alert_task():
    """
    Lista empresas com certificado_validade em 30, 15 ou 7 dias.
    Registra em log ou tabela de alertas (Fase 3 NFS-e).
    """
    from datetime import date, timedelta

    from app.database.connection import SessionLocal
    from app.models import Empresa

    db = SessionLocal()
    try:
        hoje = date.today()
        dias = [30, 15, 7]
        alertas = []
        for d in dias:
            limite = hoje + timedelta(days=d)
            q = db.query(Empresa).filter(
                Empresa.certificado_validade.isnot(None),
                Empresa.certificado_validade > hoje,
                Empresa.certificado_validade <= limite,
            )
            for emp in q:
                alertas.append({"empresa_id": emp.id, "razao_social": emp.razao_social, "validade": str(emp.certificado_validade), "dias": d})
        return {"alertas": alertas}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.emitir_nfe_pedido_marketplace")
def emitir_nfe_pedido_marketplace(pedido_id: int):
    """
    Cria NotaFiscal (rascunho) a partir do pedido marketplace e envia à SEFAZ.
    Executada após o checkout. Se falhar, a nota permanece em rascunho para retentativa.
    """
    from app.database.connection import SessionLocal
    from app.services.fiscal.emissao_service import FiscalEmissaoService
    from app.services.fiscal.nfe_marketplace_service import criar_nota_fiscal_de_pedido_marketplace

    db = SessionLocal()
    try:
        ok, msg, nota_id = criar_nota_fiscal_de_pedido_marketplace(db, pedido_id, usuario_id_emitente=None)
        if not ok or not nota_id:
            return {"success": False, "reason": msg or "Não foi possível criar a nota"}
        svc = FiscalEmissaoService(db)
        enviado, err, _ = svc.enviar_nfe(nota_id, usuario_id=None)
        if enviado:
            return {"success": True, "nota_id": nota_id, "enviada": True}
        return {"success": True, "nota_id": nota_id, "enviada": False, "erro_envio": err}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.notificar_ca_novo_pedido")
def notificar_ca_novo_pedido(pedido_id: int):
    """
    Envia e-mail aos responsáveis da loja (usuários com vínculo ao estabelecimento)
    com resumo do novo pedido.
    """
    from app.database.connection import SessionLocal
    from app.models import AreaCliente, LojaMarketplace, PedidoMarketplace, Usuario
    from app.services.email_service import EmailService

    db = SessionLocal()
    try:
        pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
        if not pedido:
            return {"sent": 0, "reason": "Pedido não encontrado"}
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == pedido.loja_id).first()
        if not loja:
            return {"sent": 0, "reason": "Loja não encontrada"}

        usuario_ids = [
            r[0] for r in db.query(AreaCliente.usuario_id).filter(
                AreaCliente.cliente_id == loja.cliente_id,
                AreaCliente.ativo == True,
            ).distinct().all()
        ]
        emails = []
        if usuario_ids:
            for (email,) in db.query(Usuario.email).filter(
                Usuario.id.in_(usuario_ids),
                Usuario.email.isnot(None),
                Usuario.email != "",
            ).all():
                e = (email or "").strip()
                if e and e not in emails:
                    emails.append(e)

        if not emails:
            return {"sent": 0, "reason": "Nenhum e-mail de responsável configurado para a loja"}

        total = str(pedido.total) if pedido.total is not None else "—"
        assunto = f"Novo pedido #{pedido_id} na sua loja"
        corpo = (
            f"Novo pedido recebido.\n\n"
            f"Pedido: #{pedido_id}\n"
            f"Comprador: {pedido.comprador_nome or '—'}\n"
            f"Total: R$ {total}\n\n"
            f"Acesse Minha loja no PDV para ver detalhes e atualizar o status."
        )
        svc = EmailService(db)
        sent = svc.send_email(to=emails, subject=assunto, body=corpo, funcao="marketplace")
        return {"sent": 1 if sent else 0, "emails": emails}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.notificar_marketplace_pagamento_confirmado")
def notificar_marketplace_pagamento_confirmado(pedido_id: int):
    """
    Após o gateway confirmar pagamento (webhook/reconciliação): e-mail aos responsáveis da loja (CA)
    e ao comprador; grava notificações no sino do CA e no inbox do consumidor (app).     Idempotência no enqueue.
    """
    from app.database.connection import SessionLocal
    from app.models import AreaCliente, LojaMarketplace, PedidoMarketplace, Usuario
    from app.models.consumidor_notificacao import ConsumidorNotificacao
    from app.models.usuario_notificacao import UsuarioNotificacao

    TIPO_INBOX = "marketplace_pedido_pago"

    db = SessionLocal()
    try:
        pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
        if not pedido:
            return {"sent_ca": 0, "sent_buyer": 0, "reason": "Pedido não encontrado"}
        if (pedido.status_pagamento or "").strip().lower() != "pago":
            return {"sent_ca": 0, "sent_buyer": 0, "reason": "Pedido não está com pagamento confirmado"}

        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == pedido.loja_id).first()
        if not loja:
            return {"sent_ca": 0, "sent_buyer": 0, "reason": "Loja não encontrada"}

        cliente_id = loja.cliente_id
        usuario_ids = [
            r[0]
            for r in db.query(AreaCliente.usuario_id)
            .filter(AreaCliente.cliente_id == cliente_id, AreaCliente.ativo == True)
            .distinct()
            .all()
        ]
        ca_emails: list[str] = []
        if usuario_ids:
            for (email,) in (
                db.query(Usuario.email)
                .filter(
                    Usuario.id.in_(usuario_ids),
                    Usuario.email.isnot(None),
                    Usuario.email != "",
                )
                .all()
            ):
                e = (email or "").strip()
                if e and e not in ca_emails:
                    ca_emails.append(e)

        total = str(pedido.total) if pedido.total is not None else "—"
        num = pedido.numero_pedido or str(pedido.id)

        inbox_ca = 0
        titulo_inbox = f"Pagamento confirmado — Pedido {num}"
        msg_inbox = (
            f"{pedido.comprador_nome or 'Comprador'} · Total R$ {total}. "
            f"Acesse os pedidos do marketplace para separar e atualizar o status."
        )
        link_inbox = "/negocio/pedidos"
        for uid in usuario_ids:
            existe = (
                db.query(UsuarioNotificacao)
                .filter(
                    UsuarioNotificacao.usuario_id == uid,
                    UsuarioNotificacao.tipo == TIPO_INBOX,
                    UsuarioNotificacao.ref_id == pedido.id,
                )
                .first()
            )
            if existe:
                continue
            db.add(
                UsuarioNotificacao(
                    usuario_id=uid,
                    tenant_id=cliente_id,
                    tipo=TIPO_INBOX,
                    ref_id=pedido.id,
                    titulo=titulo_inbox,
                    mensagem=msg_inbox,
                    link=link_inbox,
                    icone="shopping-cart",
                    cor="success",
                    lida=False,
                    dados_json={"pedido_id": pedido.id, "numero_pedido": num},
                )
            )
            inbox_ca += 1

        inbox_buyer = 0
        cid = pedido.comprador_id
        if cid:
            dup = False
            for row in (
                db.query(ConsumidorNotificacao)
                .filter(
                    ConsumidorNotificacao.consumidor_id == cid,
                    ConsumidorNotificacao.tipo == TIPO_INBOX,
                )
                .limit(50)
                .all()
            ):
                if (row.dados_json or {}).get("pedido_id") == pedido.id:
                    dup = True
                    break
            if not dup:
                db.add(
                    ConsumidorNotificacao(
                        consumidor_id=cid,
                        tipo=TIPO_INBOX,
                        titulo=f"Pagamento confirmado — Pedido {num}",
                        mensagem=f"Seu pagamento foi confirmado. Total R$ {total}. Acompanhe o pedido no app.",
                        dados_json={"pedido_id": pedido.id, "numero_pedido": num},
                    )
                )
                inbox_buyer = 1

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        from app.services.marketplace_email_service import (
            enviar_pedido_pago_comprador,
            enviar_pedido_pago_loja,
        )

        sent_ca = enviar_pedido_pago_loja(db, pedido, loja, ca_emails) if ca_emails else 0

        buyer = (pedido.comprador_email or "").strip()
        sent_buyer = 0
        if buyer:
            if enviar_pedido_pago_comprador(db, pedido, loja):
                sent_buyer = 1

        return {
            "sent_ca": sent_ca,
            "sent_buyer": sent_buyer,
            "ca_emails": ca_emails,
            "buyer": buyer or None,
            "inbox_ca_rows": inbox_ca,
            "inbox_consumidor": inbox_buyer,
        }
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.notificar_marketplace_pedido_status_email_comprador")
def notificar_marketplace_pedido_status_email_comprador(
    pedido_id: int,
    status_anterior: str,
    status_novo: str,
    status_label: str,
):
    """E-mail HTML ao comprador quando a loja altera status_pedido."""
    from app.database.connection import SessionLocal
    from app.models import LojaMarketplace, PedidoMarketplace
    from app.services.marketplace_email_service import enviar_pedido_status_comprador

    db = SessionLocal()
    try:
        pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
        if not pedido or not (pedido.comprador_email or "").strip():
            return {"sent": 0, "reason": "pedido ou e-mail ausente"}
        if (status_novo or "").strip() == (status_anterior or "").strip():
            return {"sent": 0, "reason": "status_inalterado"}
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == pedido.loja_id).first()
        if not loja:
            return {"sent": 0, "reason": "loja não encontrada"}
        ok = enviar_pedido_status_comprador(db, pedido, loja, status_novo, status_label)
        return {"sent": 1 if ok else 0}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.notificar_marketplace_entrega_status_email_comprador")
def notificar_marketplace_entrega_status_email_comprador(entrega_id: int, novo_status: str):
    """E-mail HTML ao comprador quando o entregador altera o status da entrega."""
    from app.core.constants import AGUARDANDO_PUBLICACAO, DISPONIVEL
    from app.database.connection import SessionLocal
    from app.models import EntregaMarketplace, LojaMarketplace, PedidoMarketplace
    from app.services.marketplace_email_service import enviar_entrega_status_comprador

    ns = (novo_status or "").strip()
    if ns in (AGUARDANDO_PUBLICACAO, DISPONIVEL):
        return {"sent": 0, "reason": "status_interno"}

    db = SessionLocal()
    try:
        entrega = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
        if not entrega:
            return {"sent": 0, "reason": "entrega não encontrada"}
        pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == entrega.pedido_id).first()
        if not pedido or not (pedido.comprador_email or "").strip():
            return {"sent": 0, "reason": "pedido ou e-mail ausente"}
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == pedido.loja_id).first()
        if not loja:
            return {"sent": 0, "reason": "loja não encontrada"}
        ok = enviar_entrega_status_comprador(db, pedido, loja, ns)
        return {"sent": 1 if ok else 0}
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.worker.tasks.dispatch_venda_fechada_webhook",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 4},
)
def dispatch_venda_fechada_webhook(
    self,
    webhook_url: str,
    payload: dict,
    token: str | None = None,
    timeout_seconds: int = 8,
):
    """
    Dispara webhook de integração para evento venda.fechada.
    """
    import httpx

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post(webhook_url, json=payload, headers=headers)
        resp.raise_for_status()
    return {"status": "ok", "status_code": resp.status_code}


@celery_app.task(name="app.worker.tasks.expire_reservations_marketplace")
def expire_reservations_marketplace():
    """Libera reservas de estoque marketplace com reserved_until vencido (job periódico)."""
    from app.database.connection import SessionLocal
    from app.services.reserva_estoque_marketplace_service import expire_reservations
    db = SessionLocal()
    try:
        count = expire_reservations(db)
        db.commit()
        return {"released": count}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.process_webhook_event_marketplace")
def process_webhook_event_marketplace(webhook_event_id: int):
    """
    Processa um WebhookEvent por ID (G2: reprocessamento ou fila assíncrona).
    Carrega o evento, busca pagamento no MP, reconcilia transação e marca processed_at.
    """
    from app.api.webhooks_mercadopago import process_webhook_event_by_id_sync
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        ok = process_webhook_event_by_id_sync(db, webhook_event_id)
        return {"processed": ok, "webhook_event_id": webhook_event_id}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        return {"processed": False, "webhook_event_id": webhook_event_id, "error": str(e)[:500]}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.reconcile_pending_marketplace_payments")
def reconcile_pending_marketplace_payments():
    """
    Fallback: reconcilia pedidos marketplace pendentes consultando a API do Mercado Pago.
    Roda periodicamente via beat; protege contra falhas de webhook (secret errado, rede, etc).
    Só processa pedidos criados nas últimas 48h com status_pagamento='pendente'.
    """
    from app.core.billing_config import get_mp_access_token
    from app.core.logging import log_error, log_struct
    from app.database.connection import SessionLocal
    from app.models import PaymentTransaction, PedidoMarketplace
    from app.services.payments.checkout_marketplace_service import _resolve_provider_and_credentials
    from app.services.payments.providers_marketplace import get_marketplace_provider
    from app.services.payments.webhook_marketplace_service import process_payment_notification

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        pending_txs = (
            db.query(PaymentTransaction)
            .join(PedidoMarketplace, PaymentTransaction.pedido_id == PedidoMarketplace.id)
            .filter(
                PaymentTransaction.provider_code == "mercadopago",
                PaymentTransaction.status == "pending",
                PaymentTransaction.is_active == True,
                PaymentTransaction.pedido_id.isnot(None),
                PedidoMarketplace.status_pagamento == "pendente",
                PedidoMarketplace.created_at >= cutoff,
            )
            .order_by(PaymentTransaction.id.asc())
            .limit(50)
            .all()
        )

        if not pending_txs:
            return {"reconciled": 0, "checked": 0}

        billing_fallback = get_mp_access_token(db)
        provider = get_marketplace_provider("mercadopago")
        reconciled = 0

        for tx in pending_txs:
            try:
                access_token = None
                try:
                    _, _, credentials, _ = _resolve_provider_and_credentials(db, tx.cliente_id)
                    access_token = (
                        credentials.get("access_token")
                        or credentials.get("ACCESS_TOKEN")
                        or credentials.get("token")
                    )
                except ValueError:
                    access_token = None
                if not access_token:
                    access_token = billing_fallback
                if not access_token:
                    continue

                creds = {"access_token": access_token}
                mp_payment = None
                if tx.provider_transaction_id:
                    mp_payment = provider.fetch_payment(tx.provider_transaction_id, creds)
                if not mp_payment and tx.pedido_id:
                    mp_payment = provider.search_payment_by_reference(str(tx.pedido_id), creds)
                if not mp_payment:
                    continue

                mp_status = (mp_payment.get("status") or "").lower()
                if mp_status == "pending":
                    continue

                mp_result = process_payment_notification(db, tx, mp_status, mp_payment)
                if mp_result:
                    db.commit()
                    from app.services.payments.webhook_marketplace_service import (
                        dispatch_marketplace_pedido_pagamento_confirmado_notifications,
                    )

                    dispatch_marketplace_pedido_pagamento_confirmado_notifications(
                        mp_result.pedido_ids_notify_pagamento_confirmado
                    )
                    reconciled += 1
                    log_struct(
                        "mp_auto_reconcile_success",
                        level="info",
                        pedido_id=tx.pedido_id,
                        mp_status=mp_status,
                        tx_id=tx.id,
                    )
            except Exception as exc:
                db.rollback()
                log_error(
                    "mp_auto_reconcile failed pedido_id=%s tx_id=%s: %s" % (tx.pedido_id, tx.id, exc),
                    exc_info=exc,
                )

        return {"reconciled": reconciled, "checked": len(pending_txs)}
    finally:
        db.close()


# ─── Mobile: Push Notification ───────────────────────────────
@celery_app.task(name="app.worker.tasks.enviar_push_notification")
def enviar_push_notification(consumidor_id: int, titulo: str, mensagem: str, tipo: str = "geral", dados: dict = None):
    """Envia push FCM para todos os tokens ativos do consumidor. Desativa tokens inválidos."""
    from app.database.connection import SessionLocal
    db = SessionLocal()
    try:
        from app.models.consumidor_push_token import ConsumidorPushToken
        from app.services.notificacao_service import criar_notificacao

        criar_notificacao(db, consumidor_id, tipo, titulo, mensagem, dados_json=dados)

        tokens = (
            db.query(ConsumidorPushToken)
            .filter(ConsumidorPushToken.consumidor_id == consumidor_id, ConsumidorPushToken.ativo.is_(True))
            .all()
        )
        if not tokens:
            return {"enviados": 0, "falhas": 0}

        from app.core.firebase import send_push_notification
        enviados, falhas = 0, 0
        for pt in tokens:
            ok = send_push_notification(pt.token, titulo, mensagem, dados)
            if ok:
                enviados += 1
            else:
                falhas += 1
                pt.ativo = False
        db.commit()

        try:
            from app.services.websocket_manager import publish_event
            publish_event(consumidor_id, "notificacao.nova", {"titulo": titulo, "mensagem": mensagem, "tipo": tipo})
        except Exception:
            pass

        return {"enviados": enviados, "falhas": falhas}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.registrar_termo_busca")
def registrar_termo_busca(termo: str):
    """Registra ou incrementa contagem de um termo buscado."""
    from app.database.connection import SessionLocal
    db = SessionLocal()
    try:
        from app.services.busca_service import registrar_termo
        registrar_termo(db, termo)
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.carrinho_abandonado")
def carrinho_abandonado():
    """Envia push para consumidores com checkout abandonado há >24h (aceite_marketing=True)."""
    from datetime import datetime, timedelta, timezone

    from app.database.connection import SessionLocal
    db = SessionLocal()
    try:
        from app.models import ConsumidorMarketplace, MarketplaceCheckoutSession
        limite = datetime.now(timezone.utc) - timedelta(hours=24)
        sessions = (
            db.query(MarketplaceCheckoutSession)
            .filter(
                MarketplaceCheckoutSession.status == "pendente",
                MarketplaceCheckoutSession.created_at < limite,
            )
            .limit(200)
            .all()
        )
        enviados = 0
        seen = set()
        for s in sessions:
            cid = getattr(s, "consumidor_id", None)
            if not cid or cid in seen:
                continue
            seen.add(cid)
            consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == cid).first()
            if consumidor and consumidor.aceite_marketing and consumidor.ativo:
                enviar_push_notification.delay(
                    consumidor_id=cid,
                    titulo="Você esqueceu algo no carrinho!",
                    mensagem="Seus itens ainda estão esperando. Finalize sua compra agora.",
                    tipo="carrinho_abandonado",
                )
                enviados += 1
        return {"verificados": len(sessions), "push_enviados": enviados}
    finally:
        db.close()
