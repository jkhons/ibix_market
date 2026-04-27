# PDV Ibix - Servico de geocodificacao
# Geocodificacao certeira (CEP + numero) e por CEP isolado.
# Provedores em ordem de preferencia (selecao automatica por presenca de chave):
#   1. Google Maps Geocoding API     -> rooftop / range_interpolated / locality
#   2. BrasilAPI v2 + Nominatim/OSM  -> fallback gratuito (precisao varia)
# Cache em Redis para reduzir custo e latencia.
import json
import logging
import math
import os
import re
from dataclasses import asdict, dataclass
from typing import Optional, Tuple

import httpx

from ..core.redis_client import get_redis_client, prefix_key

logger = logging.getLogger(__name__)

_CEP_RE = re.compile(r"^\d{5}-?\d{3}$")
_GEO_CACHE_TTL = 86400  # 24h (cache CEP isolado)
_ADDR_CACHE_TTL = int(os.getenv("GEO_ADDR_CACHE_TTL", str(60 * 60 * 24 * 30)))  # 30 dias


# Precisoes esperadas (compativel com Google Geocoding).
PRECISION_ROOFTOP = "rooftop"
PRECISION_RANGE = "range_interpolated"
PRECISION_GEOMETRIC_CENTER = "geometric_center"
PRECISION_APPROXIMATE = "approximate"
PRECISION_LOCALITY = "locality"
PRECISION_MANUAL = "manual"

# Precisoes consideradas "certeiras" (rooftop ou interpoladas no logradouro).
PRECISIONS_PRECISE = {PRECISION_ROOFTOP, PRECISION_RANGE, PRECISION_GEOMETRIC_CENTER}


@dataclass
class GeocodeResult:
    lat: float
    lng: float
    precision: str
    cidade: Optional[str] = None
    uf: Optional[str] = None
    bairro: Optional[str] = None
    endereco_formatado: Optional[str] = None
    provider: Optional[str] = None

    def is_precise(self) -> bool:
        return self.precision in PRECISIONS_PRECISE


def _clean_cep(cep: str) -> Optional[str]:
    """Remove formatacao e valida 8 digitos."""
    if not cep:
        return None
    cleaned = re.sub(r"\D", "", cep.strip())
    if len(cleaned) != 8:
        return None
    return cleaned


def _bbox_brasil(lat: float, lng: float) -> bool:
    return -34 <= lat <= 6 and -74 <= lng <= -28


def _google_api_key() -> Optional[str]:
    return (os.getenv("GOOGLE_MAPS_API_KEY") or "").strip() or None


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_get(cache_key: str) -> Optional[GeocodeResult]:
    redis = get_redis_client()
    if not redis:
        return None
    try:
        cached = redis.get(cache_key)
        if not cached:
            return None
        data = json.loads(cached)
        return GeocodeResult(**data)
    except Exception:
        return None


def _cache_set(cache_key: str, result: GeocodeResult, ttl: int) -> None:
    redis = get_redis_client()
    if not redis:
        return
    try:
        redis.setex(cache_key, ttl, json.dumps(asdict(result)))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Geocodificacao por endereco completo (CEP + numero) - "certeiro"
# ---------------------------------------------------------------------------

