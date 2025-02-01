import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database.models import movies, accounts  # noqa: F401
from database.models.base import Base
from database.session_postgresql import postgresql_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

async_engine = create_async_engine(postgresql_url, echo=True)

async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    connectable = async_engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True, compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine

    async with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True, compare_server_default=True
        )

        async with connection.begin():
            await context.run_migrations()


def run_migrations() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())


if __name__ == "__main__":
    run_migrations()
