"""Keep the repeatable report-category seed aligned with the frozen 9-item contract."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SEED_SQL = REPO_ROOT / "docker/mysql/init/006_seed_report_categories.sql"
OPS_SCRIPT = REPO_ROOT / "docker/mysql/scripts/ensure_report_categories.sh"
EXPECTED_IDS = {
    "elevator_broken",
    "wheelchair_lift_broken",
    "toilet_out_of_order",
    "large_crowd",
    "long_waiting_time",
    "protest_or_blockage",
    "entrance_closed",
    "ramp_blocked",
    "closed_early",
}


def test_seed_is_the_frozen_nine_category_contract():
    source = SEED_SQL.read_text()
    category_ids = set(re.findall(r"^\s*\('([a-z_]+)',\s*'[^']+'", source, re.MULTILINE))
    assert category_ids == EXPECTED_IDS
    assert "ON DUPLICATE KEY UPDATE" in source


def test_ops_entrypoint_applies_and_then_verifies_the_same_seed():
    source = OPS_SCRIPT.read_text()
    assert "006_seed_report_categories.sql" in source
    assert 'MODE="${1:---verify}"' in source
    assert '"--apply"' in source
    assert "expected 9 active report categories" in source
