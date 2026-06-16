from pathlib import Path
import sys

import pytest

# Support both the new shared package and legacy direct-module imports.
TEST_ROOT = Path(__file__).resolve().parents[2]
SHARED_DIR = TEST_ROOT / 'shared'
DQR_DIR = TEST_ROOT / 'dqr'
sys.path.insert(0, str(TEST_ROOT))
sys.path.insert(0, str(SHARED_DIR))
sys.path.insert(0, str(DQR_DIR))


def pytest_collection_modifyitems(config, items):
    """Skip integration tests by default unless explicitly selected via -m."""
    keyword = config.getoption("-m", default="")
    # If the user explicitly asked for integration tests, don't skip
    if "integration" in keyword:
        return
    skip_integration = pytest.mark.skip(
        reason="integration test — run with '-m integration' to include"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
