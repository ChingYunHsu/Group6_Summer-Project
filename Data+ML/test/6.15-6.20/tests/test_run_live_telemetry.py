"""Offline tests for run_live_telemetry CLI (SOP 5 runner, DB-4).

No DB required — covers the dry-run + mock-generation + default-mode-safety
paths. The --execute upsert path is exercised by live_capacity_telemetry's
own FakeCursor tests (test_live_capacity_telemetry.py).
"""

import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import run_live_telemetry as rlt  # noqa: E402


def _write_jsonl(path, rows):
    with open(path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def test_mock_generates_valid_payloads(tmp_path, capsys):
    out = tmp_path / "events.jsonl"
    rc = rlt.main(["--mock", "--out", str(out), "--dry-run"])
    assert rc == 2  # one intentionally-invalid payload (missing source_venue_id)

    rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    assert len(rows) == 3
    assert rows[0]["source_venue_id"] == "v_1001"
    assert "observed_at" in rows[0]
    assert 0 <= rows[0]["load_percent"] <= 100


def test_dry_run_normalizes_and_reports_without_db(tmp_path, capsys, monkeypatch):
    payload = {"source_name": "live_capacity", "source_venue_id": "v_1001",
               "observed_at": "2026-07-04T12:00:00", "load_percent": 72,
               "avg_wait_minutes": 14, "ttl_seconds": 300}
    p = tmp_path / "e.jsonl"
    _write_jsonl(p, [payload])

    def _fail():
        raise AssertionError("_connect must not be called in dry-run")
    monkeypatch.setattr(rlt, "_connect", _fail)

    rc = rlt.main(["--payloads", str(p), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "1 received, 1 normalized, 0 rejected" in out
    assert "0 rows written" in out
    assert "live-telemetry-v1" in out


def test_default_mode_is_dry_run_not_silent_write(tmp_path, capsys, monkeypatch):
    payload = {"source_name": "live_capacity", "source_venue_id": "v_1001",
               "observed_at": "2026-07-04T12:00:00", "load_percent": 30,
               "avg_wait_minutes": 3}
    p = tmp_path / "e.jsonl"
    _write_jsonl(p, [payload])

    def _fail():
        raise AssertionError("_connect must not be called in default mode")
    monkeypatch.setattr(rlt, "_connect", _fail)

    rc = rlt.main(["--payloads", str(p)])  # no --dry-run, no --execute
    assert rc == 0
    assert "0 rows written" in capsys.readouterr().out


def test_invalid_payload_is_rejected_not_crash(tmp_path, capsys, monkeypatch):
    # load_percent > 100 → TelemetryValidationError
    payload = {"source_venue_id": "v_1001", "observed_at": "2026-07-04T12:00:00",
               "load_percent": 150, "avg_wait_minutes": 5}
    p = tmp_path / "e.jsonl"
    _write_jsonl(p, [payload])
    monkeypatch.setattr(rlt, "_connect", lambda: (_ for _ in ()).throw(AssertionError()))
    rc = rlt.main(["--payloads", str(p), "--dry-run"])
    assert rc == 2  # rejected present
    assert "1 rejected" in capsys.readouterr().out


def test_missing_payloads_errors(tmp_path, capsys):
    rc = rlt.main([])
    assert rc == 1
    assert "--payloads" in capsys.readouterr().err


def test_empty_jsonl_errors(tmp_path, capsys):
    p = tmp_path / "empty.jsonl"
    p.write_text("\n\n")
    rc = rlt.main(["--payloads", str(p), "--dry-run"])
    assert rc == 1
