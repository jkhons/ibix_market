# PDV Ibix - Config Google Custom Search: DB (configuracoes) com fallback env
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Configuracao

CHAVE_GOOGLE_CSE_API_KEY = "google_cse_api_key"
CHAVE_GOOGLE_CSE_ENGINE_ID = "google_cse_engine_id"
CHAVE_GOOGLE_CSE_QUERY_SUFFIX = "google_cse_query_suffix"
CHAVE_GOOGLE_CSE_PLATAFORMA_LIMITE_DIARIO = "google_cse_plataforma_limite_diario"


def _get_from_db(db: Optional[Session], chave: str) -> Optional[str]:
    if not db:
        return None
    row = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if row and row.valor is not None and str(row.valor).strip():
        return str(row.valor).strip()
    return None


def get_google_cse_api_key(db: Optional[Session] = None) -> str:
    """API Key. Ordem: Configuracao → env GOOGLE_CUSTOM_SEARCH_API_KEY."""
    import os

    val = _get_from_db(db, CHAVE_GOOGLE_CSE_API_KEY)
    if val is not None:
        return val
    return (os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY") or "").strip()


def get_google_cse_engine_id(db: Optional[Session] = None) -> str:
    """Search engine ID (cx). Ordem: Configuracao → env GOOGLE_CUSTOM_SEARCH_ENGINE_ID."""
    import os

    val = _get_from_db(db, CHAVE_GOOGLE_CSE_ENGINE_ID)
    if val is not None:
        return val
    return (os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID") or "").strip()


def google_cse_credentials_configured(db: Optional[Session] = None) -> bool:
    return bool(get_google_cse_api_key(db) and get_google_cse_engine_id(db))


def get_google_cse_query_suffix(db: Optional[Session] = None) -> str:
    """Sufixo opcional concatenado ao nome do produto na busca (ex.: NCM ficha técnica)."""
    val = _get_from_db(db, CHAVE_GOOGLE_CSE_QUERY_SUFFIX)
    if val is not None:
        return val.strip()
    return ""


def get_plataforma_limite_diario_informativo(db: Optional[Session] = None) -> Optional[int]:
    """Teto informacional (opcional) para o painel Superadmin."""
    val = _get_from_db(db, CHAVE_GOOGLE_CSE_PLATAFORMA_LIMITE_DIARIO)
    if val is None or not str(val).strip():
        return None
    try:
        return int(val)
    except ValueError:
        return None


def build_search_query(nome_base: str, db: Optional[Session] = None) -> str:
    """Monta o parâmetro q enviado ao Google (máx. 500 caracteres API)."""
    base = (nome_base or "").strip()
    suffix = get_google_cse_query_suffix(db)
    if suffix:
        q = f"{base} {suffix}".strip()
    else:
        q = base
    if len(q) > 500:
        q = q[:500]
    return q


def get_credentials_for_request(db: Session) -> Tuple[str, str]:
    """Retorna (api_key, cx) ou ('','') se não configurado."""
    return get_google_cse_api_key(db), get_google_cse_engine_id(db)
