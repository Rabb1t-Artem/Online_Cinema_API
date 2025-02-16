import os
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from fastapi import Depends, HTTPException, status

# from fastapi.security import OAuth2PasswordBearer

from config.settings import TestingSettings, Settings, BaseAppSettings
from notifications import EmailSenderInterface, EmailSender
from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager
from storages import S3StorageInterface, S3StorageClient
from security.http import get_token
from sqlalchemy.orm import joinedload, selectinload


# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")


def get_settings() -> BaseAppSettings:
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()


def get_jwt_auth_manager(
    settings: BaseAppSettings = Depends(get_settings),
) -> JWTAuthManagerInterface:
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )


def get_accounts_email_notificator(
    settings: BaseAppSettings = Depends(get_settings),
) -> EmailSenderInterface:
    return EmailSender(
        hostname=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        email=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        template_dir=settings.PATH_TO_EMAIL_TEMPLATES_DIR,
        activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_email_template_name=settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME,
        password_email_template_name=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_complete_email_template_name=settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME,
    )


def get_s3_storage_client(
    settings: BaseAppSettings = Depends(get_settings),
) -> S3StorageInterface:
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME,
    )


async def get_current_user(token: str = Depends(get_token), settings: Settings = Depends(get_settings)):
    from database import get_db
    from database.models.accounts import UserModel

    db: AsyncSession = await anext(get_db())
    try:
        payload = JWTAuthManager(
            secret_key_access=settings.SECRET_KEY_ACCESS,
            secret_key_refresh=settings.SECRET_KEY_REFRESH,
            algorithm=settings.JWT_SIGNING_ALGORITHM,
        ).decode_access_token(token)

        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

        result = await db.execute(select(UserModel).options(selectinload(UserModel.group)).filter(UserModel.id == user_id))
        user = result.scalars().first()

        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return user

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate token: {str(e)}")
