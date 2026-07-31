from app.worker.db_task import worker_db_session
# PDV Ibix - Tasks de geocodificacao (CEP + numero -> lat/lng/precision assincrono)
import json
import logging
import re
from typing import Optional

import httpx

from .celery_app import celery_app

logger = logging.getLogger(__name__)


_NUMERO_RE = re.compile(r"(?:^|[\s,])(\d{1,6})(?:[\s,/-]|$)")


def _extrair_numero_endereco(endereco: Optional[str]) -> Optional[str]:
    """Heuristica simples para extrair numero do imovel de um endereco em texto livre."""
    if not endereco:
        return None
    m = _NUMERO_RE.search(endereco)
    return m.group(1) if m else None


@celery_app.task(
    bind=True,
    name="app.worker.geo_tasks.geocode_endereco",
    autoretry_for=(httpx.RequestError, httpx.TimeoutException),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def geocode_endereco(self, tabela: str, registro_id: int, cep: str):
    """Geocodifica endereco (CEP + numero) e atualiza lat/lng/precision no registro.

    1. Abre SessionLocal
    2. Le o registro para obter cidade/uf/numero
    3. Chama geocode_address (CEP + numero)
    4. Se sucesso: UPDATE lat/lng (+ precision em clientes), commit, audit_action
    5. Se falha: log warning, nao altera registro
    6. finally: db.close()
    """
    from app.core.audit import audit_action
    from app.services.geo_service import geocode_address, geocode_cep

    if tabela not in ("clientes", "enderecos_consumidor"):
        logger.error("geo_tasks: tabela invalida %s", tabela)
        return {"status": "error", "reason": "tabela_invalida"}

    with worker_db_session() as db:
        if tabela == "clientes":
            from app.models.cliente import Cliente
            registro = db.query(Cliente).filter(Cliente.id == registro_id).first()
        else:
            from app.models.endereco_consumidor import EnderecoConsumidor
            registro = db.query(EnderecoConsumidor).filter(EnderecoConsumidor.id == registro_id).first()

        if not registro:
            logger.warning("geo_tasks: registro nao encontrado %s id=%d", tabela, registro_id)
            return {"status": "not_found"}

        cidade = getattr(registro, "cidade", None)
        uf = getattr(registro, "uf", None)
        numero = getattr(registro, "numero", None)
        if not numero and tabela == "clientes":
            numero = _extrair_numero_endereco(getattr(registro, "endereco", None))
        complemento = getattr(registro, "complemento", None)

        result = geocode_address(
            cep=cep,
            numero=numero,
            complemento=complemento,
            cidade=cidade,
            uf=uf,
        )

        if not result:
            coords = geocode_cep(cep, cidade=cidade, uf=uf)
            if not coords:
                logger.warning(
                    "geo_tasks: geocodificacao falhou %s id=%d cep_prefixo=%s",
                    tabela,
                    registro_id,
                    cep[:5] if cep else "",
                )
                return {"status": "geocode_failed"}
            registro.latitude = coords[0]
            registro.longitude = coords[1]
            if tabela == "clientes" and hasattr(registro, "geocoding_precision"):
                registro.geocoding_precision = "approximate"
            fonte = "brasilapi"
            precision_log = "approximate"
        else:
            registro.latitude = result.lat
            registro.longitude = result.lng
            if tabela == "clientes" and hasattr(registro, "geocoding_precision"):
                registro.geocoding_precision = result.precision
            fonte = result.provider or "geocode_address"
            precision_log = result.precision

        db.commit()

        try:
            audit_action(
                db,
                acao="geo_coordenadas_atualizadas",
                recurso_tipo=tabela,
                recurso_id=registro_id,
                detalhes=json.dumps(
                    {
                        "cep_prefixo": cep[:5] if cep else "",
                        "fonte": fonte,
                        "precision": precision_log,
                        "tem_numero": bool(numero),
                    }
                ),
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "lat": registro.latitude,
            "lng": registro.longitude,
            "precision": precision_log,
        }
