"""Sync uncovered healthcare batch results into a label status CSV.

This script does not overwrite the original label file by default. It creates
venue_label_status_synced.csv so the original baseline remains auditable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


DEFAULT_LABEL_FILE = Path("../output/venue_label_status.csv")
DEFAULT_BATCH_FILE = Path("../output/healthcare_uncovered_batch_results.csv")
DEFAULT_OUTPUT_FILE = Path("../output/venue_label_status_synced.csv")


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


def sync_batch_results(
    label_file: Path,
    batch_file: Path,
    output_file: Path,
) -> pd.DataFrame:
    labels = pd.read_csv(label_file)
    if not batch_file.exists():
        raise FileNotFoundError(f"Batch result file not found: {batch_file}")

    batch = pd.read_csv(batch_file)
    if "venue_id" not in batch.columns:
        raise ValueError(f"Missing venue_id in {batch_file}")

    matched = batch[batch["matched"] == True].copy()
    matched = matched.drop_duplicates(subset=["venue_id"], keep="last")
    matched_by_id = matched.set_index("venue_id")

    synced = labels.copy()
    update_mask = synced["venue_id"].isin(matched_by_id.index)

    for index, row in synced[update_mask].iterrows():
        result = matched_by_id.loc[row["venue_id"]]
        label_status = result.get("label_status", "no_popular_times")
        has_popular_times = bool(result.get("has_popular_times", False))

        synced.at[index, "label_status"] = label_status
        synced.at[index, "ml_eligible"] = has_popular_times
        synced.at[index, "prediction_source"] = "ml_model" if has_popular_times else "rule_fallback"
        synced.at[index, "display_level"] = "quiet" if has_popular_times else "no_data"
        synced.at[index, "serpapi_checked_at"] = result.get("checked_at")
        synced.at[index, "serpapi_place_id"] = result.get("serpapi_place_id")
        synced.at[index, "review_count"] = result.get("reviews")
        synced.at[index, "rating"] = result.get("rating")
        synced.at[index, "notes"] = "Synced from healthcare_uncovered_batch_results.csv"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    synced.to_csv(output_file, index=False)

    healthcare = synced[synced["venue_type"] == "healthcare"]
    print(f"Input labels: {len(labels)}")
    print(f"Batch rows: {len(batch)}")
    print(f"Batch matched rows synced: {len(matched)}")
    print(f"Output: {output_file}")
    print("\nHealthcare label_status after sync:")
    print(healthcare["label_status"].value_counts().to_string())
    return synced


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync healthcare uncovered batch results.")
    parser.add_argument("--label-file", default=str(DEFAULT_LABEL_FILE))
    parser.add_argument("--batch-file", default=str(DEFAULT_BATCH_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    sync_batch_results(
        label_file=resolve_path(args.label_file),
        batch_file=resolve_path(args.batch_file),
        output_file=resolve_path(args.output_file),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
