from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import get_settings
from database import Base

settings = get_settings()

SQLITE_DATABASE_URL = f"sqlite+aiosqlite:///{settings.PATH_TO_DB}"
sqlite_engine = create_async_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})
SqliteSessionLocal = async_sessionmaker(bind=sqlite_engine, autocommit=False, autoflush=False, expire_on_commit=False)


async def get_sqlite_db() -> AsyncSession:
    async with SqliteSessionLocal() as db:
        yield db


@asynccontextmanager
async def get_sqlite_db_contextmanager() -> AsyncSession:
    async with SqliteSessionLocal() as db:
        yield db


async def reset_sqlite_database():
    async with sqlite_engine.begin() as conn:
        conn.run_sync(Base.metadata.drop_all)
        conn.run_sync(Base.metadata.create_all)
