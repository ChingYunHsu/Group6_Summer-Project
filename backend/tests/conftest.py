import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from app import create_app
from auth import SESSIONS
from mock_data import AUTH_USERS


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_sessions():
    SESSIONS.clear()
    original_users = list(AUTH_USERS)
    yield
    SESSIONS.clear()
    AUTH_USERS[:] = original_users


@pytest.fixture(autouse=True)
def clear_response_cache():
    """Flush cached responses (e.g. the forecast cache) so a real local
    Redis instance never lets one test's cached result leak into another
    test reusing the same cache key (venue_id, etc). Best-effort: if Redis
    isn't reachable, response_cache already fails open and there's nothing
    to clear."""
    import response_cache

    def _flush():
        try:
            client = response_cache._get_client()
            for key in client.scan_iter("forecast:v1:*"):
                client.delete(key)
        except Exception:
            pass

    _flush()
    yield
    _flush()
