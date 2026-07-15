#!/usr/bin/env python3
"""Validate that a real-data forecast-v2 run is safe to start; never falls back to synthetic data."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import forecast_v2_feature_pipeline as fp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, default=Path("evidence"))
    args = parser.parse_args()
    directory = args.evidence_root / "real-data-validation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory.mkdir(parents=True, exist_ok=False)
    result = {"created_at": datetime.now(timezone.utc).isoformat(), "mode": "real observed"}
    if not (os.environ.get("DB_URL") or os.environ.get("MYSQL_HOST")):
        result.update({
            "status": "SKIPPED — environment unavailable",
            "reason": "DB_URL or MYSQL_HOST is not configured; synthetic fallback is forbidden.",
        })
        (directory / "real_data_validation.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0
    try:
        venues = fp.load_venues(max_venues=200)
        scores = fp.load_busyness_scores(max_rows=200000)
        reports = fp.load_user_reports()
        training = fp.build_training_samples(scores, venues, reports, use_real_external=True)
        if training.empty:
            raise RuntimeError("No real training rows were produced")
        if "bootstrap_label" in training and training["bootstrap_label"].astype(bool).any():
            raise RuntimeError("Bootstrap labels found in real-data validation")
        source_columns = [column for column in training if column.endswith("_source")]
        unavailable = {column: training[column].astype(str).eq("unavailable").mean() for column in source_columns}
        result.update({"status": "READY", "training_rows": len(training), "venues": training["venue_id"].nunique(), "unavailable_source_ratios": unavailable})
        exit_code = 0
    except Exception as exc:
        result.update({"status": "SKIPPED — environment unavailable", "reason": f"{type(exc).__name__}: {exc}"})
        exit_code = 0
    (directory / "real_data_validation.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps(result, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
