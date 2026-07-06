"""Celery application wiring the background report-expiry lifecycle onto the
Redis broker already used for the JWT blacklist (see token_blacklist.py).

Run the worker + beat scheduler with:
    poetry run celery -A celery_app worker --beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab

from settings import get_settings

_settings = get_settings()

celery_app = Celery(
    "clearpath",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["tasks"],
)

celery_app.conf.beat_schedule = {
    "expire-stale-reports-every-5-minutes": {
        "task": "tasks.expire_stale_reports",
        "schedule": crontab(minute="*/5"),
    },
}
celery_app.conf.timezone = "UTC"
