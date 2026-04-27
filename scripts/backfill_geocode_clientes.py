#!/usr/bin/env python3
"""Backfill de geocodificacao de clientes (lojas).

Preenche `latitude`/`longitude`/`geocoding_precision` para clientes que ainda nao
tem coordenadas, ou cuja precisao seja menor que a desejada.

Uso:
    cd /central_solumatica/pdv_solumatica
    .venv/bin/python scripts/backfill_geocode_clientes.py [--dry-run]
                                                          [--apenas-faltantes]
                                                          [--limite N]

Notas:
- Respeita rate limit dos provedores publicos (Nominatim/BrasilAPI). Faz sleep
  entre chamadas para evitar bloqueio.
- Para subir custo controlado em producao, defina GOOGLE_MAPS_API_KEY no .env
  para usar Google Geocoding (rooftop quando disponivel).
"""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Permite rodar como script (PYTHONPATH no projeto).
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("backfill_geocode_clientes")


def main() -> int:
    from sqlalchemy import or_

    from app.database.connection import SessionLocal
    from app.models.cliente import Cliente
    from app.services.geo_service import (
        PRECISION_LOCALITY,
        geocode_address,
        geocode_cep,
    )
    from app.worker.geo_tasks import _extrair_numero_endereco

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Nao grava no banco")
    parser.add_argument(
        "--apenas-faltantes",
        action="store_true",
        help="Atualiza apenas clientes sem latitude/longitude (default: tambem reprocessa precisao locality)",
    )
    parser.add_argument("--limite", type=int, default=None, help="Limita N clientes")
    parser.add_argument("--sleep-ms", type=int, default=400, help="Pausa entre chamadas externas (ms)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(Cliente).filter(Cliente.cep.isnot(None))
        if args.apenas_faltantes:
            query = query.filter(or_(Cliente.latitude.is_(None), Cliente.longitude.is_(None)))
        else:
            query = query.filter(
                or_(
                    Cliente.latitude.is_(None),
                    Cliente.longitude.is_(None),
                    Cliente.geocoding_precision.is_(None),
                    Cliente.geocoding_precision == PRECISION_LOCALITY,
                )
            )
        if args.limite:
            query = query.limit(args.limite)
        clientes = query.all()
        total = len(clientes)
        logger.info("backfill_geocode_clientes: %d candidato(s) - dry_run=%s", total, args.dry_run)

        ok = falhas = 0
        for i, cli in enumerate(clientes, start=1):
            cep = (cli.cep or "").strip()
            numero = _extrair_numero_endereco(cli.endereco)
            try:
                result = geocode_address(
                    cep=cep,
                    numero=numero,
                    cidade=cli.cidade,
                    uf=cli.uf,
                )
                if result:
                    lat, lng, precision = result.lat, result.lng, result.precision
                else:
                    coords = geocode_cep(cep, cidade=cli.cidade, uf=cli.uf)
                    if not coords:
                        falhas += 1
                        logger.warning("[%d/%d] cliente_id=%s SEM coords (cep=%s)", i, total, cli.id, cep[:5])
                        time.sleep(args.sleep_ms / 1000.0)
                        continue
                    lat, lng = coords
                    precision = "approximate"

                if args.dry_run:
                    logger.info(
                        "[%d/%d] DRY cliente_id=%s lat=%.6f lng=%.6f precision=%s",
                        i,
                        total,
                        cli.id,
                        lat,
                        lng,
                        precision,
                    )
                else:
                    cli.latitude = lat
                    cli.longitude = lng
                    cli.geocoding_precision = precision
                    db.commit()
                    logger.info(
                        "[%d/%d] OK cliente_id=%s precision=%s", i, total, cli.id, precision
                    )
                ok += 1
            except Exception as exc:
                falhas += 1
                logger.exception(
                    "[%d/%d] ERRO cliente_id=%s: %s", i, total, cli.id, type(exc).__name__
                )
                db.rollback()
            time.sleep(args.sleep_ms / 1000.0)

        logger.info("backfill_geocode_clientes: ok=%d falhas=%d total=%d", ok, falhas, total)
        return 0 if falhas == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
