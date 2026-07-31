# PDV Ibix - Database Connection (PostgreSQL)
import os
from urllib.parse import quote_plus

from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _env(key: str, default: str) -> str:
    """Lê variável de ambiente e remove espaços/newlines (evita 'localhost\\n' etc.)."""
    return (os.getenv(key) or default).strip()


def _env_int(key: str, default: int) -> int:
    """Lê variável de ambiente como inteiro."""
    val = os.getenv(key)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


# Configuração do banco de dados (PostgreSQL)
DB_USER = _env("DB_USER", "postgres")
DB_PASSWORD = _env("DB_PASSWORD", "")
DB_HOST = _env("DB_HOST", "localhost")
DB_PORT = _env("DB_PORT", "5432")
DB_NAME = _env("DB_NAME", "pdv_solumatica")


def get_database_url():
    """Retorna a URL de conexão com o banco de dados (PostgreSQL). Senha com caracteres especiais é codificada."""
    password_encoded = quote_plus(DB_PASSWORD) if DB_PASSWORD else ""
    return f"postgresql+psycopg2://{quote_plus(DB_USER)}:{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def _get_connect_args():
    """Argumentos de conexão PostgreSQL."""
    return {"options": "-c client_encoding=utf8"}


# Pool de conexões (configurável por env; total_conexões = (gunicorn + celery workers) × (pool_size + max_overflow) < max_connections)
# SET LOCAL (statement_timeout, futuro RLS) é aplicado por request em get_db — compatível com PgBouncer transaction mode.
_pool_kw = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": _env_int("DB_POOL_SIZE", 10),
    "max_overflow": _env_int("DB_MAX_OVERFLOW", 5),
    "pool_timeout": _env_int("DB_POOL_TIMEOUT", 10),
    "pool_reset_on_return": "rollback",
}

# Criar engine do SQLAlchemy
engine = create_engine(
    get_database_url(),
    **_pool_kw,
    connect_args=_get_connect_args(),
    echo=False  # Set to True for SQL debugging
)

# Criar sessão local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()


def open_db_session(
    *,
    tenant_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    bypass_rls: Optional[bool] = None,
):
    """Sessão com SET LOCAL statement_timeout + RLS (middleware, workers, scripts)."""
    from app.core.db_session_scope import apply_db_session_locals

    db = SessionLocal()
    apply_db_session_locals(
        db,
        tenant_id=tenant_id,
        brand_id=brand_id,
        bypass_rls=bypass_rls,
    )
    return db


def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = open_db_session()
    try:
        yield db
    finally:
        db.close()


def get_db_pre_auth():
    """Sessão para login/cadastro/recuperação de senha (tenant ainda desconhecido).

    Com RLS ativo, consultas a usuarios/tenants sem bypass retornam zero linhas para
    registros com tenant_id preenchido — o login falhava com «Email ou senha incorretos».
    """
    from app.core.rls import rls_enabled

    db = open_db_session(bypass_rls=True if rls_enabled() else None)
    try:
        yield db
    finally:
        db.close()
