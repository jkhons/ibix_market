# PDV Ibix - Tasks Celery do módulo NFS-e (Fase 5)
from datetime import datetime, timezone

from app.worker.celery_app import celery_app
from app.worker.db_task import worker_db_session


@celery_app.task(
    bind=True,
    name="app.worker.nfse_tasks.job_issue_nfse",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def job_issue_nfse(self, invoice_id: int):
    """
    Emissão assíncrona: valida pré-requisitos, reserva RPS, chama provider.issue(),
    grava log OUT/IN em nfse_message_logs (redigido), atualiza status.
    """
    from app.models import Empresa
    from app.models.nfse import NfseInvoice
    from app.services.nfse import reservar_rps, validar_pre_requisitos_emissao
    from app.services.nfse.errors import NfseErrorCode
    from app.services.nfse.logging_nfse import log_nfse_message
    from app.services.nfse.providers import get_provider

    try:
        with worker_db_session() as db:
            inv = db.get(NfseInvoice, invoice_id)
            if not inv or inv.status not in ("QUEUED", "DRAFT"):
                return {"status": "skipped", "reason": "invalid_state"}

            empresa = db.get(Empresa, inv.empresa_id)
            if not empresa:
                inv.status = "REJECTED"
                inv.last_error_code = NfseErrorCode.SCHEMA_INVALID.value
                inv.last_error_msg = "Empresa não encontrada."
                db.commit()
                return {"status": "rejected"}

            ok, code, msg = validar_pre_requisitos_emissao(
                db, inv.tenant_id, inv.empresa_id, inv.cliente_id, inv.municipio_prestacao_ibge
            )
            if not ok:
                inv.status = "REJECTED"
                inv.last_error_code = code
                inv.last_error_msg = msg
                db.commit()
                return {"status": "rejected", "code": code}

            rps = reservar_rps(db, inv.tenant_id, inv.empresa_id)
            if not rps:
                inv.status = "REJECTED"
                inv.last_error_code = NfseErrorCode.RPS_UNAVAILABLE.value
                inv.last_error_msg = "Falha ao reservar RPS."
                db.commit()
                return {"status": "rejected"}

            rps.nfse_invoice_id = inv.id
            rps.status = "USED"
            inv.status = "SENT"
            db.flush()

            provider = get_provider(inv.provider or "NACIONAL")
            credential = None  # opcional: nfse_credentials por empresa
            result = provider.issue(inv, empresa, credential, rps_numero=rps.numero, rps_serie=rps.serie or "1")

            log_nfse_message(
                db,
                tenant_id=inv.tenant_id,
                nfse_invoice_id=inv.id,
                direction="OUT",
                http_status=result.http_status,
                payload_redacted=result.payload_out_redacted,
                response_redacted=result.response_in_redacted,
            )

            if result.success and result.status == "AUTHORIZED":
                inv.status = "AUTHORIZED"
                inv.numero_nfse = result.numero_nfse
                inv.codigo_verificacao = result.codigo_verificacao
                inv.url_consulta = result.url_consulta
                inv.data_emissao = result.data_emissao or datetime.now(timezone.utc)
                inv.last_error_code = None
                inv.last_error_msg = None
            elif result.success and result.status == "SENT":
                inv.status = "SENT"
                pass
            else:
                inv.status = "REJECTED"
                inv.last_error_code = result.error_code or NfseErrorCode.REJEICAO_PREFIX.value
                inv.last_error_msg = (result.error_msg or "")[:500]

            db.commit()
            return {"status": inv.status.lower(), "numero_nfse": inv.numero_nfse}
    except Exception as e:
        with worker_db_session() as db:
            inv = db.get(NfseInvoice, invoice_id)
            if inv and inv.status == "SENT":
                inv.status = "QUEUED"
                inv.last_error_code = NfseErrorCode.NETWORK_ERROR.value
                inv.last_error_msg = str(e)[:500]
                db.commit()
        raise


@celery_app.task(name="app.worker.nfse_tasks.job_poll_nfse")
def job_poll_nfse(invoice_id: int):
    """Consulta status no provider até AUTHORIZED ou REJECTED."""
    from app.models import Empresa
    from app.models.nfse import NfseInvoice
    from app.services.nfse.logging_nfse import log_nfse_message
    from app.services.nfse.providers import get_provider

    with worker_db_session() as db:
        inv = db.get(NfseInvoice, invoice_id)
        if not inv or inv.status != "SENT":
            return {"status": "skipped"}
        empresa = db.get(Empresa, inv.empresa_id)
        provider = get_provider(inv.provider or "NACIONAL")
        result = provider.poll(inv, empresa, None)
        log_nfse_message(
            db,
            tenant_id=inv.tenant_id,
            nfse_invoice_id=inv.id,
            direction="IN",
            http_status=result.http_status,
            response_redacted=result.response_redacted,
        )
        if result.status == "AUTHORIZED":
            inv.status = "AUTHORIZED"
            inv.numero_nfse = result.numero_nfse or inv.numero_nfse
            inv.codigo_verificacao = result.codigo_verificacao or inv.codigo_verificacao
            inv.url_consulta = result.url_consulta or inv.url_consulta
            inv.data_emissao = result.data_emissao or inv.data_emissao
            inv.last_error_code = None
            inv.last_error_msg = None
        elif result.status == "REJECTED":
            inv.status = "REJECTED"
            inv.last_error_code = result.error_code
            inv.last_error_msg = (result.error_msg or "")[:500]
        db.commit()
        return {"status": inv.status}


@celery_app.task(name="app.worker.nfse_tasks.job_cancel_nfse")
def job_cancel_nfse(invoice_id: int, reason: str):
    """Cancelamento assíncrono: chama provider.cancel() e marca CANCELED."""
    from app.models import Empresa
    from app.models.nfse import NfseInvoice
    from app.services.nfse.logging_nfse import log_nfse_message
    from app.services.nfse.providers import get_provider

    with worker_db_session() as db:
        inv = db.get(NfseInvoice, invoice_id)
        if not inv:
            return {"status": "not_found"}
        if inv.status != "AUTHORIZED":
            return {"status": "invalid_state", "current": inv.status}
        empresa = db.get(Empresa, inv.empresa_id)
        provider = get_provider(inv.provider or "NACIONAL")
        result = provider.cancel(inv, empresa, None, reason=reason)
        log_nfse_message(
            db,
            tenant_id=inv.tenant_id,
            nfse_invoice_id=inv.id,
            direction="OUT",
            http_status=result.http_status,
            payload_redacted=result.payload_out_redacted,
            response_redacted=result.response_in_redacted,
        )
        if result.success:
            inv.status = "CANCELED"
            inv.last_error_code = None
            inv.last_error_msg = None
        else:
            inv.last_error_code = result.error_code
            inv.last_error_msg = (result.error_msg or "")[:500]
        db.commit()
        return {"status": "canceled" if result.success else "cancel_failed"}


@celery_app.task(name="app.worker.nfse_tasks.job_generate_pdf_nfse")
def job_generate_pdf_nfse(invoice_id: int):
    """Gera e armazena PDF/espelho da NFS-e quando autorizada. Stub: apenas registra; implementar geração real quando houver armazenamento de arquivo."""
    from app.models.nfse import NfseInvoice

    with worker_db_session() as db:
        inv = db.get(NfseInvoice, invoice_id)
        if not inv:
            return {"status": "not_found"}
        if inv.status != "AUTHORIZED":
            return {"status": "skipped", "reason": "invoice_not_authorized"}
        # TODO: gerar PDF (ex.: weasyprint ou reportlab), salvar em storage e registrar URL no invoice ou tabela anexos
        return {"status": "ok", "invoice_id": invoice_id, "message": "PDF stub (implementar geração)"}
