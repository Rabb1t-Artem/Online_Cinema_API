from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import get_settings

settings = get_settings()

POSTGRESQL_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_HOST}:{settings.POSTGRES_DB_PORT}/{settings.POSTGRES_DB}"
)

postgresql_engine = create_async_engine(POSTGRESQL_DATABASE_URL)

PostgresqlSessionLocal = async_sessionmaker(
    bind=postgresql_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


async def get_postgresql_db() -> AsyncSession:
    async with PostgresqlSessionLocal() as db:
        yield db


@asynccontextmanager
async def get_postgresql_db_contextmanager() -> AsyncSession:
    async with PostgresqlSessionLocal() as db:
        yield db
