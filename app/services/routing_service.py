# PDV Ibix - Servico de roteamento (distance matrix)
# Calcula distancia/tempo de carro (driving) entre uma origem e varios destinos.
# Provedores em ordem de preferencia (selecao automatica por presenca de chave):
#   1. Google Distance Matrix API (GOOGLE_MAPS_API_KEY) - mais certeiro
#   2. OSRM publico (router.project-osrm.org) - gratuito, "best effort"
#   3. Fallback Haversine (sempre disponivel; marcado como is_estimate=True)
# Cache em Redis por geohash da origem para reduzir custo/latencia.
import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import List, Optional, Sequence, Tuple

import httpx

from ..core.redis_client import get_redis_client, prefix_key
from .geo_service import haversine_km

logger = logging.getLogger(__name__)

_ROUTING_CACHE_TTL = int(os.getenv("ROUTING_CACHE_TTL", str(60 * 60 * 24)))  # 24h
_ROUTING_BATCH = int(os.getenv("ROUTING_BATCH", "25"))
_ROUTING_HTTP_TIMEOUT = float(os.getenv("ROUTING_HTTP_TIMEOUT", "15"))
_ROUTING_GEOHASH_PRECISION = int(os.getenv("ROUTING_GEOHASH_PRECISION", "7"))  # ~150m


@dataclass
class RouteLeg:
    """Resultado de um destino. Distancia em km e duracao em minutos.
    is_estimate=True quando vem do Haversine (sem rota real).
    """
    lat: float
    lng: float
    distance_km: float
    duration_min: Optional[float] = None
    provider: Optional[str] = None
    is_estimate: bool = False


# ---------------------------------------------------------------------------
# Geohash mini-implementation (sem dependencia externa)
# ---------------------------------------------------------------------------
_GEOHASH_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def _encode_geohash(lat: float, lng: float, precision: int) -> str:
    lat_lo, lat_hi = -90.0, 90.0
    lng_lo, lng_hi = -180.0, 180.0
    geohash: List[str] = []
    bits: List[int] = []
    bit = 0
    even = True
    ch = 0
    while len(geohash) < precision:
        if even:
            mid = (lng_lo + lng_hi) / 2
            if lng > mid:
                ch |= 1 << (4 - bit)
                lng_lo = mid
            else:
                lng_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat > mid:
                ch |= 1 << (4 - bit)
                lat_lo = mid
            else:
                lat_hi = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(_GEOHASH_BASE32[ch])
            bits.append(ch)
            bit = 0
            ch = 0
    return "".join(geohash)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_key(origin_geohash: str, dest_lat: float, dest_lng: float) -> str:
    return prefix_key(
        f"routing:{origin_geohash}:{round(dest_lat, 5)}:{round(dest_lng, 5)}"
    )


def _cache_get(origin_geohash: str, destination: Tuple[float, float]) -> Optional[RouteLeg]:
    redis = get_redis_client()
    if not redis:
        return None
    try:
        cached = redis.get(_cache_key(origin_geohash, destination[0], destination[1]))
        if not cached:
            return None
        return RouteLeg(**json.loads(cached))
    except Exception:
        return None


