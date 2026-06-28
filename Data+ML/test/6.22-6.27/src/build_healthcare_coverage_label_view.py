"""Build a notebook-ready label view with supplemental healthcare coverage.

The baseline venue_label_status.csv is kept unchanged. This script creates a
derived view that includes:
- DB-driven batch results with Place API status
- discovery-first matches as search_matched_unvalidated
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


DEFAULT_BASE_LABEL_FILE = Path("../output/venue_label_status.csv")
DEFAULT_BATCH_FILE = Path("../output/healthcare_uncovered_batch_results.csv")
DEFAULT_DISCOVERY_MAP_FILE = Path("../output/healthcare_uncovered_discovery_venue_place_map.csv")
DEFAULT_RESTROOM_AUDIT_FILE = Path("../output/restroom_popular_times_audit.csv")
DEFAULT_OUTPUT_FILE = Path("../output/venue_label_status_coverage_view.csv")


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def apply_batch_results(labels: pd.DataFrame, batch_file: Path) -> pd.DataFrame:
    if not batch_file.exists():
        return labels
    batch = pd.read_csv(batch_file)
    matched = batch[batch["matched"] == True].drop_duplicates("venue_id", keep="last")
    by_id = matched.set_index("venue_id")
    update_mask = labels["venue_id"].isin(by_id.index)

    for index, row in labels[update_mask].iterrows():
        result = by_id.loc[row["venue_id"]]
        has_popular_times = bool(result.get("has_popular_times", False))
        labels.at[index, "label_status"] = result.get("label_status")
        labels.at[index, "ml_eligible"] = has_popular_times
        labels.at[index, "prediction_source"] = "ml_model" if has_popular_times else "rule_fallback"
        labels.at[index, "display_level"] = "quiet" if has_popular_times else "no_data"
        labels.at[index, "serpapi_checked_at"] = result.get("checked_at")
        labels.at[index, "serpapi_place_id"] = result.get("serpapi_place_id")
        labels.at[index, "review_count"] = result.get("reviews")
        labels.at[index, "rating"] = result.get("rating")
        labels.at[index, "notes"] = "Synced from healthcare_uncovered_batch_results.csv"
    return labels


def apply_discovery_matches(labels: pd.DataFrame, discovery_map_file: Path) -> pd.DataFrame:
    if not discovery_map_file.exists():
        return labels
    discovery = pd.read_csv(discovery_map_file)
    discovery = discovery.drop_duplicates("venue_id", keep="last")
    by_id = discovery.set_index("venue_id")
    update_mask = (
        labels["venue_id"].isin(by_id.index)
        & labels["label_status"].isin(["api_not_checked", "search_not_matched"])
    )

    for index, row in labels[update_mask].iterrows():
        result = by_id.loc[row["venue_id"]]
        labels.at[index, "label_status"] = "search_matched_unvalidated"
        labels.at[index, "ml_eligible"] = False
        labels.at[index, "prediction_source"] = "pending_place_validation"
        labels.at[index, "display_level"] = "no_data"
        labels.at[index, "serpapi_checked_at"] = pd.NA
        labels.at[index, "serpapi_place_id"] = result.get("serpapi_place_id")
        labels.at[index, "review_count"] = result.get("reviews", pd.NA)
        labels.at[index, "rating"] = result.get("rating", pd.NA)
        labels.at[index, "notes"] = "Matched by discovery; Place API not checked"
    return labels


def rename_unmatched_healthcare(labels: pd.DataFrame) -> pd.DataFrame:
    """Use a precise status for healthcare rows not matched by Search discovery."""
    mask = (
        labels["venue_type"].eq("healthcare")
        & labels["label_status"].eq("api_not_checked")
    )
    labels.loc[mask, "label_status"] = "search_not_matched"
    labels.loc[mask, "notes"] = "Not matched in current SerpAPI Search discovery results"
    return labels


def apply_restroom_audit(labels: pd.DataFrame, restroom_audit_file: Path) -> pd.DataFrame:
    """Merge restroom Popular Times audit rows into the coverage view."""
    if not restroom_audit_file.exists():
        return labels

    audit = pd.read_csv(restroom_audit_file)
    if "venue_id" not in audit.columns:
        raise ValueError(f"Missing venue_id in {restroom_audit_file}")

    checked = audit[audit["place_checked"] == True].drop_duplicates("venue_id", keep="last")
    by_id = checked.set_index("venue_id")
    update_mask = labels["venue_id"].isin(by_id.index) & labels["venue_type"].eq("restroom")

    for index, row in labels[update_mask].iterrows():
        result = by_id.loc[row["venue_id"]]
        has_popular_times = bool(result.get("has_popular_times", False))
        labels.at[index, "label_status"] = "has_popular_times" if has_popular_times else "no_popular_times"
        labels.at[index, "ml_eligible"] = has_popular_times
        labels.at[index, "prediction_source"] = "ml_model" if has_popular_times else "rule_fallback"
        labels.at[index, "display_level"] = "quiet" if has_popular_times else "no_data"
        labels.at[index, "serpapi_checked_at"] = result.get("checked_at", pd.NA)
        labels.at[index, "serpapi_place_id"] = result.get("serpapi_place_id")
        labels.at[index, "review_count"] = result.get("reviews", pd.NA)
        labels.at[index, "rating"] = result.get("rating", pd.NA)
        labels.at[index, "notes"] = "Synced from restroom_popular_times_audit.csv"
    return labels


def build_label_view(
    base_label_file: Path,
    batch_file: Path,
    discovery_map_file: Path,
    restroom_audit_file: Path,
    output_file: Path,
) -> pd.DataFrame:
    labels = pd.read_csv(output_file if output_file.exists() else base_label_file)
    labels = apply_batch_results(labels, batch_file)
    labels = apply_discovery_matches(labels, discovery_map_file)
    labels = rename_unmatched_healthcare(labels)
    labels = apply_restroom_audit(labels, restroom_audit_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(output_file, index=False)

    healthcare = labels[labels["venue_type"] == "healthcare"]
    print(f"Base labels: {base_label_file}")
    print(f"Output view: {output_file}")
    print("\nHealthcare label_status in coverage view:")
    print(healthcare["label_status"].value_counts().to_string())
    return labels


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build notebook coverage label view.")
    parser.add_argument("--base-label-file", default=str(DEFAULT_BASE_LABEL_FILE))
    parser.add_argument("--batch-file", default=str(DEFAULT_BATCH_FILE))
    parser.add_argument("--discovery-map-file", default=str(DEFAULT_DISCOVERY_MAP_FILE))
    parser.add_argument("--restroom-audit-file", default=str(DEFAULT_RESTROOM_AUDIT_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    build_label_view(
        base_label_file=resolve_path(args.base_label_file),
        batch_file=resolve_path(args.batch_file),
        discovery_map_file=resolve_path(args.discovery_map_file),
        restroom_audit_file=resolve_path(args.restroom_audit_file),
        output_file=resolve_path(args.output_file),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
