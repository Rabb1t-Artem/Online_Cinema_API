import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Завантаження змінних середовища з .env файлу
load_dotenv()


# Базові налаштування додатку
class BaseAppSettings(BaseModel):
    # Використовуємо Field із default_factory, щоб BASE_DIR визначався динамічно
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent)

    # Шляхи до файлів та бази даних
    PATH_TO_DB: str = Field(
        default_factory=lambda: str(Path(__file__).parent.parent / "database" / "source" / "theater.db")
    )
    PATH_TO_MOVIES_CSV: str = Field(
        default_factory=lambda: str(Path(__file__).parent.parent / "database" / "seed_data" / "imdb_movies.csv")
    )

    # Шлях до шаблонів електронної пошти та назви шаблонів
    PATH_TO_EMAIL_TEMPLATES_DIR: str = Field(
        default_factory=lambda: str(Path(__file__).parent.parent / "notifications" / "templates")
    )
    ACTIVATION_EMAIL_TEMPLATE_NAME: str = "activation_request.html"
    ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME: str = "activation_complete.html"
    PASSWORD_RESET_TEMPLATE_NAME: str = "password_reset_request.html"
    PASSWORD_RESET_COMPLETE_TEMPLATE_NAME: str = "password_reset_complete.html"

    LOGIN_TIME_DAYS: int = 7

    # Налаштування електронної пошти
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "host")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "25"))
    EMAIL_HOST_USER: str = os.getenv("EMAIL_HOST_USER", "testuser")
    EMAIL_HOST_PASSWORD: str = os.getenv("EMAIL_HOST_PASSWORD", "test_password")
    EMAIL_USE_TLS: bool = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
    MAILHOG_API_PORT: int = int(os.getenv("MAILHOG_API_PORT", "8025"))

    # Налаштування S3/MinIO
    S3_STORAGE_HOST: str = os.getenv("MINIO_HOST", "minio-theater")
    S3_STORAGE_PORT: int = int(os.getenv("MINIO_PORT", "9000"))
    S3_STORAGE_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    S3_STORAGE_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "some_password")
    S3_BUCKET_NAME: str = os.getenv("MINIO_STORAGE", "theater-storage")

    # STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY")
    # STRIPE_PUBLIC_KEY: str = os.getenv("STRIPE_PUBLIC_KEY")

    @property
    def S3_STORAGE_ENDPOINT(self) -> str:
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"


# Налаштування для продакшн-режиму або локальної роботи з PostgreSQL
class Settings(BaseAppSettings):
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "test_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "test_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "test_host")
    POSTGRES_DB_PORT: int = int(os.getenv("POSTGRES_DB_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "test_db")

    # Генеруємо секретні ключі; оскільки os.urandom повертає байти, перетворюємо їх у hex-рядок
    SECRET_KEY_ACCESS: str = os.getenv("SECRET_KEY_ACCESS", os.urandom(32).hex())
    SECRET_KEY_REFRESH: str = os.getenv("SECRET_KEY_REFRESH", os.urandom(32).hex())
    JWT_SIGNING_ALGORITHM: str = os.getenv("JWT_SIGNING_ALGORITHM", "HS256")


# Налаштування для тестування
class TestingSettings(BaseAppSettings):
    SECRET_KEY_ACCESS: str = "TEST_SECRET_KEY_ACCESS"
    SECRET_KEY_REFRESH: str = "TEST_SECRET_KEY_REFRESH"
    JWT_SIGNING_ALGORITHM: str = "HS256"

    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

    def model_post_init(self, __context: dict[str, Any] | None = None) -> None:
        # Після ініціалізації замінюємо шлях до бази даних на тестову базу
        object.__setattr__(self, "PATH_TO_DB", self.TEST_DATABASE_URL)


# Приклад створення екземпляру налаштувань
if __name__ == "__main__":
    settings = Settings()
    print("S3 endpoint:", settings.S3_STORAGE_ENDPOINT)
    print("Path to DB:", settings.PATH_TO_DB)
