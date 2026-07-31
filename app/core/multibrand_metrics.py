# PDV Ibix — Métricas Prometheus multi-brand (Fase 3.2, cardinalidade controlada)
"""Labels: brand_slug (baixa cardinalidade) + status_class; tenant_id só em logs, não em métricas."""
from __future__ import annotations

from typing import Optional

try:
    from prometheus_client import Counter, Histogram
except ImportError:  # pragma: no cover
    Counter = None  # type: ignore
    Histogram = None  # type: ignore

HTTP_REQUESTS_TOTAL = (
    Counter(
        "pdv_http_requests_total",
        "Total de requisições HTTP por marca (cardinalidade controlada)",
        ["method", "brand_slug", "status_class"],
    )
    if Counter is not None
    else None
)

HTTP_REQUEST_DURATION_SECONDS = (
    Histogram(
        "pdv_http_request_duration_seconds",
        "Duração de requisições HTTP por marca",
        ["method", "brand_slug", "status_class"],
        buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    )
    if Histogram is not None
    else None
)


def status_class(status_code: int) -> str:
    if status_code < 200:
        return "1xx"
    if status_code < 300:
        return "2xx"
    if status_code < 400:
        return "3xx"
    if status_code < 500:
        return "4xx"
    return "5xx"


def record_http_request(
    *,
    method: str,
    brand_slug: str,
    status_code: int,
    duration_seconds: Optional[float] = None,
) -> None:
    if HTTP_REQUESTS_TOTAL is None:
        return
    slug = (brand_slug or "unknown").strip().lower()[:32]
    sc = status_class(status_code)
    HTTP_REQUESTS_TOTAL.labels(method.upper(), slug, sc).inc()
    if duration_seconds is not None and HTTP_REQUEST_DURATION_SECONDS is not None:
        HTTP_REQUEST_DURATION_SECONDS.labels(method.upper(), slug, sc).observe(duration_seconds)
