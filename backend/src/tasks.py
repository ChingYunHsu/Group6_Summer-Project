"""Background lifecycle tasks for crowdsourced reports.

expire_stale_reports runs on a Celery beat schedule (see celery_app.py) and
mutates any report untouched for 2+ hours to "expired" — but only if it
never picked up an upvote/confirmation, since a confirmed report's
latest_action_at keeps getting refreshed by api/reports.py on every
confirmation.
"""

from celery_app import celery_app
from db import db_transaction

STALE_REPORT_HOURS = 2


@celery_app.task(name="tasks.expire_stale_reports")
def expire_stale_reports() -> int:
    """Mark active, unconfirmed reports older than STALE_REPORT_HOURS as
    expired. Returns the number of rows updated."""
    with db_transaction() as cursor:
        cursor.execute(
            "UPDATE user_reports "
            "SET status = 'expired' "
            "WHERE status = 'active' "
            "  AND confirmation_count = 0 "
            "  AND upvote_count = 0 "
            "  AND latest_action_at <= NOW() - INTERVAL %s HOUR",
            (STALE_REPORT_HOURS,),
        )
        return cursor.rowcount