def geocode_address(
    cep: str,
    numero: Optional[str] = None,
    complemento: Optional[str] = None,
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
) -> Optional[GeocodeResult]:
    """Geocodifica endereco residencial brasileiro com a melhor precisao disponivel.

    Ordem dos provedores:
      1. Google Geocoding API (se GOOGLE_MAPS_API_KEY configurada)
      2. BrasilAPI v2 (logradouro do CEP) + Nominatim/OSM (logradouro + numero)
      3. BrasilAPI v2 isolado (fallback CEP -> ponto do CEP)

    Retorna GeocodeResult com `precision` para o caller decidir se aceita
    (ex.: rejeitar `locality` em fluxos que exigem rooftop).
    """
    cep_limpo = _clean_cep(cep)
    if not cep_limpo:
        return None

    numero_norm = (numero or "").strip()
    complemento_norm = (complemento or "").strip()

    cache_key = prefix_key(
        f"geo:addr:{cep_limpo}:{numero_norm.lower()}:{complemento_norm.lower()}"
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Provedor 1: Google.
    google_key = _google_api_key()
    if google_key:
        result = _geocode_google_address(google_key, cep_limpo, numero_norm, complemento_norm)
        if result and _bbox_brasil(result.lat, result.lng):
            _cache_set(cache_key, result, _ADDR_CACHE_TTL)
            return result

    # Provedor 2/3: BrasilAPI + Nominatim.
    result = _geocode_brasilapi_nominatim(cep_limpo, numero_norm, cidade, uf)
    if result and _bbox_brasil(result.lat, result.lng):
        _cache_set(cache_key, result, _ADDR_CACHE_TTL)
        return result

    logger.warning("geo_service: geocode_address falhou cep=%s", cep_limpo[:5])
    return None


def _geocode_google_address(
    api_key: str,
    cep_limpo: str,
    numero: str,
    complemento: str,
) -> Optional[GeocodeResult]:
    parts = []
    if numero:
        parts.append(numero)
    if complemento:
        parts.append(complemento)
    address = " ".join(parts).strip()
    cep_fmt = f"{cep_limpo[:5]}-{cep_limpo[5:]}"
    query = f"{address}, {cep_fmt}, Brasil" if address else f"{cep_fmt}, Brasil"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": query, "region": "br", "language": "pt-BR", "key": api_key},
            )
            r.raise_for_status()
            data = r.json()
        if data.get("status") != "OK" or not data.get("results"):
            return None
        top = data["results"][0]
        loc = top["geometry"]["location"]
        location_type = (top["geometry"].get("location_type") or "").upper()
        precision_map = {
            "ROOFTOP": PRECISION_ROOFTOP,
            "RANGE_INTERPOLATED": PRECISION_RANGE,
            "GEOMETRIC_CENTER": PRECISION_GEOMETRIC_CENTER,
            "APPROXIMATE": PRECISION_APPROXIMATE,
        }
        precision = precision_map.get(location_type, PRECISION_APPROXIMATE)
        cidade = uf = bairro = None
        for comp in top.get("address_components", []) or []:
            types = comp.get("types") or []
            if "administrative_area_level_2" in types and not cidade:
                cidade = comp.get("long_name")
            if "administrative_area_level_1" in types and not uf:
                uf = (comp.get("short_name") or "").upper() or None
            if "sublocality" in types or "neighborhood" in types:
                bairro = bairro or comp.get("long_name")
        return GeocodeResult(
            lat=float(loc["lat"]),
            lng=float(loc["lng"]),
            precision=precision,
            cidade=cidade,
            uf=uf,
            bairro=bairro,
            endereco_formatado=top.get("formatted_address"),
            provider="google",
        )
    except Exception as exc:
        logger.info("geo_service: google address falhou erro=%s", type(exc).__name__)
        return None


def _geocode_brasilapi_nominatim(
    cep_limpo: str,
    numero: str,
    cidade_in: Optional[str],
    uf_in: Optional[str],
) -> Optional[GeocodeResult]:
    """Combina BrasilAPI (logradouro/cidade/UF do CEP) com Nominatim (refino por logradouro+numero)."""
    logradouro = bairro_brasilapi = None
    cidade = cidade_in
    uf = (uf_in or "").upper() or None
    coords_brasilapi: Optional[Tuple[float, float]] = None
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"https://brasilapi.com.br/api/cep/v2/{cep_limpo}")
            r.raise_for_status()
            data = r.json()
        cidade = (data.get("city") or cidade or "").strip() or None
        uf_remoto = (data.get("state") or "").strip().upper() or None
        if uf_remoto:
            uf = uf_remoto
        bairro_brasilapi = (data.get("neighborhood") or "").strip() or None
        logradouro = (data.get("street") or "").strip() or None
        loc = (data.get("location") or {}).get("coordinates") or {}
        lat_b = loc.get("latitude")
        lng_b = loc.get("longitude")
        if lat_b is not None and lng_b is not None:
            try:
                coords_brasilapi = (float(lat_b), float(lng_b))
            except (TypeError, ValueError):
                coords_brasilapi = None
    except Exception as exc:
        logger.info("geo_service: brasilapi falhou cep=%s erro=%s", cep_limpo[:5], type(exc).__name__)

    # Tentativa de refino por Nominatim com logradouro + numero.
    if logradouro and cidade and uf:
        nominatim = _try_nominatim_address(logradouro, numero, bairro_brasilapi, cidade, uf)
        if nominatim:
            return GeocodeResult(
                lat=nominatim[0],
                lng=nominatim[1],
                precision=(PRECISION_RANGE if numero else PRECISION_APPROXIMATE),
                cidade=cidade,
                uf=uf,
                bairro=bairro_brasilapi,
                endereco_formatado=(
                    f"{logradouro}, {numero}, {bairro_brasilapi or ''} - {cidade}/{uf}".strip(", ")
                ),
                provider="brasilapi+nominatim",
            )

    if coords_brasilapi:
        return GeocodeResult(
            lat=coords_brasilapi[0],
            lng=coords_brasilapi[1],
            precision=PRECISION_APPROXIMATE,
            cidade=cidade,
            uf=uf,
            bairro=bairro_brasilapi,
            endereco_formatado=(
                f"{logradouro or ''}{', ' + numero if numero and logradouro else ''}, {cidade or ''}/{uf or ''}".strip(", ")
            )
            or None,
            provider="brasilapi",
        )

    if cidade and uf:
        nominatim_city = _try_nominatim(cidade, uf)
        if nominatim_city:
            return GeocodeResult(
                lat=nominatim_city[0],
                lng=nominatim_city[1],
                precision=PRECISION_LOCALITY,
                cidade=cidade,
                uf=uf,
                bairro=bairro_brasilapi,
                endereco_formatado=f"{cidade}/{uf}",
                provider="nominatim",
            )

    return None


