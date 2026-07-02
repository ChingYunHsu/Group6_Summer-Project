"""Write healthcare prediction group metadata to `venues`. No API calls.

Default mode is dry-run. Live DB writes require `--live`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pymysql


GROUPED_VIEW_FILE = (
    Path(__file__).resolve().parent.parent / "output" / "venue_label_status_grouped_view.csv"
)

REQUIRED_COLUMNS = [
    "venue_id",
    "venue_type",
    "label_status",
    "ml_eligible",
    "serpapi_checked_at",
    "serpapi_place_id",
    "prediction_group_id",
    "prediction_shared",
]


def load_healthcare_group_rows(grouped_view_file: Path = GROUPED_VIEW_FILE) -> pd.DataFrame:
    """Load and validate grouped healthcare rows for DB writeback."""
    grouped = pd.read_csv(grouped_view_file)
    missing = [column for column in REQUIRED_COLUMNS if column not in grouped.columns]
    if missing:
        raise ValueError(
            "Grouped view is missing required DB writeback columns: "
            + ", ".join(missing)
            + f". Rebuild it first with {Path(__file__).with_name('build_healthcare_prediction_groups.py')}"
        )

    return grouped[grouped["venue_type"] == "healthcare"][
        [
            "venue_id",
            "label_status",
            "ml_eligible",
            "serpapi_checked_at",
            "serpapi_place_id",
            "prediction_group_id",
            "prediction_shared",
        ]
    ].copy()


def print_writeback_summary(healthcare: pd.DataFrame) -> None:
    print(f"Healthcare rows to update: {len(healthcare)}")
    print(f"Rows with serpapi_place_id: {int(healthcare['serpapi_place_id'].notna().sum())}")
    print(f"Rows with prediction_group_id: {int(healthcare['prediction_group_id'].notna().sum())}")
    print(f"Rows with shared prediction group: {int(healthcare['prediction_shared'].fillna(False).astype(bool).sum())}")
    print("label_status distribution:")
    print(healthcare["label_status"].value_counts(dropna=False).to_string())


def write_healthcare_groups(live: bool = False) -> dict[str, int]:
    healthcare = load_healthcare_group_rows()
    print_writeback_summary(healthcare)

    if not live:
        print("Dry-run only. No database writes will be made.")
        return {"venues_updated": 0}

    rows = [
        (
            None if pd.isna(row.label_status) else row.label_status,
            str(row.label_status) == "has_popular_times",
            bool(row.ml_eligible),
            None if pd.isna(row.serpapi_checked_at) else row.serpapi_checked_at,
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
                ("serpapi_label_status", "VARCHAR(32) NULL"),
                ("has_popular_times", "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("ml_eligible", "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("serpapi_checked_at", "VARCHAR(32) NULL"),
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
                SET serpapi_label_status = %s,
                    has_popular_times = %s,
                    ml_eligible = %s,
                    serpapi_checked_at = %s,
                    serpapi_place_id = %s,
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
