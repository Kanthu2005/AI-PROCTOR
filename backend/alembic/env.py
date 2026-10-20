from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database import Base, resolve_database_url
import app.models  # noqa: F401

# Support migration IDs up to 64 chars in PostgreSQL without right-truncation
import alembic.ddl.impl as alembic_impl
from sqlalchemy import Table, MetaData, Column, String, PrimaryKeyConstraint

def _wide_version_table_impl(self, *, version_table, version_table_schema, version_table_pk, **kw):
    vt = Table(
        version_table,
        MetaData(),
        Column("version_num", String(64), nullable=False),
        schema=version_table_schema,
    )
    if version_table_pk:
        vt.append_constraint(PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc"))
    return vt

alembic_impl.DefaultImpl.version_table_impl = _wide_version_table_impl

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set sqlalchemy.url from our settings (escaped for configparser interpolation)
config.set_main_option("sqlalchemy.url", resolve_database_url(settings.DATABASE_URL).replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_num_length=64,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the primary application engine."""
    from app.database import engine

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_num_length=64,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
