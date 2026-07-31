# PDV Ibix - Celery app (E1.5 confirmação de impl.)
# Broker: Redis (simples) ou RabbitMQ (produção). Fila para PDF e tarefas pesadas.
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from celery import Celery
from celery.schedules import crontab

# CELERY_BROKER_URL ou REDIS_URL (fallback redis local)
BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "pdv_solumatica",
    broker=BROKER_URL,
    backend=BROKER_URL,
    include=["app.worker.tasks", "app.worker.nfse_tasks", "app.worker.geo_tasks"],
)
celery_app.conf.timezone = "America/Sao_Paulo"
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
# Celery 6+: explicita reconexão no startup para manter comportamento atual.
celery_app.conf.broker_connection_retry_on_startup = True

# Job diário: bloqueio + notificações (03:00); certificado expirando (04:00)
celery_app.conf.beat_schedule = {
    "billing-daily-job": {
        "task": "app.worker.tasks.billing_daily_job",
        "schedule": crontab(hour=3, minute=0),
    },
    "certificado-expirando-alert": {
        "task": "app.worker.tasks.certificado_expirando_alert_task",
        "schedule": crontab(hour=4, minute=0),
    },
    "reconcile-pending-marketplace-payments": {
        "task": "app.worker.tasks.reconcile_pending_marketplace_payments",
        "schedule": 600.0,
    },
    "lgpd-purge-consumidores": {
        "task": "app.worker.tasks.lgpd_purge_consumidores",
        "schedule": crontab(hour=5, minute=0),
    },
}
