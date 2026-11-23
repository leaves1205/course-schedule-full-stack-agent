"""Run Alembic migrations from Python (used by manage.py and the tests)."""

from alembic import command
from alembic.config import Config

from app.config import BASE_DIR


def alembic_config(connection=None) -> Config:
    """Build the Alembic config. Passing a connection migrates that connection instead of DATABASE_URL."""
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    config.attributes["configure_logger"] = False
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def upgrade(connection=None, revision: str = "head") -> None:
    command.upgrade(alembic_config(connection), revision)


def downgrade(connection=None, revision: str = "base") -> None:
    command.downgrade(alembic_config(connection), revision)
