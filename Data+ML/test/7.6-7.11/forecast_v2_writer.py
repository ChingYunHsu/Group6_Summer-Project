"""forecast_v2_writer.py — Upsert prediction_curve_v2.csv into busyness_forecasts table.

Reuses the write_forecasts_to_db.py pattern but adapted for forecast-v2:
  - Uses venue_id directly (no place_id → venue_id resolution needed)
  - Parametrizes --model-version forecast-v2
  - Each row has venue_id, forecast_for, offset_hours, predicted_score, predicted_level

Usage:
  python forecast_v2_writer.py --dry-run --csv output/prediction_curve_v2.csv
  python forecast_v2_writer.py --execute --csv output/prediction_curve_v2.csv
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import db_utils
from score_utils import clamp_score, score_to_level

HERE = Path(__file__).resolve().parent


def derive_forecast_for(
    base_time: datetime,
    offset_hours: int,
) -> datetime:
    """Convert forecast_for + offset_hours → absolute forecast DATETIME."""
    return base_time + timedelta(hours=int(offset_hours))


def load_curve(csv_path: Path, model_version: str = "forecast-v2") -> list[dict[str, Any]]:
    """Read prediction_curve_v2.csv, return list of rows ready for upsert."""
    df = pd.read_csv(csv_path)
    if "model_version" in df.columns:
        df = df[df["model_version"] == model_version]

    rows = []
    for _, r in df.iterrows():
        base_time = pd.Timestamp(r["forecast_for"]).to_pydatetime()
        forecast_for = derive_forecast_for(base_time, r["offset_hours"])
        score = clamp_score(r["predicted_score"])
        level = r.get("predicted_level", score_to_level(score))
        rows.append({
            "venue_id": r["venue_id"],
            "forecast_for": forecast_for,
            "predicted_score": score,
            "predicted_level": level,
            "model_version": model_version,
        })
    return rows


_UPSERT_STMT = (
    "INSERT INTO busyness_forecasts "
    "(venue_id, forecast_for, predicted_score, predicted_level, "
    "estimated_wait_minutes, model_version) VALUES "
    "(%s, %s, %s, %s, %s, %s) "
    "ON DUPLICATE KEY UPDATE "
    "predicted_score = VALUES(predicted_score), "
    "predicted_level = VALUES(predicted_level), "
    "estimated_wait_minutes = VALUES(estimated_wait_minutes)"
)


def dry_run_sql(
    venue_id: str, forecast_for: datetime, score: int, level: str, model_version: str,
) -> str:
    return (
        "INSERT INTO busyness_forecasts "
        "(venue_id, forecast_for, predicted_score, predicted_level, "
        "estimated_wait_minutes, model_version) VALUES "
        f"('{venue_id}', '{forecast_for.strftime('%Y-%m-%d %H:%M:%S')}', "
        f"{score}, '{level}', NULL, '{model_version}') "
        "ON DUPLICATE KEY UPDATE "
        "predicted_score = VALUES(predicted_score), "
        "predicted_level = VALUES(predicted_level), "
        "estimated_wait_minutes = VALUES(estimated_wait_minutes);"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upsert forecast-v2 predictions into busyness_forecasts")
    p.add_argument("--csv", required=True, help="prediction_curve_v2.csv path")
    p.add_argument("--model-version", default="forecast-v2")
    p.add_argument("--dry-run", action="store_true", help="Print SQL only, no DB write")
    p.add_argument("--execute", action="store_true", help="Write to DB")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.dry_run and not args.execute:
        args.dry_run = True  # safe default

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 1

    rows = load_curve(csv_path, args.model_version)
    if not rows:
        print(f"No rows matched model_version={args.model_version!r}", file=sys.stderr)
        return 1

    n_venues = len(set(r["venue_id"] for r in rows))
    print(f"Loaded {len(rows)} forecast rows for {n_venues} venues "
          f"(model_version={args.model_version})")

    if args.dry_run:
        print(f"\n-- DRY RUN: {len(rows)} upserts would be emitted --")
        for r in rows[:5]:
            print(dry_run_sql(r["venue_id"], r["forecast_for"],
                              r["predicted_score"], r["predicted_level"],
                              r["model_version"]))
        if len(rows) > 5:
            print(f"... and {len(rows) - 5} more")
        print(f"\n-- dry-run complete: 0 written to DB. Re-run with --execute to write.")
        return 0

    # --execute
    conn = db_utils.get_conn()
    inserted, updated = 0, 0
    failed_venues: list[str] = []
    try:
        with conn.cursor() as cur:
            for r in rows:
                try:
                    cur.execute(_UPSERT_STMT, (
                        r["venue_id"], r["forecast_for"],
                        r["predicted_score"], r["predicted_level"],
                        None, r["model_version"],
                    ))
                    if cur.rowcount == 1:
                        inserted += 1
                    elif cur.rowcount == 2:
                        updated += 1
                    else:
                        inserted += 1
                except Exception as e:
                    failed_venues.append(f"{r['venue_id']}: {e}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"\nDB write complete:")
    print(f"  inserted: {inserted}")
    print(f"  updated: {updated}")
    print(f"  failed venue mappings: {len(failed_venues)}")
    if failed_venues:
        for f in failed_venues[:10]:
            print(f"    {f}")

    return 0 if not failed_venues else 2


if __name__ == "__main__":
    raise SystemExit(main())
