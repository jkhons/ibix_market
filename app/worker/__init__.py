# PDV Ibix - Worker assíncrono (Celery + Redis)
# Confirmação de impl.: E1.5 — Worker para PDF e tarefas pesadas
from .celery_app import celery_app

__all__ = ["celery_app"]
