#!/usr/bin/env python3
"""Run canonical forecast-v2 evidence without overwriting legacy output files."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(command: list[str], cwd: Path, log: Path, allowed: set[int] = {0}) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    with log.open("a", encoding="utf-8") as handle:
        handle.write("$ " + " ".join(command) + "\n")
        handle.write(result.stdout)
        handle.write(result.stderr)
        handle.write(f"[exit={result.returncode}]\n\n")
    if result.returncode not in allowed:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}")
    return result.stdout + result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description="Create append-only forecast-v2 evidence.")
    parser.add_argument("--mode", choices=("offline", "real"), default="offline")
    parser.add_argument("--evidence-root", type=Path, default=HERE / "evidence")
    parser.add_argument("--venues", type=int, default=30)
    parser.add_argument("--hours-back", type=int, default=168)
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.evidence_root / args.mode / stamp
    output.mkdir(parents=True, exist_ok=False)
    log = output / "run.log"

    feature_command = [sys.executable, "forecast_v2_feature_pipeline.py", "--output-dir", str(output)]
    if args.mode == "real":
        feature_command.extend(["--live-db", "--n-synth-venues", str(args.venues)])
    else:
        feature_command.extend(["--dry-run", "--n-synth-venues", str(args.venues), "--synth-hours-back", str(args.hours_back)])
    _run(feature_command, HERE, log)
    _run([
        sys.executable, "forecast_v2_model.py", "--features", str(output / "forecast_v2_training_features.csv"),
        "--pred-features", str(output / "forecast_v2_prediction_features.csv"), "--output-dir", str(output),
    ], HERE, log)
    quality_report = _run(
        [sys.executable, "forecast_v2_quality_gate.py", "--output-dir", str(output)], HERE, log, {0, 2}
    )
    (output / "forecast_v2_quality_gate_report.txt").write_text(quality_report, encoding="utf-8")
    _run([
        sys.executable, "forecast_v2_writer.py", "--dry-run", "--csv", str(output / "prediction_curve_v2.csv"),
        "--model-version", "forecast-v2",
    ], HERE, log)
    _run([
        sys.executable, "generate_v2_report_visuals.py", "--evidence-dir", str(output),
        "--data-mode", "synthetic bootstrap" if args.mode == "offline" else "real observed",
    ], HERE, log)

    training = pd.read_csv(output / "forecast_v2_training_features.csv")
    curve = pd.read_csv(output / "prediction_curve_v2.csv")
    metrics = pd.read_csv(output / "forecast_v2_model_metrics.csv")
    test_metrics = metrics[metrics["split"] == "test"]
    best = test_metrics.loc[test_metrics["mae"].idxmin()].to_dict()
    provenance = "synthetic bootstrap" if args.mode == "offline" else "real observed"
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=HERE.parents[2], text=True, capture_output=True
    ).stdout.strip() or "unavailable"
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "label_provenance": provenance,
        "model_version": "forecast-v2",
        "git_commit": git_commit,
        "commands_log": "run.log",
        "training_rows": int(len(training)),
        "training_venues": int(training["venue_id"].nunique()),
        "prediction_rows": int(len(curve)),
        "prediction_venues": int(curve["venue_id"].nunique()),
        "bootstrap_label_ratio": float(training.get("bootstrap_label", pd.Series([args.mode == "offline"] * len(training))).astype(bool).mean()),
        "best_test_model": best,
        "inputs": {
            name: _sha256(output / name)
            for name in ("forecast_v2_training_features.csv", "forecast_v2_prediction_features.csv")
        },
        "quality_gate": "forecast_v2_quality_gate_report.txt",
        "limitations": [
            "Offline mode uses synthetic bootstrap labels and is not real foot-traffic validation.",
            "Report heatmap is venue-by-time unless geographic coordinates are supplied separately.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
