"""Write healthcare prediction group fields to `venues`. No API calls."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pymysql


GROUPED_VIEW_FILE = (
    Path(__file__).resolve().parent.parent / "output" / "venue_label_status_grouped_view.csv"
)


def write_healthcare_groups(live: bool = False) -> dict[str, int]:
    grouped = pd.read_csv(GROUPED_VIEW_FILE)
    healthcare = grouped[grouped["venue_type"] == "healthcare"][
        ["venue_id", "serpapi_place_id", "prediction_group_id", "prediction_shared"]
    ]
    print(f"Healthcare rows to update: {len(healthcare)}")

    if not live:
        print("Dry-run only. No database writes will be made.")
        return {"venues_updated": 0}

    rows = [
        (
            None if pd.isna(row.serpapi_place_id) else row.serpapi_place_id,
            None if pd.isna(row.prediction_group_id) else row.prediction_group_id,
            bool(row.prediction_shared),
            row.venue_id,
        )
        for row in healthcare.itertuples(index=False)
    ]

    conn = pymysql.connect(
        host=os.getenv("CLEARPATH_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("CLEARPATH_DB_PORT", "3306")),
        user=os.getenv("CLEARPATH_DB_USER", "clearpath_app"),
        password=os.getenv("CLEARPATH_DB_PASSWORD", "clearpath_app"),
        database=os.getenv("CLEARPATH_DB_NAME", "clearpath"),
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        with conn.cursor() as cursor:
            for column, ddl in (
                ("serpapi_place_id", "VARCHAR(36) NULL"),
                ("prediction_group_id", "VARCHAR(64) NULL"),
                ("prediction_shared", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ):
                cursor.execute(f"SHOW COLUMNS FROM venues LIKE '{column}'")
                if not cursor.fetchone():
                    cursor.execute(f"ALTER TABLE venues ADD COLUMN {column} {ddl}")
            cursor.executemany(
                """
                UPDATE venues
                SET serpapi_place_id = %s,
                    prediction_group_id = %s,
                    prediction_shared = %s
                WHERE venue_id = %s
                """,
                rows,
            )
        conn.commit()
    finally:
        conn.close()

    print(f"Writeback complete: {len(rows)} venues updated.")
    return {"venues_updated": len(rows)}


run_writeback = write_healthcare_groups


def main() -> int:
    write_healthcare_groups(live="--live" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
