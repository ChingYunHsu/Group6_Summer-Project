
"""Backfill `venues.rating` from SerpAPI place results.

Default mode is dry-run. Live DB writes require `--live`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from healthcare_common import resolve_path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DB_ROOT = PROJECT_ROOT / "Data+ML/test/6.2-6.5_DB"
if str(DB_ROOT) not in sys.path:
    sys.path.insert(0, str(DB_ROOT))

from clearpath_db.db import etl_executemany, get_conn


DEFAULT_SOURCE_FILE = Path("../output/phase_b_place_results.csv")
DEFAULT_LABEL_FILE = Path("../output/venue_label_status_coverage_view.csv")


def normalize_place_id(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()


def load_source_frames(source_file: Path, label_file: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    place = pd.read_csv(source_file, usecols=["serpapi_place_id", "rating"])
    place["rating"] = pd.to_numeric(place["rating"], errors="coerce")
    place = place[place["rating"].notna()].drop_duplicates("serpapi_place_id", keep="last").copy()
    place["serpapi_place_id"] = normalize_place_id(place["serpapi_place_id"])

    labels = pd.read_csv(label_file, usecols=["venue_id", "venue_type", "serpapi_place_id", "rating"])
    labels = labels[labels["venue_type"].eq("healthcare")].copy()
    labels["rating"] = pd.to_numeric(labels["rating"], errors="coerce")
    labels.loc[labels["serpapi_place_id"].notna(), "serpapi_place_id"] = normalize_place_id(
        labels.loc[labels["serpapi_place_id"].notna(), "serpapi_place_id"]
    )
    return place, labels


def load_rating_updates(place: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    label_updates = labels[labels["rating"].notna()][["venue_id", "rating"]]
    place_updates = labels[labels["serpapi_place_id"].notna()].merge(
        place, on="serpapi_place_id", how="inner", suffixes=("_label", "")
    )[["venue_id", "rating"]]
    updates = pd.concat([label_updates, place_updates], ignore_index=True)
    return updates.drop_duplicates("venue_id", keep="last")


def write_ratings(updates: pd.DataFrame, live: bool) -> int:
    if updates.empty:
        print("No rating rows to backfill.")
        return 0
    if not live:
        print("Dry-run only. No database writes will be made.")
        print(updates.head(20).to_string(index=False))
        return 0

    conn = get_conn()
    try:
        updated, _ = etl_executemany(
            conn,
            "UPDATE venues SET rating = %s WHERE venue_id = %s",
            [(float(row.rating), row.venue_id) for row in updates.itertuples(index=False)],
            source="venues_rating_backfill",
            record_id="phase_b_place_results",
        )
    finally:
        conn.close()

    print(f"Write complete: {updated} venues updated.")
    return updated


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill venues.rating from SerpAPI place results.")
    parser.add_argument("--source-file", default=str(DEFAULT_SOURCE_FILE))
    parser.add_argument("--label-file", default=str(DEFAULT_LABEL_FILE))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--live", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    source_file = resolve_path(args.source_file)
    label_file = resolve_path(args.label_file)
    place, healthcare = load_source_frames(source_file, label_file)
    updates = load_rating_updates(place, healthcare)

    print(f"Source file: {source_file}")
    print(f"Label file: {label_file}")
    print(f"Rated place rows: {len(place)}")
    print(f"Healthcare rows: {healthcare['venue_id'].nunique()}")
    print(f"Healthcare rows with label rating: {healthcare['rating'].notna().sum()}")
    print(f"Healthcare rows with serpapi_place_id: {healthcare['serpapi_place_id'].notna().sum()}")
    print(f"Venue rows to update: {len(updates)}")

    if args.dry_run or not args.live:
        write_ratings(updates, live=False)
        return 0

    write_ratings(updates, live=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
