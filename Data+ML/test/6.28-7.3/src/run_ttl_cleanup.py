#!/usr/bin/env python3
"""run_ttl_cleanup.py — TTL expiration worker (SOP 2 / BE-4 / D3.6).

Calls cleanup_expired_reports() to soft-expire active reports whose TTL has
elapsed. Designed to run via cron or a simple while-true loop with sleep.

Deployment modes:
  1. Cron (recommended): run every 2 minutes
     */2 * * * * cd /path/to/project && python Data+ML/test/6.28-7.3/src/run_ttl_cleanup.py --execute
  2. Loop mode: long-running process with configurable interval
     python run_ttl_cleanup.py --execute --loop --interval 120
  3. Dry-run: audit without mutating
     python run_ttl_cleanup.py --dry-run

Monitoring:
  - --execute prints "ttl_cleanup: expired N rows" to stdout
  - Exit code 0 on success, 1 on DB unavailable, 2 on partial failure
  - Cron mode: pipe stdout to a log file for audit trail
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone


def _connect():
    import pymysql
    return pymysql.connect(
        host=os.environ.get("CLEARPATH_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("CLEARPATH_DB_PORT", "3306")),
        user=os.environ.get("CLEARPATH_DB_USER", "clearpath_app"),
        password=os.environ.get("CLEARPATH_DB_PASSWORD", "clearpath_app"),
        database=os.environ.get("CLEARPATH_DB_NAME", "clearpath"),
        charset="utf8mb4",
        autocommit=False,
    )


def cleanup_expired_reports(cur) -> int:
    """Soft-expire active reports whose expires_at <= NOW().

    Idempotent: guarded by status='active' so resolved/expired rows are
    never overwritten. Returns the number of rows expired.
    """
    cur.execute(
        "UPDATE user_reports SET status = 'expired' "
        "WHERE status = 'active' AND expires_at <= NOW()"
    )
    return cur.rowcount


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="TTL cleanup worker — expires stale user_reports (D3.6)."
    )
    p.add_argument("--execute", action="store_true",
                   help="Connect to DB and expire stale rows.")
    p.add_argument("--dry-run", action="store_true",
                   help="Audit only: print what would happen without mutating.")
    p.add_argument("--loop", action="store_true",
                   help="Run continuously (for process-supervisor mode).")
    p.add_argument("--interval", type=int, default=120,
                   help="Sleep seconds between iterations in --loop mode (default: 120).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.dry_run and not args.execute:
        args.dry_run = True

    if args.loop and args.dry_run:
        print("ERROR: --loop requires --execute.", file=sys.stderr)
        return 1

    # --dry-run: count without mutating
    if args.dry_run:
        try:
            conn = _connect()
        except Exception as exc:
            print(f"ttl_cleanup: DB unavailable — {exc}", file=sys.stderr)
            return 1
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM user_reports "
                    "WHERE status = 'active' AND expires_at <= NOW()"
                )
                row = cur.fetchone()
                count = row[0] if isinstance(row, (tuple, list)) else list(row.values())[0]
            now_iso = datetime.now(timezone.utc).isoformat()
            print(f"ttl_cleanup dry-run [{now_iso}]: {count} rows would be expired.")
        finally:
            conn.close()
        return 0

    # --execute (once or loop)
    def _run_once() -> int:
        try:
            conn = _connect()
        except Exception as exc:
            print(f"ttl_cleanup: DB unavailable — {exc}", file=sys.stderr)
            return 1
        try:
            with conn.cursor() as cur:
                n = cleanup_expired_reports(cur)
            conn.commit()
            now_iso = datetime.now(timezone.utc).isoformat()
            if n:
                print(f"ttl_cleanup [{now_iso}]: expired {n} rows.")
            return 0
        except Exception as exc:
            conn.rollback()
            print(f"ttl_cleanup [{datetime.now(timezone.utc).isoformat()}]: ERROR — {exc}",
                  file=sys.stderr)
            return 2
        finally:
            conn.close()

    if not args.loop:
        return _run_once()

    print(f"ttl_cleanup: starting loop (interval={args.interval}s). Ctrl+C to stop.")
    try:
        while True:
            rc = _run_once()
            if rc == 1:
                print("ttl_cleanup: waiting for DB...", file=sys.stderr)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nttl_cleanup: stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
