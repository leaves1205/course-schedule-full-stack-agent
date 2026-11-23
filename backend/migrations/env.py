"""Alembic environment: connects to DATABASE_URL and compares against the SQLAlchemy models."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (importing registers every table on Base.metadata)
from app.config import settings
from app.database import Base

config = context.config
# Tests and manage.py pass their own connection and keep the host's logging configuration.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """The migrations inspect the live schema so they can adopt databases that predate Alembic."""
    raise SystemExit(
        "Offline mode (--sql) is not supported: the migrations adapt to the tables that already exist. "
        "Run `alembic upgrade head` against the database instead."
    )


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
