"""Unit test for the Celery beat task that expires stale, unconfirmed
reports, with MySQL faked out so this runs without a live database or
Redis broker."""

from contextlib import contextmanager

import tasks as tasks_module


class _FakeCursor:
    rowcount = 3

    def execute(self, query, params=()):
        query = " ".join(query.split())
        assert query.startswith("UPDATE user_reports SET status = 'expired'")
        assert "confirmation_count = 0" in query
        assert "upvote_count = 0" in query
        assert params == (tasks_module.STALE_REPORT_HOURS,)


def test_expire_stale_reports_runs_expected_update(monkeypatch):
    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor()

    monkeypatch.setattr(tasks_module, "db_transaction", fake_db_transaction)

    result = tasks_module.expire_stale_reports()

    assert result == 3
