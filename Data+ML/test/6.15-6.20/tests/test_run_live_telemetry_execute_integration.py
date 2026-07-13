"""Integration test: run_live_telemetry.py --execute against a real MySQL.

Closes O2 verification gap: every other telemetry test mocks the DB
(test_run_live_telemetry mocks _connect; test_live_capacity_telemetry uses
FakeCursor). This one proves the live path — --execute writes busyness_scores
(model_version='live-telemetry-v1') + a telemetry_audit_log row, and the realtime
read query (backend/src/api/realtime.py) returns the fresh rows.

Requires the compose MySQL (docker compose up -d mysql). Skipped by default; run with:
    pytest tests/test_run_live_telemetry_execute_integration.py -m integration -v

conftest.py puts src/ on sys.path, so run_live_telemetry imports directly.
"""

import json
import os
from datetime import datetime, timezone

import pytest

import run_live_telemetry as runner

pytestmark = pytest.mark.integration

# venue_source_links seed maps live_capacity v_1001 -> bryant-park, v_1002 -> bellevue.
SEED_VENUES = ("seed-restroom-bryant-park-001", "seed-healthcare-bellevue-001")
MODEL_VERSION = "live-telemetry-v1"

DB_CONFIG = {
    "host": os.environ.get("CLEARPATH_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("CLEARPATH_DB_PORT", "3306")),
    "user": os.environ.get("CLEARPATH_DB_USER", "clearpath_app"),
    "password": os.environ.get("CLEARPATH_DB_PASSWORD", "clearpath_app"),
    "database": os.environ.get("CLEARPATH_DB_NAME", "clearpath"),
    "charset": "utf8mb4",
}


@pytest.fixture()
def db():
    pymysql = pytest.importorskip("pymysql")
    try:
        conn = pymysql.connect(autocommit=True, **DB_CONFIG)
    except Exception as exc:  # DB not up — integration infra absent
        pytest.skip(f"compose MySQL unreachable ({exc}); run `docker compose up -d mysql`")
    # Ensure the runner's _connect() targets the same DB.
    for key, val in {
        "CLEARPATH_DB_HOST": DB_CONFIG["host"],
        "CLEARPATH_DB_PORT": str(DB_CONFIG["port"]),
        "CLEARPATH_DB_USER": DB_CONFIG["user"],
        "CLEARPATH_DB_PASSWORD": DB_CONFIG["password"],
        "CLEARPATH_DB_NAME": DB_CONFIG["database"],
    }.items():
        os.environ[key] = val
    yield conn
    conn.close()


def _scalar(conn, sql, args=None):
    with conn.cursor() as cur:
        cur.execute(sql, args or ())
        row = cur.fetchone()
        return row[0] if row else None


def _write_clean_payloads(path):
    """Two valid payloads for the two distinct seeded venues (v_1001->bryant-park,
    v_1002->bellevue) -> 2 busyness rows, 0 rejected, 0 unmatched."""
    now_min = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    payloads = [
        {"source_name": "live_capacity", "source_venue_id": "v_1001",
         "observed_at": now_min.isoformat(), "load_percent": 72,
         "avg_wait_minutes": 14, "ttl_seconds": 300},
        {"source_name": "live_capacity", "source_venue_id": "v_1002",
         "observed_at": now_min.isoformat(), "load_percent": 30,
         "avg_wait_minutes": 3, "ttl_seconds": 300},
    ]
    with open(path, "w") as fh:
        for p in payloads:
            fh.write(json.dumps(p) + "\n")


def test_dependency_tables_exist(db):
    count = _scalar(
        db,
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name IN "
        "('telemetry_audit_log', 'venue_source_links')",
        (DB_CONFIG["database"],),
    )
    assert count == 2, "O2 dependency tables (telemetry_audit_log, venue_source_links) must exist"


def test_execute_writes_busyness_audit_and_is_realtime_readable(db, tmp_path):
    payload_file = tmp_path / "telemetry_smoke.jsonl"
    _write_clean_payloads(str(payload_file))

    audit_before = _scalar(db, "SELECT COUNT(*) FROM telemetry_audit_log")

    rc = runner.main(["--payloads", str(payload_file), "--execute"])
    assert rc == 0, "clean batch should exit 0 (0 rejected, 0 unmatched)"

    # busyness_scores: 2 fresh live-telemetry rows across the two seeded venues.
    placeholders = ", ".join(["%s"] * len(SEED_VENUES))
    fresh_rows = _scalar(
        db,
        "SELECT COUNT(*) FROM busyness_scores "
        f"WHERE model_version = %s AND venue_id IN ({placeholders}) "
        "AND created_at >= (NOW() - INTERVAL 5 MINUTE)",
        (MODEL_VERSION, *SEED_VENUES),
    )
    assert fresh_rows >= 2, f"expected >=2 fresh busyness rows, got {fresh_rows}"

    # telemetry_audit_log: one new row, success/ingested/unmatched as expected.
    audit_after = _scalar(db, "SELECT COUNT(*) FROM telemetry_audit_log")
    assert audit_after == audit_before + 1, "one audit row must be appended per --execute run"
    with db.cursor() as cur:
        cur.execute(
            "SELECT success, ingested, unmatched FROM telemetry_audit_log "
            "ORDER BY audit_id DESC LIMIT 1"
        )
        success, ingested, unmatched = cur.fetchone()
    assert success == 1
    assert ingested == 2
    assert unmatched == 0

    # realtime read path (backend/src/api/realtime.py shape): model_version + freshness.
    realtime_rows = _scalar(
        db,
        "SELECT COUNT(*) FROM busyness_scores "
        "WHERE model_version = %s AND created_at >= (NOW() - INTERVAL 5 MINUTE)",
        (MODEL_VERSION,),
    )
    assert realtime_rows >= 2, "realtime endpoint read query must return the fresh live-telemetry rows"
