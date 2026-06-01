import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context
from app.core.config import settings


from sqlmodel import SQLModel
from app.staff.model import Staff, Directorate, Department
from app.tickets.model import Ticket
from app.ict_personnel.model import IctPersonnel
from app.assets.model import Asset, AssetAllocation
from app.audit.model import AuditLog
from app.auth.model import Session

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


DATABASE_URL = settings.DATABASE_URL.replace("?sslmode=require", "")
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
        connect_args={"ssl": True}
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
