# import pytest
# from fastapi.testclient import TestClient
# from sqlalchemy import insert
#
# from config import get_settings, get_accounts_email_notificator, get_s3_storage_client
# from database import (
#     reset_database,
#     get_db_contextmanager,
#     # UserGroupEnum,
#     # UserGroupModel,
# )
# from database.populate import CSVDatabaseSeeder
# from main import app
# from security.token_manager import JWTAuthManager
# from storages import S3StorageClient
# from tests.doubles.fakes.storage import FakeS3Storage
# from tests.doubles.stubs.emails import StubEmailSender
#
#
# def pytest_configure(config):
#     config.addinivalue_line("markers", "e2e: End-to-end tests")
#     config.addinivalue_line("markers", "order: Specify the order of test execution")
#     config.addinivalue_line("markers", "unit: Unit tests")
#
#
# @pytest.fixture(scope="function", autouse=True)
# def reset_db(request):
#     if request.node.get_closest_marker("e2e"):
#         return None
#     reset_database()
#
#
# @pytest.fixture(scope="session")
# def reset_db_once_for_e2e(request):
#     reset_database()
#
#
# @pytest.fixture(scope="session")
# def settings():
#     return get_settings()
#
#
# @pytest.fixture(scope="function")
# def email_sender_stub():
#     return StubEmailSender()
#
#
# @pytest.fixture(scope="function")
# def s3_storage_fake():
#     return FakeS3Storage()
#
#
# @pytest.fixture(scope="session")
# def s3_client(settings):
#     return S3StorageClient(
#         endpoint_url=settings.S3_STORAGE_ENDPOINT,
#         access_key=settings.S3_STORAGE_ACCESS_KEY,
#         secret_key=settings.S3_STORAGE_SECRET_KEY,
#         bucket_name=settings.S3_BUCKET_NAME,
#     )
#
#
# @pytest.fixture(scope="function")
# def client(email_sender_stub, s3_storage_fake):
#     app.dependency_overrides[get_accounts_email_notificator] = lambda: email_sender_stub
#     app.dependency_overrides[get_s3_storage_client] = lambda: s3_storage_fake
#
#     with TestClient(app) as test_client:
#         yield test_client
#
#     app.dependency_overrides.clear()
#
#
# @pytest.fixture(scope="session")
# def e2e_client():
#     with TestClient(app) as test_client:
#         yield test_client
#
#
# @pytest.fixture(scope="function")
# def db_session():
#     with get_db_contextmanager() as session:
#         yield session
#
#
# @pytest.fixture(scope="function")
# def jwt_manager(settings):
#     return JWTAuthManager(
#         secret_key_access=settings.SECRET_KEY_ACCESS,
#         secret_key_refresh=settings.SECRET_KEY_REFRESH,
#         algorithm=settings.JWT_SIGNING_ALGORITHM,
#     )
#
#
# @pytest.fixture(scope="function")
# def seed_user_groups(db_session):
#     groups = [{"name": group.value} for group in UserGroupEnum]
#     db_session.execute(insert(UserGroupModel).values(groups))
#     db_session.commit()
#     yield db_session
#
#
# @pytest.fixture(scope="function")
# def seed_database(db_session, settings):
#     seeder = CSVDatabaseSeeder(csv_file_path=settings.PATH_TO_MOVIES_CSV, db_session=db_session)
#     if not seeder.is_db_populated():
#         seeder.seed()
#     yield db_session

import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
# from config.settings import TestingSettings
from config import get_settings, get_accounts_email_notificator, get_s3_storage_client
from database.session_test import get_test_db, reset_test_database, TestSessionLocal
from database import get_db
from database.models.accounts import UserModel, UserGroupModel, UserGroupEnum
from database.populate import CSVDatabaseSeeder
from main import app
from security.token_manager import JWTAuthManager
from storages import S3StorageClient
from tests.doubles.fakes.storage import FakeS3Storage
from tests.doubles.stubs.emails import StubEmailSender


# event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# clear test DB before testing
@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    await reset_test_database()


# override get_db to get_test_db
@pytest.fixture(scope="function")
def app_with_test_db():
    app.dependency_overrides[get_db] = get_test_db
    yield app
    app.dependency_overrides.clear()


# aсинхронний HTTP-клієнт для тестування API
@pytest.fixture(scope="function")
async def async_client(app_with_test_db) -> AsyncClient:
    async with AsyncClient(app=app_with_test_db, base_url="http://test") as client:
        yield client


# Async session DB for test
@pytest.fixture(scope="function")
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


# fixture User Groups
@pytest.fixture(scope="function")
async def seed_user_groups(db_session: AsyncSession):
    groups = [{"name": group.value} for group in UserGroupEnum]
    await db_session.execute(insert(UserGroupModel).values(groups))
    await db_session.commit()
    yield db_session


# preparing test data
@pytest.fixture(scope="function")
async def seed_database(db_session: AsyncSession):
    settings = get_settings()
    seeder = CSVDatabaseSeeder(csv_file_path=settings.PATH_TO_MOVIES_CSV, db_session=db_session)
    if not await seeder.is_db_populated():
        await seeder.seed()
    yield db_session


# test user fixture
@pytest.fixture(scope="function")
async def create_test_user(db_session: AsyncSession):
    user = UserModel(email="testuser@example.com", group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# Мокові сервіси
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

