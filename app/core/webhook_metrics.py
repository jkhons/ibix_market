# PDV Ibix - Métricas Prometheus para webhooks de pagamento
"""Contadores para observabilidade: recebidos, processados, assinatura inválida, erros."""
from prometheus_client import Counter

WEBHOOK_LABELS = ["provider"]

webhook_received_total = Counter(
    "pdv_webhook_received_total",
    "Total de webhooks de pagamento recebidos (type=payment, com data.id)",
    WEBHOOK_LABELS,
)
webhook_processed_total = Counter(
    "pdv_webhook_processed_total",
    "Total de webhooks processados com sucesso (tx encontrada e atualizada)",
    WEBHOOK_LABELS,
)
webhook_signature_invalid_total = Counter(
    "pdv_webhook_signature_invalid_total",
    "Total de webhooks rejeitados por assinatura inválida",
    WEBHOOK_LABELS,
)
webhook_processing_error_total = Counter(
    "pdv_webhook_processing_error_total",
    "Total de erros ao processar webhook (exceção ou billing/reversão)",
    WEBHOOK_LABELS,
)
webhook_queued_total = Counter(
    "pdv_webhook_queued_total",
    "Total de webhooks enfileirados para processamento assíncrono",
    WEBHOOK_LABELS,
)