def _cache_set(origin_geohash: str, leg: RouteLeg) -> None:
    redis = get_redis_client()
    if not redis:
        return
    try:
        redis.setex(
            _cache_key(origin_geohash, leg.lat, leg.lng),
            _ROUTING_CACHE_TTL,
            json.dumps(asdict(leg)),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def distance_matrix(
    origin: Tuple[float, float],
    destinations: Sequence[Tuple[float, float]],
) -> List[RouteLeg]:
    """Calcula distancia/tempo de carro da origem para cada destino, na mesma ordem.

    Politica:
      - Google Distance Matrix se GOOGLE_MAPS_API_KEY estiver configurada.
      - Caso contrario, OSRM publico.
      - Em caso de falha de rede/HTTP, marca is_estimate=True e usa Haversine.
      - Cache por geohash da origem (precisao ~150m) economiza chamadas para
        moradores na mesma quadra consultando as mesmas lojas.
    """
    if not destinations:
        return []

    origin_geohash = _encode_geohash(origin[0], origin[1], _ROUTING_GEOHASH_PRECISION)

    out: List[Optional[RouteLeg]] = [None] * len(destinations)
    pendentes_idx: List[int] = []
    for idx, dest in enumerate(destinations):
        cached = _cache_get(origin_geohash, dest)
        if cached:
            out[idx] = cached
        else:
            pendentes_idx.append(idx)

    if pendentes_idx:
        google_key = (os.getenv("GOOGLE_MAPS_API_KEY") or "").strip() or None
        for batch_start in range(0, len(pendentes_idx), _ROUTING_BATCH):
            batch_idx = pendentes_idx[batch_start : batch_start + _ROUTING_BATCH]
            batch_dests = [destinations[i] for i in batch_idx]
            legs: Optional[List[RouteLeg]] = None
            if google_key:
                legs = _google_distance_matrix(google_key, origin, batch_dests)
            if legs is None:
                legs = _osrm_distance_matrix(origin, batch_dests)
            if legs is None:
                legs = _haversine_legs(origin, batch_dests)
            for k, leg in enumerate(legs):
                out[batch_idx[k]] = leg
                if not leg.is_estimate:
                    _cache_set(origin_geohash, leg)

    final: List[RouteLeg] = []
    for idx, leg in enumerate(out):
        if leg is None:
            d = destinations[idx]
            final.append(
                RouteLeg(
                    lat=d[0],
                    lng=d[1],
                    distance_km=round(haversine_km(origin[0], origin[1], d[0], d[1]), 2),
                    duration_min=None,
                    provider="haversine",
                    is_estimate=True,
                )
            )
        else:
            final.append(leg)
    return final


# ---------------------------------------------------------------------------
# Provedores
# ---------------------------------------------------------------------------

def _google_distance_matrix(
    api_key: str,
    origin: Tuple[float, float],
    destinations: Sequence[Tuple[float, float]],
) -> Optional[List[RouteLeg]]:
    try:
        params = {
            "origins": f"{origin[0]},{origin[1]}",
            "destinations": "|".join(f"{lat},{lng}" for lat, lng in destinations),
            "mode": "driving",
            "language": "pt-BR",
            "region": "br",
            "key": api_key,
        }
        with httpx.Client(timeout=_ROUTING_HTTP_TIMEOUT) as client:
            r = client.get(
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params=params,
            )
            r.raise_for_status()
            data = r.json()
        if data.get("status") != "OK":
            logger.info("routing_service: google status=%s", data.get("status"))
            return None
        rows = data.get("rows") or []
        if not rows:
            return None
        elements = rows[0].get("elements") or []
        if len(elements) != len(destinations):
            return None
        legs: List[RouteLeg] = []
        for el, (lat, lng) in zip(elements, destinations):
            if el.get("status") != "OK":
                legs.append(
                    RouteLeg(
                        lat=lat,
                        lng=lng,
                        distance_km=round(haversine_km(origin[0], origin[1], lat, lng), 2),
                        duration_min=None,
                        provider="haversine",
                        is_estimate=True,
                    )
                )
                continue
            distance_m = (el.get("distance") or {}).get("value") or 0
            duration_s = (el.get("duration") or {}).get("value") or 0
            legs.append(
                RouteLeg(
                    lat=lat,
                    lng=lng,
                    distance_km=round(distance_m / 1000.0, 2),
                    duration_min=round(duration_s / 60.0, 1),
                    provider="google",
                    is_estimate=False,
                )
            )
        return legs
    except Exception as exc:
        logger.info("routing_service: google falhou erro=%s", type(exc).__name__)
        return None


def _osrm_distance_matrix(
    origin: Tuple[float, float],
    destinations: Sequence[Tuple[float, float]],
) -> Optional[List[RouteLeg]]:
    try:
        coords = [f"{origin[1]},{origin[0]}"] + [f"{lng},{lat}" for lat, lng in destinations]
        url = (
            "https://router.project-osrm.org/table/v1/driving/"
            + ";".join(coords)
            + "?annotations=duration,distance&sources=0"
        )
        with httpx.Client(timeout=_ROUTING_HTTP_TIMEOUT) as client:
            r = client.get(url)
            r.raise_for_status()
            data = r.json()
        if data.get("code") != "Ok":
            return None
        durations_row = (data.get("durations") or [[]])[0]
        distances_row = (data.get("distances") or [[]])[0]
        if len(durations_row) != len(destinations) + 1:
            return None
        legs: List[RouteLeg] = []
        for i, (lat, lng) in enumerate(destinations, start=1):
            dur_s = durations_row[i]
            dist_m = distances_row[i] if distances_row else None
            if dur_s is None or dist_m is None:
                legs.append(
                    RouteLeg(
                        lat=lat,
                        lng=lng,
                        distance_km=round(haversine_km(origin[0], origin[1], lat, lng), 2),
                        duration_min=None,
                        provider="haversine",
                        is_estimate=True,
                    )
                )
                continue
            legs.append(
                RouteLeg(
                    lat=lat,
                    lng=lng,
                    distance_km=round(float(dist_m) / 1000.0, 2),
                    duration_min=round(float(dur_s) / 60.0, 1),
                    provider="osrm",
                    is_estimate=False,
                )
            )
        return legs
    except Exception as exc:
        logger.info("routing_service: osrm falhou erro=%s", type(exc).__name__)
        return None


def _haversine_legs(
    origin: Tuple[float, float],
    destinations: Sequence[Tuple[float, float]],
) -> List[RouteLeg]:
    return [
        RouteLeg(
            lat=lat,
            lng=lng,
            distance_km=round(haversine_km(origin[0], origin[1], lat, lng), 2),
            duration_min=None,
            provider="haversine",
            is_estimate=True,
        )
        for (lat, lng) in destinations
    ]
