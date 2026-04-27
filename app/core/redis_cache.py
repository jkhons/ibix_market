# PDV Ibix - Cache Redis (subscription_blocked, permissões, regras fiscais)
# Fallback para DB quando Redis indisponível. Chaves com prefixo (redis_client.prefix_key) para segurança e isolamento.
import json
import os
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Callable, List, Optional

from .redis_client import get_redis_client, prefix_key

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

SUB_BLOCKED_TTL = 90  # segundos
PERMS_TTL = 300  # segundos
LOJA_CATEGORIAS_TTL = 60  # segundos (alinhado ao Cache-Control da resposta)

_REGRA_FISCAL_ICMS_TTL = int(os.getenv("REGRA_FISCAL_ICMS_TTL", "300"))


def _cache_get(key: str) -> Optional[str]:
    client = get_redis_client()
    if client is None:
        return None
    try:
        return client.get(prefix_key(key))
    except Exception:
        return None


def _cache_set(key: str, value: str, ttl: int) -> bool:
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(prefix_key(key), ttl, value)
        return True
    except Exception:
        return False


def get_loja_categorias_cached(cache_key_suffix: str, fetch_from_db: Callable[[], List[dict]]) -> List[dict]:
    """
    Retorna lista de categorias da vitrine (cada item um dict serializável).
    fetch_from_db: callable que retorna a lista de dicts (ex.: [r.__dict__ ou model_dump]).
    """
    key = f"loja:categorias:{cache_key_suffix}"
    cached = _cache_get(key)
    if cached is not None:
        try:
            return json.loads(cached)
        except Exception:
            pass
    data = fetch_from_db()
    try:
        _cache_set(key, json.dumps(data, default=str), LOJA_CATEGORIAS_TTL)
    except Exception:
        pass
    return data


def _cache_delete(key: str) -> bool:
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.delete(prefix_key(key))
        return True
    except Exception:
        return False


def get_subscription_blocked_cached(user_id: int, fetch_from_db: Callable[[], bool]) -> bool:
    """
    Retorna se o usuário está bloqueado (assinatura). Usa cache Redis.
    fetch_from_db: callable que retorna is_subscription_blocked(db, user) sem args.
    """
    key = f"sub:blocked:{user_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached == "1"
    blocked = fetch_from_db()
    _cache_set(key, "1" if blocked else "0", SUB_BLOCKED_TTL)
    return blocked


def invalidate_subscription_blocked(user_id: int) -> None:
    """Invalida cache de subscription_blocked para o user_id."""
    _cache_delete(f"sub:blocked:{user_id}")


def invalidate_subscription_blocked_all() -> None:
    """Invalida todos os caches de subscription_blocked. Usar após billing_daily_job."""
    client = get_redis_client()
    if client is None:
        return
    try:
        pattern = prefix_key("sub:blocked:*")
        for key in client.scan_iter(match=pattern):
            client.delete(key)
    except Exception:
        pass


def get_permissions_cached(user_id: int, fetch_from_db: Callable[[], List[str]]) -> List[str]:
    """
    Retorna lista de permissões do usuário. Usa cache Redis.
    fetch_from_db: callable que retorna a lista de permissões.
    """
    key = f"perms:{user_id}"
    cached = _cache_get(key)
    if cached is not None:
        try:
            return json.loads(cached)
        except (json.JSONDecodeError, TypeError):
            pass
    perms = fetch_from_db()
    _cache_set(key, json.dumps(perms), PERMS_TTL)
    return perms


def invalidate_permissions(user_id: int) -> None:
    """Invalida cache de permissões para o user_id."""
    _cache_delete(f"perms:{user_id}")


def add_token_to_blacklist(jti: str, ttl_seconds: int) -> bool:
    """Adiciona token à blacklist (logout). Retorna True se gravou, False se Redis indisponível."""
    if ttl_seconds <= 0:
        return True
    key = f"blacklist:{jti}"
    return _cache_set(key, "1", ttl_seconds)


def is_token_blacklisted(jti: str) -> bool:
    """Verifica se o token está na blacklist. Retorna True se blacklisted ou Redis indisponível = fail-open (não bloqueia)."""
    client = get_redis_client()
    if client is None:
        return False  # fail-open
    try:
        return client.exists(prefix_key(f"blacklist:{jti}")) > 0
    except Exception:
        return False  # fail-open


def invalidate_permissions_for_role(role_id: int, db: "Session") -> None:
    """Invalida cache de permissões para todos os usuários com a role_id. Usa pipeline para uma única ida ao Redis."""
    from ..models import Usuario
    client = get_redis_client()
    user_ids = db.query(Usuario.id).filter(Usuario.role_id == role_id).all()
    if not user_ids:
        return
    if client is None:
        for (uid,) in user_ids:
            invalidate_permissions(uid)
        return
    try:
        keys = [prefix_key(f"perms:{uid}") for (uid,) in user_ids]
        client.delete(*keys)
    except Exception:
        for (uid,) in user_ids:
            invalidate_permissions(uid)


# --- Regras Fiscais ICMS (cache por empresa) ---