def _try_nominatim_address(
    logradouro: str,
    numero: str,
    bairro: Optional[str],
    cidade: str,
    uf: str,
) -> Optional[Tuple[float, float]]:
    try:
        params = {
            "street": (f"{numero} " if numero else "") + logradouro.strip(),
            "city": cidade.strip(),
            "state": uf.strip().upper(),
            "country": "Brazil",
            "format": "json",
            "limit": "1",
            "addressdetails": "1",
        }
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers={"User-Agent": "PDV-Ibix/1.0 (geo-service)"},
            )
            r.raise_for_status()
            results = r.json()
        if not results:
            return None
        lat_f = float(results[0]["lat"])
        lng_f = float(results[0]["lon"])
        if -34 <= lat_f <= 6 and -74 <= lng_f <= -28:
            return (lat_f, lng_f)
        return None
    except Exception as exc:
        logger.info(
            "geo_service: nominatim address falhou cidade=%s erro=%s",
            cidade[:20],
            type(exc).__name__,
        )
        return None


# ---------------------------------------------------------------------------
# Geocodificacao por CEP isolado (legado, mantido para compatibilidade)
# ---------------------------------------------------------------------------

def geocode_cep(
    cep: str,
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
) -> Optional[Tuple[float, float]]:
    """Geocodifica CEP brasileiro -> (latitude, longitude) ou None.

    1. Valida formato
    2. Consulta cache Redis
    3. BrasilAPI /cep/v2/{cep} (primario)
    4. Nominatim/OSM com cidade+UF (fallback)
    5. Grava cache se sucesso
    """
    cep_limpo = _clean_cep(cep)
    if not cep_limpo:
        return None

    redis = get_redis_client()
    cache_key = prefix_key(f"geo:cep:{cep_limpo}")

    if redis:
        try:
            cached = redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return (data["lat"], data["lng"])
        except Exception:
            pass

    coords = _try_brasilapi(cep_limpo)

    if coords is None and cidade and uf:
        coords = _try_nominatim(cidade, uf)

    if coords:
        if redis:
            try:
                redis.setex(cache_key, _GEO_CACHE_TTL, json.dumps({"lat": coords[0], "lng": coords[1]}))
            except Exception:
                pass
        return coords

    logger.warning("geo_service: geocodificacao falhou cep_prefixo=%s", cep_limpo[:5])
    return None


def _try_brasilapi(cep_limpo: str) -> Optional[Tuple[float, float]]:
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"https://brasilapi.com.br/api/cep/v2/{cep_limpo}")
            r.raise_for_status()
            data = r.json()
        loc = data.get("location", {}).get("coordinates", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if lat is not None and lng is not None:
            lat_f, lng_f = float(lat), float(lng)
            if _bbox_brasil(lat_f, lng_f):
                return (lat_f, lng_f)
        return None
    except Exception as exc:
        logger.info("geo_service: brasilapi falhou cep_prefixo=%s erro=%s", cep_limpo[:5], type(exc).__name__)
        return None


def _try_nominatim(cidade: str, uf: str) -> Optional[Tuple[float, float]]:
    try:
        q = f"{cidade.strip()}, {uf.strip().upper()}, Brasil"
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": "1"},
                headers={"User-Agent": "PDV-Ibix/1.0 (geo-service)"},
            )
            r.raise_for_status()
            results = r.json()
        if results:
            lat_f = float(results[0]["lat"])
            lng_f = float(results[0]["lon"])
            if _bbox_brasil(lat_f, lng_f):
                return (lat_f, lng_f)
        return None
    except Exception as exc:
        logger.info("geo_service: nominatim falhou cidade=%s erro=%s", cidade[:20], type(exc).__name__)
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia em km entre dois pontos (formula de Haversine)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))
