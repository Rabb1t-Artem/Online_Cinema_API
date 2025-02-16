from sqlalchemy.future import select
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timezone
from database.models.accounts import ActivationTokenModel
from database import get_db

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

celery_app = Celery("accounts", broker=CELERY_BROKER_URL)
celery_app.conf.result_backend = CELERY_RESULT_BACKEND
celery_app.conf.timezone = "UTC"


@celery_app.task
async def delete_expired_tokens():
    """
    Task to delete expired activation tokens.
    """
    async with get_db() as session:
        result = await session.execute(
            select(ActivationTokenModel).where(ActivationTokenModel.expires_at < datetime.now(timezone.utc))
        )
        expired_tokens = result.scalars().all()

        for token in expired_tokens:
            await session.delete(token)

        await session.commit()


celery_app.conf.beat_schedule = {
    "delete-expired-tokens-every-day": {
        "task": "celery.delete_expired_tokens",
        "schedule": crontab(hour="0", minute="0"),
    },
}
