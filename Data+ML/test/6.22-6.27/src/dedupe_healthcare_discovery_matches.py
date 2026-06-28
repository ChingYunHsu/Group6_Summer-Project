"""Deduplicate healthcare discovery matches before Place API validation.

Outputs two files:
- place-level CSV: one row per serpapi_place_id, for minimum Place API calls
- venue-place mapping CSV: all venue_id mappings, preserving DB coverage rows
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_FILE = Path("../output/healthcare_uncovered_discovery_matches.csv")
DEFAULT_PLACE_FILE = Path("../output/healthcare_uncovered_discovery_places_dedup.csv")
DEFAULT_MAPPING_FILE = Path("../output/healthcare_uncovered_discovery_venue_place_map.csv")


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def dedupe_matches(
    input_file: Path,
    place_file: Path,
    mapping_file: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    matches = pd.read_csv(input_file)
    if "serpapi_place_id" not in matches.columns:
        raise ValueError(f"Missing serpapi_place_id in {input_file}")

    valid = matches[matches["serpapi_place_id"].notna()].copy()
    valid = valid.sort_values(
        ["serpapi_place_id", "distance_m", "name_similarity"],
        ascending=[True, True, False],
    )

    place_rows = valid.drop_duplicates(subset=["serpapi_place_id"], keep="first").copy()
    place_rows["mapped_venue_count"] = place_rows["serpapi_place_id"].map(
        valid.groupby("serpapi_place_id")["venue_id"].nunique()
    )
    place_rows["same_coordinate_venue_count"] = place_rows.groupby(
        ["latitude", "longitude"]
    )["venue_id"].transform("nunique")

    mapping_cols = [
        "venue_id",
        "venue_name",
        "district",
        "latitude",
        "longitude",
        "serpapi_place_id",
        "serpapi_data_id",
        "serpapi_name",
        "serpapi_type",
        "distance_m",
        "name_similarity",
        "search_category",
        "search_district",
        "search_page_start",
        "search_result_rank",
    ]
    mapping = valid[mapping_cols].copy()

    place_file.parent.mkdir(parents=True, exist_ok=True)
    place_rows.to_csv(place_file, index=False)
    mapping.to_csv(mapping_file, index=False)

    print(f"Input match rows: {len(matches)}")
    print(f"Valid place_id rows: {len(valid)}")
    print(f"Unique DB venues: {valid['venue_id'].nunique()}")
    print(f"Unique SerpAPI places: {valid['serpapi_place_id'].nunique()}")
    print(f"Duplicate place rows removed for Place API: {len(valid) - len(place_rows)}")
    print(f"Duplicate exact DB coordinate rows: {valid.duplicated(['latitude', 'longitude']).sum()}")
    print(f"Place-level output: {place_file}")
    print(f"Venue-place mapping output: {mapping_file}")
    return place_rows, mapping


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deduplicate healthcare discovery matches.")
    parser.add_argument("--input-file", default=str(DEFAULT_INPUT_FILE))
    parser.add_argument("--place-file", default=str(DEFAULT_PLACE_FILE))
    parser.add_argument("--mapping-file", default=str(DEFAULT_MAPPING_FILE))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dedupe_matches(
        input_file=resolve_path(args.input_file),
        place_file=resolve_path(args.place_file),
        mapping_file=resolve_path(args.mapping_file),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
