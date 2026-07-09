"""write_forecasts_to_db.py — DB-3 forecast write contract.

Upserts ML prediction output (prediction_curve_v1.csv) into the
`busyness_forecasts` table, closing the SOP 3 forecast loop.

Write contract (frozen by DB-3):
  * unique key (venue_id, forecast_for, model_version) → idempotent upsert
    via INSERT ... ON DUPLICATE KEY UPDATE.
  * predicted_score bounded 0-100 (DB CHECK constraint enforces it).
  * predicted_level enum mirrors API: quiet/moderate/busy/no_data.
  * forecast_for = absolute future DATETIME, one row per future hour.
  * model_version derived from model_name (Ridge→ridge-v1,
    RandomForestRegressor→rf-v1, GradientBoostingRegressor→gbm-v1).

Source mapping:
  The CSV is keyed by Google Place ID (prediction_group_id, a ChIJ... value),
  NOT by the DB venues.venue_id (v_XXXX). At execute time the writer resolves
  each prediction_group_id → venues.venue_id via venue_source_links
  (source_name='google_places', source_record_id=<place_id>). In --dry-run
  mode no DB is needed: the raw place_id is shown so the mapping can be
  audited before any write.

Usage:
  # Audit only — no DB, prints upsert SQL + counts
  python write_forecasts_to_db.py --dry-run \
      --csv ../output/prediction_curve_v1.csv

  # Real write (requires DB env vars; resolves place_id → venue_id)
  python write_forecasts_to_db.py \
      --csv ../output/prediction_curve_v1.csv --model-version ridge-v1 \
      --execute
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta
from typing import Iterable

# model_name (CSV) -> model_version (busyness_forecasts.model_version)
MODEL_VERSION_MAP = {
    "Ridge": "ridge-v1",
    "RandomForestRegressor": "rf-v1",
    "GradientBoostingRegressor": "gbm-v1",
}

WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def next_occurrence(day_of_week: str, hour: int, now: datetime) -> datetime:
    """Return the next datetime matching (day_of_week, hour), strictly future.

    If today matches the weekday but the hour has already passed today, roll
    forward to next week so every emitted forecast_for is in the future
    (the backend query filters forecast_for >= NOW()).
    """
    target_wd = WEEKDAY_INDEX[day_of_week.lower()]
    days_ahead = (target_wd - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def forecast_datetimes(day_of_week: str, hours: Iterable[int], now: datetime) -> list[datetime]:
    """One forecast_for per hour, sorted ascending."""
    return sorted(next_occurrence(day_of_week, h, now) for h in hours)


def clamp_score(value: float) -> int:
    """Round + clamp to [0, 100]; the DB CHECK rejects > 100."""
    return max(0, min(100, round(float(value))))


def upsert_sql(venue_id: str, forecast_for: datetime, score: int, level: str,
               wait_minutes, model_version: str) -> str:
    """Parameter-free SQL string for --dry-run auditing.

    In --execute mode the parameterized form is used instead (see _upsert_row).
    """
    wait = "NULL" if wait_minutes in (None, "") else str(int(wait_minutes))
    return (
        "INSERT INTO busyness_forecasts "
        "(venue_id, forecast_for, predicted_score, predicted_level, "
        "estimated_wait_minutes, model_version) VALUES "
        f"('{venue_id}', '{forecast_for.strftime('%Y-%m-%d %H:%M:%S')}', "
        f"{score}, '{level}', {wait}, '{model_version}') "
        "ON DUPLICATE KEY UPDATE "
        "predicted_score = VALUES(predicted_score), "
        "predicted_level = VALUES(predicted_level), "
        "estimated_wait_minutes = VALUES(estimated_wait_minutes);"
    )


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


def load_rows(csv_path: str, model_version: str | None) -> list[dict]:
    """Read CSV, filter to the chosen model_version (or all if None)."""
    target = None
    if model_version is not None:
        # accept either CSV model_name or mapped model_version
        target = {v: k for k, v in MODEL_VERSION_MAP.items()}.get(model_version, model_version)

    out = []
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            if target is not None and row["model_name"] != target:
                continue
            mv = MODEL_VERSION_MAP.get(row["model_name"], row["model_name"].lower() + "-v1")
            out.append({
                "place_id": row["prediction_group_id"],
                "day_of_week": row["day_of_week"],
                "hour": int(row["hour"]),
                "predicted_score": clamp_score(row["predicted_score"]),
                "predicted_level": row["predicted_level"],
                "model_version": mv,
            })
    return out


def resolve_place_id(cur, place_id: str) -> str | None:
    """Map Google Place ID -> venues.venue_id via venue_source_links."""
    cur.execute(
        "SELECT vsl.venue_id FROM venue_source_links vsl "
        "WHERE vsl.source_name = 'google_places' AND vsl.source_record_id = %s "
        "LIMIT 1",
        (place_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return row[0] if isinstance(row, (tuple, list)) else row.get("venue_id")


def _connect():
    """Lazy DB connection for --execute mode only."""
    import pymysql  # imported here so --dry-run needs no DB deps
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
    parser = argparse.ArgumentParser(description="Upsert ML forecasts into busyness_forecasts (DB-3).")
    parser.add_argument("--csv", required=True, help="prediction_curve_v1.csv path")
    parser.add_argument("--model-version", default="ridge-v1",
                        help="model_version to write (ridge-v1|rf-v1|gbm-v1); default ridge-v1")
    parser.add_argument("--dry-run", action="store_true",
                        help="print upsert SQL + counts; do not touch the DB")
    parser.add_argument("--execute", action="store_true",
                        help="resolve place_id→venue_id and upsert into the DB")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.execute:
        # SOP 3 rollback control: default to dry-run, never silently write.
        args.dry_run = True

    rows = load_rows(args.csv, args.model_version)
    if not rows:
        print(f"No CSV rows matched model_version={args.model_version!r}; nothing to write.",
              file=sys.stderr)
        return 1

    now = datetime.now()
    # group by (place_id, model_version) so each venue+model is one 12h series
    by_key: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_key.setdefault((r["place_id"], r["model_version"]), []).append(r)

    total = 0
    unmatched: list[str] = []

    if args.dry_run:
        print(f"-- DB-3 dry-run: model_version={args.model_version}, "
              f"{len(rows)} rows, {len(by_key)} (venue,model) groups --")
        for (place_id, mv), group in sorted(by_key.items()):
            dts = forecast_datetimes(group[0]["day_of_week"],
                                     [g["hour"] for g in group], now)
            print(f"\n-- place_id={place_id}  model_version={mv}  "
                  f"({len(dts)} forecast rows)")
            for r, dt in zip(sorted(group, key=lambda g: g["hour"]), dts):
                print(upsert_sql(f"<venue_id for {place_id}>", dt,
                                 r["predicted_score"], r["predicted_level"],
                                 None, mv))
                total += 1
        print(f"\n-- dry-run complete: {total} upsert statements emitted "
              f"(0 written to DB). Re-run with --execute to write.")
        return 0

    # --execute path
    conn = _connect()
    written = 0
    try:
        with conn.cursor() as cur:
            for (place_id, mv), group in by_key.items():
                venue_id = resolve_place_id(cur, place_id)
                if not venue_id:
                    unmatched.append(place_id)
                    continue
                dts = forecast_datetimes(group[0]["day_of_week"],
                                         [g["hour"] for g in group], now)
                for r, dt in zip(sorted(group, key=lambda g: g["hour"]), dts):
                    cur.execute(_UPSERT_STMT, (
                        venue_id, dt, r["predicted_score"],
                        r["predicted_level"], None, mv,
                    ))
                    written += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"DB-3 upsert: {written} rows written, {len(unmatched)} unmatched place_ids.")
    if unmatched:
        print("Unmatched (no venue_sourcelinks row, source_name='google_places'):",
              ", ".join(unmatched), file=sys.stderr)
    return 0 if not unmatched else 2


if __name__ == "__main__":
    raise SystemExit(main())
