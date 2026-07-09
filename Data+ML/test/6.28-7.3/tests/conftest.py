"""pytest config for the 6.28-7.3 ML test directory.

Adds the sibling src/ to sys.path so `import ml_modeling` / `import
ml_feature_pipeline` resolve when running plain pytest from anywhere.
Integration tests (live BestTime / Google / DB) are skipped by default —
run with `-m integration` to include them.
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
