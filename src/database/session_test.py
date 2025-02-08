import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import get_settings
from database.models import Base

settings = get_settings()

# in-memory SQLite DB
TEST_DATABASE_URL = settings.PATH_TO_DB

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False)


async def get_test_db() -> AsyncSession:
    """session test DB"""
    async with TestSessionLocal() as db:
        yield db


async def reset_test_database():
    """reset test DB"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def delete_test_database():
    if TEST_DATABASE_URL.startswith("sqlite") and settings.PATH_TO_DB != ":memory:":
        db_path = settings.PATH_TO_DB.replace("sqlite+aiosqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)
