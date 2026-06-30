"""Build offline prediction groups from existing SerpAPI place IDs.

This script does not call any API. It folds healthcare venues into shared
prediction groups using already-saved serpapi_place_id values.

Outputs:
- venue_label_status_grouped_view.csv: coverage view with group columns added
- healthcare_prediction_groups.csv: one row per prediction group
- healthcare_prediction_group_members.csv: one row per healthcare venue
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_FILE = Path("../output/venue_label_status_coverage_view.csv")
DEFAULT_GROUP_VIEW_FILE = Path("../output/venue_label_status_grouped_view.csv")
DEFAULT_GROUPS_FILE = Path("../output/healthcare_prediction_groups.csv")
DEFAULT_MEMBERS_FILE = Path("../output/healthcare_prediction_group_members.csv")


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def build_group_id(row: pd.Series) -> str:
    place_id = row.get("serpapi_place_id")
    if pd.notna(place_id) and str(place_id).strip():
        return str(place_id)
    return f"venue::{row['venue_id']}"


def build_prediction_groups(
    input_file: Path,
    group_view_file: Path,
    groups_file: Path,
    members_file: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = pd.read_csv(input_file)
    healthcare = labels[labels["venue_type"] == "healthcare"].copy()

    healthcare["prediction_group_id"] = healthcare.apply(build_group_id, axis=1)
    healthcare["prediction_shared"] = healthcare["prediction_group_id"].duplicated(keep=False)

    group_stats = (
        healthcare
        .groupby("prediction_group_id")
        .agg(
            group_member_count=("venue_id", "count"),
            unique_place_id=("serpapi_place_id", "nunique"),
            has_popular_times=("label_status", lambda s: int((s == "has_popular_times").any())),
            any_validation=("label_status", lambda s: int(s.isin(["has_popular_times", "no_popular_times", "search_matched_unvalidated"]).any())),
            venue_types=("venue_type", lambda s: ", ".join(sorted(set(s)))),
            districts=("district", lambda s: ", ".join(sorted(set(s)))),
        )
        .reset_index()
    )

    primary_rows = (
        healthcare
        .sort_values(["prediction_group_id", "prediction_shared", "name"])
        .drop_duplicates("prediction_group_id", keep="first")
        .copy()
    )
    primary_rows = primary_rows[[
        "prediction_group_id",
        "venue_id",
        "name",
        "district",
        "venue_type",
        "serpapi_place_id",
        "label_status",
        "prediction_shared",
    ]].rename(columns={
        "venue_id": "primary_venue_id",
        "name": "primary_venue_name",
        "district": "primary_district",
        "venue_type": "primary_venue_type",
        "serpapi_place_id": "source_place_id",
        "label_status": "primary_label_status",
    })

    groups = group_stats.merge(primary_rows, on="prediction_group_id", how="left")
    groups["group_type"] = groups["source_place_id"].notna().map({True: "shared_place", False: "fallback_singleton"})
    groups["prediction_source"] = groups["source_place_id"].notna().map({True: "serpapi_place_id", False: "venue_id_fallback"})

    members = healthcare[[
        "venue_id",
        "venue_type",
        "district",
        "name",
        "latitude",
        "longitude",
        "label_status",
        "serpapi_place_id",
        "prediction_group_id",
        "prediction_shared",
    ]].copy()
    members = members.merge(
        groups[["prediction_group_id", "group_member_count", "group_type", "prediction_source"]],
        on="prediction_group_id",
        how="left",
    )

    labels = labels.merge(
        healthcare[["venue_id", "prediction_group_id", "prediction_shared"]].drop_duplicates("venue_id"),
        on="venue_id",
        how="left",
    )

    labels["prediction_group_id"] = labels["prediction_group_id"].where(labels["venue_type"] == "healthcare", pd.NA)
    labels["prediction_shared"] = labels["prediction_shared"].where(labels["venue_type"] == "healthcare", False)
    labels["prediction_shared"] = labels["prediction_shared"].infer_objects(copy=False).fillna(False).astype(bool)
    labels["group_match_source"] = labels["serpapi_place_id"].where(labels["venue_type"] == "healthcare", pd.NA)
    labels["group_match_source"] = labels["group_match_source"].fillna("")
    labels["group_match_source"] = labels["group_match_source"].where(labels["group_match_source"].astype(str).str.len() > 0, "none")

    labels["group_member_count"] = labels["prediction_group_id"].map(
        groups.set_index("prediction_group_id")["group_member_count"]
    )
    labels["group_member_count"] = labels["group_member_count"].fillna(0).astype(int)

    group_view_file.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(group_view_file, index=False)
    groups.to_csv(groups_file, index=False)
    members.to_csv(members_file, index=False)

    print(f"Input labels: {len(labels)}")
    print(f"Healthcare rows: {len(healthcare)}")
    print(f"Shared groups: {int(groups['prediction_shared'].sum())}")
    print(f"Unique prediction groups: {len(groups)}")
    print(f"Groups with serpapi_place_id: {int(groups['source_place_id'].notna().sum())}")
    print(f"Fallback singleton groups: {int(groups['source_place_id'].isna().sum())}")
    print(f"Grouped view: {group_view_file}")
    print(f"Groups table: {groups_file}")
    print(f"Members table: {members_file}")
    return labels, groups, members


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build offline healthcare prediction groups.")
    parser.add_argument("--input-file", default=str(DEFAULT_INPUT_FILE))
    parser.add_argument("--group-view-file", default=str(DEFAULT_GROUP_VIEW_FILE))
    parser.add_argument("--groups-file", default=str(DEFAULT_GROUPS_FILE))
    parser.add_argument("--members-file", default=str(DEFAULT_MEMBERS_FILE))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    build_prediction_groups(
        input_file=resolve_path(args.input_file),
        group_view_file=resolve_path(args.group_view_file),
        groups_file=resolve_path(args.groups_file),
        members_file=resolve_path(args.members_file),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