def _regra_para_dict(regra) -> dict:
    """Serializa RegraFiscalIcms ou RegraFiscalIcmsCache para dict (JSON)."""
    top = getattr(regra.tipo_operacao, "value", regra.tipo_operacao) if regra.tipo_operacao else None
    td = getattr(regra.tipo_destinatario, "value", regra.tipo_destinatario) if regra.tipo_destinatario else None
    return {
        "id": regra.id,
        "empresa_id": regra.empresa_id,
        "crt": regra.crt,
        "tipo_operacao": top,
        "tipo_destinatario": td,
        "uf_destinatario": regra.uf_destinatario,
        "ncm_prefix": regra.ncm_prefix,
        "ncm_exato": regra.ncm_exato,
        "cest": regra.cest,
        "cfop_filtro": regra.cfop_filtro,
        "vigencia_inicio": regra.vigencia_inicio.isoformat() if regra.vigencia_inicio else None,
        "vigencia_fim": regra.vigencia_fim.isoformat() if regra.vigencia_fim else None,
        "cfop": regra.cfop,
        "origem_mercadoria": regra.origem_mercadoria,
        "cst_icms": regra.cst_icms,
        "csosn": regra.csosn,
        "aliquota_icms": str(regra.aliquota_icms) if regra.aliquota_icms is not None else "0",
        "modalidade_bc_icms": regra.modalidade_bc_icms,
        "percentual_reducao_bc": str(regra.percentual_reducao_bc) if regra.percentual_reducao_bc is not None else None,
        "gera_icms_st": bool(regra.gera_icms_st),
        "aliquota_icms_st": str(regra.aliquota_icms_st) if regra.aliquota_icms_st is not None else None,
        "modalidade_bc_icms_st": regra.modalidade_bc_icms_st,
        "percentual_mva_st": str(regra.percentual_mva_st) if regra.percentual_mva_st is not None else None,
        "permite_credito_icms": regra.permite_credito_icms,
        "ordem_prioridade": regra.ordem_prioridade,
    }


def _dict_para_regra_cache(d: dict):
    """Deserializa dict para RegraFiscalIcmsCache."""
    from ..services.fiscal.motor_tributario_icms import RegraFiscalIcmsCache
    return RegraFiscalIcmsCache(
        id=d["id"],
        empresa_id=d["empresa_id"],
        crt=d.get("crt"),
        tipo_operacao=d.get("tipo_operacao"),
        tipo_destinatario=d.get("tipo_destinatario"),
        uf_destinatario=d.get("uf_destinatario"),
        ncm_prefix=d.get("ncm_prefix"),
        ncm_exato=d.get("ncm_exato"),
        cest=d.get("cest"),
        cfop_filtro=d.get("cfop_filtro"),
        vigencia_inicio=date.fromisoformat(d["vigencia_inicio"]) if d.get("vigencia_inicio") else None,
        vigencia_fim=date.fromisoformat(d["vigencia_fim"]) if d.get("vigencia_fim") else None,
        cfop=d["cfop"],
        origem_mercadoria=d.get("origem_mercadoria", 0),
        cst_icms=d.get("cst_icms"),
        csosn=d.get("csosn"),
        aliquota_icms=Decimal(d.get("aliquota_icms", "0") or "0"),
        modalidade_bc_icms=d.get("modalidade_bc_icms"),
        percentual_reducao_bc=Decimal(d["percentual_reducao_bc"]) if d.get("percentual_reducao_bc") else None,
        gera_icms_st=bool(d.get("gera_icms_st", False)),
        aliquota_icms_st=Decimal(d["aliquota_icms_st"]) if d.get("aliquota_icms_st") else None,
        modalidade_bc_icms_st=d.get("modalidade_bc_icms_st"),
        percentual_mva_st=Decimal(d["percentual_mva_st"]) if d.get("percentual_mva_st") else None,
        permite_credito_icms=d.get("permite_credito_icms"),
        ordem_prioridade=d.get("ordem_prioridade", 100),
    )


def get_regras_fiscais_empresa_cached(
    empresa_id: int,
    fetch_from_db: Callable[[], List],
) -> List:
    """
    Retorna regras ativas da empresa (cache Redis). fetch_from_db retorna List[RegraFiscalIcms].
    Retorno: List[RegraFiscalIcms] do DB ou List[RegraFiscalIcmsCache] do cache.
    """
    key = f"regras_fiscais_icms:empresa:{empresa_id}"
    cached = _cache_get(key)
    if cached is not None:
        try:
            data = json.loads(cached)
            return [_dict_para_regra_cache(item) for item in data]
        except Exception:
            pass
    regras = fetch_from_db()
    try:
        serialized = json.dumps([_regra_para_dict(r) for r in regras], default=str)
        _cache_set(key, serialized, _REGRA_FISCAL_ICMS_TTL)
    except Exception:
        pass
    return regras


def invalidate_regras_fiscais_empresa(empresa_id: int) -> None:
    """Invalida cache de regras fiscais da empresa."""
    _cache_delete(f"regras_fiscais_icms:empresa:{empresa_id}")


def invalidate_regras_fiscais_all() -> None:
    """Invalida todos os caches de regras fiscais (útil para manutenção)."""
    client = get_redis_client()
    if client is None:
        return
    try:
        pattern = prefix_key("regras_fiscais_icms:empresa:*")
        for key in client.scan_iter(match=pattern):
            client.delete(key)
    except Exception:
        pass
