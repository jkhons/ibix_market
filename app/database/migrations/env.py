# Alembic env.py - PDV Ibix
# A URL do banco é obtida de app.database.connection.get_database_url() (PostgreSQL).

import sys
from pathlib import Path

# Garantir que o projeto esteja no path (raiz do repositório)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from logging.config import fileConfig

import app.models  # noqa: F401 - registra todos os modelos no Base.metadata
from alembic import context
from app.database.base import Base

# Importar URL da aplicação e metadata dos modelos
from app.database.connection import get_database_url
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (gera SQL sem conectar)."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (conecta ao banco)."""
    configuration = config.get_section(config.config_ini_section, {}) or {}
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
