"""conftest.py — pytest configuration for Sprint 4 (7.13-7.18) Data tests.

Adds the canonical Sprint 4 directory before src/. forecast-v2 is maintained
there; src/ remains available for the other frozen Sprint 4 modules.
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if SRC not in sys.path:
    sys.path.append(SRC)


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
