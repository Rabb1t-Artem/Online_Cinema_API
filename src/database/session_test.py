from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import get_settings
from database.models import Base

settings = get_settings()

# in-memory SQLite DB
TEST_DATABASE_URL = settings.PATH_TO_DB

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False)


# session test DB
async def get_test_db() -> AsyncSession:
    async with TestSessionLocal() as db:
        yield db


# reset test DB
async def reset_test_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
