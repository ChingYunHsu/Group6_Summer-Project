from pathlib import Path
import sys

import pytest

# Support both the new shared package and legacy direct-module imports.
TEST_ROOT = Path(__file__).resolve().parents[1]  # 6.15-5.20/
SRC_DIR = TEST_ROOT / 'src'
# Legacy dqr modules live in the old 6.8-6.12_DB directory
LEGACY_DB = TEST_ROOT.parent / '6.8-6.12_DB'
SHARED_DIR = LEGACY_DB / 'shared'
DQR_DIR = LEGACY_DB / 'dqr'
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(LEGACY_DB))
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
