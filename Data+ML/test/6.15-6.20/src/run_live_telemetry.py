#!/usr/bin/env python3
"""run_live_telemetry.py — CLI runner for live capacity telemetry ingestion.

Closes the SOP 5 / DB-4 ops gap: live_capacity_telemetry.py had
normalize/upsert/process_batch logic but no runnable entrypoint. This adds a
CLI that reads a JSONL file of telemetry payloads and upserts them into
`busyness_scores` (model_version='live-telemetry-v1').

The concrete telemetry *source* (BestTime / NYC proxy / partner feed) and
write frequency/freshness window are team decisions (DB-4). This runner is
source-agnostic: it consumes a normalized JSONL contract so any source
adapter can feed it. A `--mock` generator emits sample payloads for local
smoke-testing without an external API.

Usage:
  # Dry-run (default — never silently writes): normalize + resolve only
  python run_live_telemetry.py --payloads events.jsonl --dry-run

  # Real upsert (requires DB env vars)
  python run_live_telemetry.py --payloads events.jsonl --execute

  # Generate a small sample JSONL, then dry-run against it (no external API)
  python run_live_telemetry.py --mock --out mock_events.jsonl --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make the sibling live_capacity_telemetry importable when run directly.
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import live_capacity_telemetry as lct  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Live capacity telemetry ingestion runner (SOP 5 / DB-4).")
    p.add_argument("--payloads", help="JSONL file: one telemetry payload per line.")
    p.add_argument("--execute", action="store_true",
                   help="Resolve venue_id + upsert into busyness_scores (needs DB).")
    p.add_argument("--dry-run", action="store_true",
                   help="Normalize + report counts; do not write to DB (default).")
    p.add_argument("--mock", action="store_true",
                   help="Generate a small sample payloads JSONL (no external API).")
    p.add_argument("--out", default="mock_telemetry.jsonl",
                   help="Output path for --mock (default: mock_telemetry.jsonl).")
    p.add_argument("--ttl-seconds", type=int, default=lct.DEFAULT_TTL_SECONDS,
                   help="Freshness window in seconds (DB-4 freshness contract).")
    return p.parse_args(argv)


def load_payloads(path: str) -> list[dict]:
    payloads = []
    with open(path, newline="") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"WARN: line {lineno} not JSON: {exc}", file=sys.stderr)
    return payloads


def write_mock_payloads(path: str) -> list[dict]:
    """Emit deterministic sample payloads for local smoke-tests."""
    from datetime import datetime, timezone, timedelta
    base = datetime.now(timezone.utc).replace(microsecond=0)
    samples = [
        {"source_name": "live_capacity", "source_venue_id": "v_1001",
         "observed_at": base.isoformat(), "load_percent": 72, "avg_wait_minutes": 14,
         "ttl_seconds": 300},
        {"source_name": "live_capacity", "source_venue_id": "v_1002",
         "observed_at": (base - timedelta(minutes=1)).isoformat(),
         "load_percent": 30, "avg_wait_minutes": 3, "ttl_seconds": 300},
        # invalid: missing source_venue_id → rejected by normalize_event
        {"source_name": "live_capacity", "observed_at": base.isoformat(),
         "load_percent": 50, "avg_wait_minutes": 5},
    ]
    with open(path, "w") as fh:
        for s in samples:
            fh.write(json.dumps(s) + "\n")
    return samples


def _connect():
    import pymysql  # imported lazily so --dry-run/--mock need no DB deps
    return pymysql.connect(
        host=os.environ.get("CLEARPATH_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("CLEARPATH_DB_PORT", "3306")),
        user=os.environ.get("CLEARPATH_DB_USER", "clearpath_app"),
        password=os.environ.get("CLEARPATH_DB_PASSWORD", "clearpath_app"),
        database=os.environ.get("CLEARPATH_DB_NAME", "clearpath"),
        charset="utf8mb4",
        autocommit=False,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.dry_run and not args.execute:
        # SOP rollback control: default to dry-run, never silently write.
        args.dry_run = True

    if args.mock:
        samples = write_mock_payloads(args.out)
        print(f"--mock: wrote {len(samples)} sample payloads to {args.out}")
        if not args.payloads:
            args.payloads = args.out

    if not args.payloads:
        print("ERROR: --payloads (or --mock) is required.", file=sys.stderr)
        return 1

    payloads = load_payloads(args.payloads)
    if not payloads:
        print(f"ERROR: no payloads loaded from {args.payloads}", file=sys.stderr)
        return 1

    # Normalize first (validation is free of DB). Count rejects up front so
    # the dry-run path is meaningful without a connection.
    normalized = []
    rejected = 0
    for p in payloads:
        try:
            ev = lct.normalize_event(p)
            normalized.append(ev)
        except lct.TelemetryValidationError as exc:
            rejected += 1
            print(f"REJECT: {exc} — payload={json.dumps(p)[:120]}", file=sys.stderr)

    print(f"-- telemetry: {len(payloads)} received, {len(normalized)} normalized, {rejected} rejected")
    print(f"-- freshness window: ttl_seconds={args.ttl_seconds} (model_version={lct.MODEL_VERSION})")

    if args.dry_run:
        for ev in normalized:
            print(f"   OK source={ev.source_name} venue={ev.source_venue_id} "
                  f"load={ev.load_percent}% level={ev.level} wait={ev.avg_wait_minutes}min "
                  f"window=[{ev.forecast_start_time} → {ev.forecast_end_time}]")
        print(f"-- dry-run complete: 0 rows written. Re-run with --execute to upsert.")
        return 0 if rejected == 0 else 2

    # --execute path
    conn = _connect()
    ingested = unmatched = 0
    try:
        with conn.cursor() as cur:
            result = lct.process_batch(cur, payloads)
        conn.commit()
        ingested, unmatched = result.ingested, len(result.unmatched)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"-- execute: {ingested} upserted, {unmatched} unmatched, {rejected} rejected.")
    if unmatched:
        print("Unmatched (no venue_source_links row):", ", ".join(result.unmatched),
              file=sys.stderr)
    return 0 if unmatched == 0 and rejected == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
