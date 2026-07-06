"""conftest.py — pytest configuration for Sprint 4 (7.6-7.11) Data tests.

Adds the sibling src/ to sys.path so all test files can import from the
Sprint 4 src modules. Also configures integration test skipping.
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def pytest_collection_modifyitems(config, items):
    """Skip @pytest.mark.integration tests unless `-m integration` is given."""
    keyword = config.getoption("-m", default="") or ""
    if "integration" in keyword:
        return
    skip_integration = pytest.mark.skip(
        reason="integration test — run with '-m integration' to include"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
