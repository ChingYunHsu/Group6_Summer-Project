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
