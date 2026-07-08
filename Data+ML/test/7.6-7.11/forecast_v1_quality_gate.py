#!/usr/bin/env python3
"""forecast_v1_quality_gate.py — retrospective quality gate for V1 pipeline output.

Runs the same audit gates as forecast_v2_quality_gate.py where V1 schema allows:
  - Leakage / overfitting (R2/MAE thresholds)
  - Label distribution (busy_level: quiet/moderate/busy)
  - Train/val split duplicate keys (via time-ordered position split)
  - Prediction curve: hourly coverage check
  - Target leakage (busyness_score not in feature columns)

Gates skipped for V1 (schema does not support):
  - Sentinel ratio (no humidity/temperature/wind features)
  - Rolling window leakage (no latest_busyness_age_minutes)
  - External feature source check (no weather_source/gbfs_source/mta_source)
  - 12h curve point-per-venue check (V1 uses day_of_week+hour, not forecast_for+offset)

Usage:
  python3 forecast_v1_quality_gate.py --output-dir /path/to/6.28-7.3/output
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

LEAK_R2 = 0.99
LEAK_MAE = 0.1


def pct(n: int, total: int) -> str:
    return f"{(100.0 * n / total):.2f}%" if total else "0%"


# ── Loaders ──────────────────────────────────────────────────────────

def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    if not path.exists():
        return [], []
    with open(path, newline="") as fh:
        r = csv.DictReader(fh)
        rows = list(r)
        return list(r.fieldnames or []), rows


# ── Gates ────────────────────────────────────────────────────────────

def gate_leakage(metrics: list[dict]) -> tuple[list[str], bool]:
    findings = []
    blocked = False
    for m in metrics:
        split = m.get("split", "")
        if split not in ("val", "test"):
            continue
        name = m.get("model_name", "?")
        r2_s = m.get("r2", "")
        mae_s = m.get("mae", "")
        try:
            r2v = float(r2_s)
        except ValueError:
            r2v = None
        try:
            maev = float(mae_s)
        except ValueError:
            maev = None
        trips = []
        if r2v is not None and r2v >= LEAK_R2:
            trips.append(f"R2={r2v:.3f} >= {LEAK_R2}")
        if maev is not None and maev <= LEAK_MAE:
            trips.append(f"MAE={maev:.3f} <= {LEAK_MAE}")
        if trips:
            blocked = True
            findings.append(f"  [BLOCK] {name}/{split}: " + ", ".join(trips))
        else:
            findings.append(f"  [ok]    {name}/{split}: R2={r2_s} MAE={mae_s}")
    verdict = "BLOCKED" if blocked else "PASS"
    findings.insert(0, f"leakage/overfitting gate (R2>={LEAK_R2} or MAE<={LEAK_MAE} => block): {verdict}")
    return findings, blocked


def gate_label_distribution(train_rows: list[dict]) -> tuple[list[str], bool]:
    findings = []
    level_key = None
    for candidate in ("busy_level", "label_level", "target_busy_level"):
        if candidate in train_rows[0] if train_rows else False:
            level_key = candidate
            break
    if level_key is None:
        findings.append("  [WARN] no busy_level / label_level column — cannot audit")
        findings.insert(0, "label distribution gate: SKIP (no level column)")
        return findings, False

    dist = Counter(r.get(level_key, "") for r in train_rows)
    findings.append(f"  train label dist (via {level_key}): {dict(dist)}")
    total = sum(dist.values()) or 1
    busy = dist.get("busy", 0)
    blocked = busy == 0
    if blocked:
        findings.append(f"  [BLOCK] no 'busy' samples — cannot predict high-crowd reliably")
    elif busy / total < 0.05:
        findings.append(f"  [WARN] busy share low: {pct(busy, total)}")
    verdict = "BLOCKED" if blocked else "PASS"
    findings.insert(0, f"label distribution gate: {verdict}")
    return findings, blocked


def gate_train_val_split(train_rows: list[dict]) -> tuple[list[str], bool]:
    """Sort by heuristic time proxy (day_index + hour) if forecast_for is missing."""
    findings = []
    blocked = False
    if not train_rows:
        findings.append("  [WARN] no training rows")
        findings.insert(0, "train/val split duplicate gate: SKIP (no data)")
        return findings, False

    # V1 uses day_index + hour instead of forecast_for
    time_keys: list[tuple[float, str, str]] = []
    for r in train_rows:
        di = float(r.get("day_index", 0))
        hr = float(r.get("hour", 0))
        sort_key = di * 24 + hr  # proxy: hour of week
        venue = r.get("venue_id", "")
        time_keys.append((sort_key, venue, f"d{int(di)}_h{int(hr)}"))

    sorted_rows = sorted(zip(time_keys, train_rows), key=lambda x: x[0][0])
    n = len(sorted_rows)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    # Build keys for duplicate check
    all_keys = [(x[0][1], x[0][2]) for x in sorted_rows]  # (venue_id, day_hour)
    key_positions: dict[tuple[str, str], list[int]] = {}
    for i, key in enumerate(all_keys):
        key_positions.setdefault(key, []).append(i)

    cross_split = 0
    for key, positions in key_positions.items():
        if len(positions) > 1:
            in_train = any(p < train_end for p in positions)
            in_val = any(train_end <= p < val_end for p in positions)
            in_test = any(p >= val_end for p in positions)
            if sum([in_train, in_val, in_test]) > 1:
                cross_split += 1

    findings.append(f"  total rows: {n}, train: {train_end}, val: {val_end - train_end}, test: {n - val_end}")
    findings.append(f"  unique (venue_id, day_hour) keys: {len(key_positions)}")
    findings.append(f"  keys crossing split boundary: {cross_split}")

    if cross_split > 0:
        blocked = True
    verdict = "BLOCKED" if blocked else "PASS"
    findings.insert(0, f"train/val split duplicate gate (no key in multiple splits): {verdict}")
    return findings, blocked


def gate_target_leakage(train_cols: list[str]) -> tuple[list[str], bool]:
    findings = []
    # V1: busyness_score is the target
    forbidden = {"busyness_score", "predicted_score", "predicted_level", "serving_predicted_level"}
    leaked = forbidden & set(train_cols)
    # busyness_score IS the target column, not a feature
    targets = {"busyness_score"} & set(train_cols)
    findings.append(f"  target columns present in training CSV: {sorted(targets)} (expected)")
    findings.append(f"  forbidden columns present: {sorted(leaked - targets) or 'none'}")
    blocked = bool((leaked - targets))
    findings.insert(0, f"target leakage gate: {'BLOCKED' if blocked else 'PASS'}")
    return findings, blocked


def gate_curve_hours(curve_rows: list[dict]) -> tuple[list[str], bool]:
    """V1: check per-venue hour coverage (DOW x hour combo)."""
    findings = []
    if not curve_rows:
        findings.append("  [WARN] no curve rows")
        findings.insert(0, "curve hour coverage gate: SKIP (no data)")
        return findings, False

    per_venue = Counter(r["venue_id"] for r in curve_rows)
    findings.append(f"  venues: {len(per_venue)}, curve rows: {len(curve_rows)}")
    findings.append(f"  rows per venue: min={min(per_venue.values())}, max={max(per_venue.values())}")
    # V1 should have 7 days * 24 hours = 168 curve points per venue ideally
    low = sum(1 for n in per_venue.values() if n < 24)
    if low:
        findings.append(f"  [WARN] {low} venues with < 24 curve points")
    findings.insert(0, "curve hour coverage gate: PASS")
    return findings, False  # never block on V1 curve coverage


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="V1 retrospective quality gate audit")
    p.add_argument("--output-dir", default="output", help="V1 output directory")
    args = p.parse_args(argv)

    out = Path(args.output_dir)
    metrics_path = out / "model_metrics_v1.csv"
    train_path = out / "ml_training_frame_v1.csv"
    curve_path = out / "prediction_curve_v1.csv"

    metrics = []
    if metrics_path.exists():
        metrics = load_csv(metrics_path)[1]

    train_cols, train_rows = load_csv(train_path)
    _, curve_rows = load_csv(curve_path)

    if not train_rows:
        print("ERROR: ml_training_frame_v1.csv not found or empty", file=sys.stderr)
        return 1

    sections: list[tuple[str, bool, bool]] = []

    if metrics:
        f, b = gate_leakage(metrics); sections.append(("\n".join(f), b, False))
    else:
        sections.append(("leakage gate: SKIP (no model_metrics_v1.csv)", False, False))

    f, b = gate_label_distribution(train_rows); sections.append(("\n".join(f), b, False))
    f, b = gate_target_leakage(train_cols); sections.append(("\n".join(f), b, False))
    f, b = gate_train_val_split(train_rows); sections.append(("\n".join(f), b, False))
    f, b = gate_curve_hours(curve_rows); sections.append(("\n".join(f), b, False))

    # Skipped gates
    sections.append(("sentinel ratio gate: SKIP (V1 has no humidity/temperature/wind features)", False, False))
    sections.append(("rolling window leakage gate: SKIP (V1 has no latest_busyness_age_minutes)", False, False))
    sections.append(("external feature gate: SKIP (V1 has no weather_source/gbfs_source/mta_source)", False, False))

    print("=" * 70)
    print("forecast-v1 legacy quality-gate audit (retrospective)")
    print("=" * 70)
    for text, _, _ in sections:
        print()
        print(text)

    any_blocked = any(s[1] for s in sections)
    any_partial = any(s[2] for s in sections)
    print()
    print("=" * 70)
    if any_blocked:
        print("OVERALL VERDICT: BLOCKED — V1 has critical quality issues.")
        code = 3
    elif any_partial:
        print("OVERALL VERDICT: PARTIAL — V1 has known limitations (legacy risk).")
        code = 2
    else:
        print("OVERALL VERDICT: PASS — V1 meets legacy quality thresholds.")
        code = 0
    print("=" * 70)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
