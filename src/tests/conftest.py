import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from config.dependencies import get_settings
from database.session_test import get_test_db, reset_test_database, TestSessionLocal
from database import get_db
from database.models.accounts import UserModel, UserGroupModel, UserGroupEnum
from database.populate import CSVDatabaseSeeder
from security.token_manager import JWTAuthManager
from storages import S3StorageClient
from tests.doubles.fakes.storage import FakeS3Storage
from tests.doubles.stubs.emails import StubEmailSender
import pytest_asyncio
from httpx import AsyncClient
from httpx import ASGITransport
from main import app
import pytest

pytest_plugins = "pytest_asyncio"

def pytest_configure():
    pytest.asyncio_mode = "auto"


# Event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Clear test DB before testing
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    await reset_test_database()


# Override get_db to get_test_db
@pytest.fixture(scope="function")
def app_with_test_db():
    app.dependency_overrides[get_db] = get_test_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client(app_with_test_db):
    """
    Create an async client for testing FastAPI application.
    """
    async with AsyncClient(transport=ASGITransport(app=app_with_test_db), base_url="http://test") as client:
        yield client


# Async session DB for test
@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


# JWT manager
@pytest.fixture(scope="function")
def jwt_manager():
    settings = get_settings()
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )


# Fixture for User Groups
@pytest_asyncio.fixture(scope="function")
async def seed_user_groups(db_session: AsyncSession):
    groups = [{"name": group.value} for group in UserGroupEnum]
    await db_session.execute(insert(UserGroupModel).values(groups))
    await db_session.commit()
    yield db_session


# Preparing test data
@pytest_asyncio.fixture(scope="function")
async def seed_database(db_session: AsyncSession):
    settings = get_settings()
    seeder = CSVDatabaseSeeder(csv_file_path=settings.PATH_TO_MOVIES_CSV, db_session=db_session)
    if not await seeder.is_db_populated():
        await seeder.seed()
    yield db_session


# Test user fixture
@pytest_asyncio.fixture(scope="function")
async def create_test_user(db_session: AsyncSession):
    user = UserModel(email="testuser@example.com", group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# Mock services
@pytest.fixture(scope="function")
def email_sender_stub():
    return StubEmailSender()


@pytest.fixture(scope="function")
def s3_storage_fake():
    return FakeS3Storage()


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def s3_client(settings):
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME,
    )
