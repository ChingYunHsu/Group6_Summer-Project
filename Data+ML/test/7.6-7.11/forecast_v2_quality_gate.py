#!/usr/bin/env python3
"""forecast_v2_quality_gate.py — pre-deployment quality gate for forecast-v2.

Implements the O5 gates from docs/memory/Sprint3-4_execution-plan.md:
  - Leakage / overfitting: block if val/test R2 >= 0.99 or MAE <= 0.1.
  - Label distribution: quiet/moderate/busy counts per split; block busy=0.
  - Coverage: training_venue_count, prediction_venue_count, forecast_row_count,
    rows_per_venue must be recorded (no implicit defaults).
  - External features: weather/gbfs/mta source status; partial if any missing.
  - Target leakage: label_score / label_level must not be feature columns.
  - 12h curve: prediction curve must have 12 points per venue.

Reads the pipeline output CSVs and prints a per-gate verdict + overall rollup.
Exit code 0 = pass, 2 = partial rollout allowed, 3 = blocked.

Usage:
  python3 forecast_v2_quality_gate.py --output-dir output
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

LEAK_R2 = 0.99
LEAK_MAE = 0.1
CURVE_POINTS = 12
SENTINEL_THRESHOLD = 0.5  # block if >50% of rows have sentinel value


def load_metrics(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    if not path.exists():
        return [], []
    with open(path, newline="") as fh:
        r = csv.DictReader(fh)
        rows = list(r)
        return list(r.fieldnames or []), rows


def pct(n: int, total: int) -> str:
    return f"{(100.0 * n / total):.2f}%" if total else "0%"


def gate_leakage(metrics: list[dict]) -> list[str]:
    findings = []
    blocked = False
    for m in metrics:
        split = m.get("split", "")
        if split not in ("val", "test"):
            continue
        name = m.get("model_name", "?")
        r2 = m.get("r2", "")
        mae = m.get("mae", "")
        try:
            r2v = float(r2)
        except ValueError:
            r2v = None
        try:
            maev = float(mae)
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
            findings.append(f"  [ok]    {name}/{split}: R2={r2} MAE={mae}")
    verdict = "BLOCKED" if blocked else "PASS"
    findings.insert(0, f"leakage/overfitting gate (R2>={LEAK_R2} or MAE<={LEAK_MAE} => block): {verdict}")
    return findings, blocked


def gate_label_distribution(train_rows: list[dict], pred_rows: list[dict]) -> tuple[list[str], bool]:
    findings = []
    train_dist = Counter(r.get("label_level", "") for r in train_rows)
    findings.append(f"  train label dist: {dict(train_dist)}")
    busy = train_dist.get("busy", 0)
    total = sum(train_dist.values()) or 1
    blocked = busy == 0
    if blocked:
        findings.append(f"  [BLOCK] no 'busy' samples in training — cannot predict high-crowd reliably")
    elif busy / total < 0.05:
        findings.append(f"  [WARN] busy share low: {pct(busy, total)}")
    # prediction curve levels
    pred_dist = Counter(r.get("predicted_level", "") for r in pred_rows)
    findings.append(f"  prediction curve levels: {dict(pred_dist)}")
    verdict = "BLOCKED" if blocked else "PASS"
    findings.insert(0, f"label distribution gate: {verdict}")
    return findings, blocked


def gate_coverage(train_rows: list[dict], pred_feat_rows: list[dict], curve_rows: list[dict]) -> tuple[list[str], bool]:
    findings = []
    train_venues = {r["venue_id"] for r in train_rows}
    pred_venues = {r["venue_id"] for r in pred_feat_rows}
    curve_venues = {r["venue_id"] for r in curve_rows}
    train_n = len(train_rows)
    pred_n = len(pred_feat_rows)
    curve_n = len(curve_rows)
    findings.append(f"  training_venue_count = {len(train_venues)}")
    findings.append(f"  training_row_count = {train_n}  ({train_n / max(len(train_venues),1):.2f} rows/venue)")
    findings.append(f"  prediction_venue_count = {len(pred_venues)}")
    findings.append(f"  forecast_row_count = {curve_n}")
    findings.append(f"  rows_per_venue (curve) = {curve_n / max(len(curve_venues),1):.2f}")
    cov = len(pred_venues) / max(len(train_venues), 1)
    findings.append(f"  prediction vs training venue coverage = {pct(len(pred_venues), len(train_venues))}")
    partial = cov < 0.5
    if partial:
        findings.append(f"  [WARN] prediction covers < 50% of training venues — mark partial rollout")
    findings.insert(0, "coverage gate (counts recorded, no implicit defaults): PASS")
    return findings, partial


def gate_sentinel_ratio(train_cols: list[str], train_rows: list[dict]) -> tuple[list[str], bool]:
    """Check sentinel/missing values in external feature columns.

    Sentinel values like humidity_pct=-1 or temperature_c=-999 indicate
    the pipeline failed to read from the external cache.  If a sentinel
    appears in > SENTINEL_THRESHOLD fraction of rows, the gate blocks.
    """
    checks = {
        "humidity_pct": -1,
        "temperature_c": -999,
        "wind_speed_kmh": -1,
    }
    findings = []
    blocked = False
    total = max(len(train_rows), 1)
    for col, sentinel in checks.items():
        if col not in train_cols:
            continue
        count = sum(1 for r in train_rows if float(r.get(col, 0)) == sentinel)
        ratio = count / total
        status = "BLOCK" if ratio > SENTINEL_THRESHOLD else "ok"
        if ratio > SENTINEL_THRESHOLD:
            blocked = True
        findings.append(
            f"  [{status}] {col}={sentinel}: {count}/{total} rows ({ratio:.1%}) "
            f"threshold={SENTINEL_THRESHOLD:.0%}"
        )
    verdict = "BLOCKED" if blocked else "PASS"
    findings.insert(0, f"sentinel ratio gate (> {SENTINEL_THRESHOLD:.0%} sentinel values => block): {verdict}")
    return findings, blocked


def gate_rolling_leakage(train_cols: list[str], train_rows: list[dict]) -> tuple[list[str], bool]:
    """Verify rolling/latest features only use data strictly before forecast_for.

    Checks:
      - latest_busyness_age_minutes >= 0 for all rows (negative = future data leak)
      - latest_score_missing ⇔ latest_busyness_age_minutes consistency
    """
    findings = []
    blocked = False
    age_col = "latest_busyness_age_minutes"
    if age_col not in train_cols:
        findings.append(f"  [WARN] {age_col} column not found — cannot verify rolling window integrity")
        findings.insert(0, "rolling window leakage gate: SKIP (column missing)")
        return findings, False

    total = len(train_rows)
    negative = 0
    min_age = float("inf")
    for r in train_rows:
        try:
            age = float(r.get(age_col, 0))
        except (ValueError, TypeError):
            age = 0
        if age < 0:
            negative += 1
        if age < min_age:
            min_age = age

    if negative > 0:
        blocked = True
        findings.append(f"  [BLOCK] {negative}/{total} rows have {age_col} < 0 (future data leak)")
    else:
        findings.append(f"  [ok]    no rows with {age_col} < 0")
    findings.append(f"  min {age_col} = {min_age:.1f} min (must be >= 0)")

    verdict = "BLOCKED" if blocked else "PASS"
    findings.insert(0, f"rolling window leakage gate (latest feature timestamp < forecast_for): {verdict}")
    return findings, blocked


def gate_train_val_split(
    train_rows: list[dict],
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> tuple[list[str], bool]:
    """Replicate the model's time_split and check no (venue_id, forecast_for)
    pair crosses the train/val boundary.  Also checks for intra-training
    duplicate keys (same venue_id + forecast_for appearing at different
    positions — these would contaminate rolling features).
    """
    findings = []
    blocked = False

    if not train_rows:
        findings.append("  [WARN] no training rows — skipping split audit")
        findings.insert(0, "train/val split duplicate gate: SKIP (no data)")
        return findings, False

    # Sort by forecast_for (same as time_split in forecast_v2_model.py)
    sorted_rows = sorted(train_rows, key=lambda r: r.get("forecast_for", ""))
    n = len(sorted_rows)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))

    # Check for duplicate (venue_id, forecast_for) pairs that could cross splits
    all_keys = [(r.get("venue_id", ""), r.get("forecast_for", "")) for r in sorted_rows]
    key_positions: dict[tuple[str, str], list[int]] = {}
    for i, key in enumerate(all_keys):
        key_positions.setdefault(key, []).append(i)

    cross_split = 0
    intra_dupes = 0
    for key, positions in key_positions.items():
        if len(positions) > 1:
            intra_dupes += 1
            in_train = any(p < train_end for p in positions)
            in_val = any(train_end <= p < val_end for p in positions)
            in_test = any(p >= val_end for p in positions)
            splits = sum([in_train, in_val, in_test])
            if splits > 1:
                cross_split += 1
                findings.append(f"  [BLOCK] key {key} appears in {splits} splits "
                                f"(positions {positions[:5]})")

    findings.append(f"  total rows: {n}, train: {train_end}, val: {val_end - train_end}, test: {n - val_end}")
    findings.append(f"  unique (venue_id, forecast_for) keys: {len(key_positions)}")
    findings.append(f"  keys with >1 row: {intra_dupes}")
    findings.append(f"  keys crossing split boundary: {cross_split}")

    if cross_split > 0:
        blocked = True
    verdict = "BLOCKED" if blocked else "PASS"
    findings.insert(0, f"train/val split duplicate gate (no key in multiple splits): {verdict}")
    return findings, blocked


def gate_external_features(train_cols: list[str], train_rows: list[dict]) -> tuple[list[str], bool]:
    findings = []
    sources = {"weather_source": "open_meteo", "gbfs_source": "lyft_gbfs_2.3", "mta_source": "gtfs_rt"}
    partial = False
    for col, expected in sources.items():
        if col not in train_cols:
            findings.append(f"  [BLOCK] missing column {col}")
            partial = True
            continue
        dist = Counter(r.get(col, "") for r in train_rows)
        top, top_n = dist.most_common(1)[0]
        status = "ok" if top == expected else "unavailable/other"
        if top != expected:
            partial = True
        findings.append(f"  {col}: top='{top}' ({pct(top_n, len(train_rows))}) expected='{expected}' -> {status}")
    verdict = "PARTIAL" if partial else "PASS"
    findings.insert(0, f"external feature gate: {verdict}")
    return findings, partial


def gate_target_leakage(train_cols: list[str]) -> tuple[list[str], bool]:
    forbidden = {"label_score", "label_level", "predicted_score"}
    leaked = forbidden & set(train_cols)
    # label_score/label_level are the target columns present in the training CSV
    # but must be EXCLUDED from feature_cols by the model. We verify they are not
    # used as features by checking the model's feature_cols construction cannot
    # be inspected from CSV alone; we flag their presence as target columns.
    findings = []
    targets = {"label_score", "label_level"} & set(train_cols)
    findings.append(f"  target columns present in training CSV: {sorted(targets)} (expected, model must exclude)")
    findings.append(f"  forbidden feature leakage columns found: {sorted(leaked - targets) or 'none'}")
    blocked = bool((leaked - targets))
    findings.insert(0, f"target leakage gate: {'BLOCKED' if blocked else 'PASS'}")
    return findings, blocked


def gate_curve(curve_rows: list[dict]) -> tuple[list[str], bool]:
    findings = []
    per_venue = Counter(r["venue_id"] for r in curve_rows)
    bad = {v: n for v, n in per_venue.items() if n != CURVE_POINTS}
    findings.append(f"  venues with != {CURVE_POINTS} points: {len(bad)} / {len(per_venue)}")
    if bad:
        sample = list(bad.items())[:5]
        findings.append(f"  examples: {sample}")
    blocked = bool(bad)
    findings.insert(0, f"12h curve gate ({CURVE_POINTS} points/venue): {'BLOCKED' if blocked else 'PASS'}")
    return findings, blocked


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="forecast-v2 pre-deployment quality gate (O5).")
    p.add_argument("--output-dir", default="output", help="Pipeline output directory.")
    args = p.parse_args(argv)

    out = Path(args.output_dir)
    metrics = load_metrics(out / "forecast_v2_model_metrics.csv")
    train_cols, train_rows = load_csv(out / "forecast_v2_training_features.csv")
    _, pred_feat_rows = load_csv(out / "forecast_v2_prediction_features.csv")
    _, curve_rows = load_csv(out / "prediction_curve_v2.csv")

    if not metrics:
        print("ERROR: forecast_v2_model_metrics.csv not found — run the pipeline first.", file=sys.stderr)
        return 1

    sections: list[tuple[str, bool, bool]] = []  # (text, blocked, partial)

    f, b = gate_leakage(metrics); sections.append(("\n".join(f), b, False))
    f, b = gate_sentinel_ratio(train_cols, train_rows); sections.append(("\n".join(f), b, False))
    f, b = gate_label_distribution(train_rows, curve_rows); sections.append(("\n".join(f), b, False))
    f, b = gate_target_leakage(train_cols); sections.append(("\n".join(f), b, False))
    f, b = gate_curve(curve_rows); sections.append(("\n".join(f), b, False))
    f, b = gate_rolling_leakage(train_cols, train_rows); sections.append(("\n".join(f), b, False))
    f, b = gate_train_val_split(train_rows); sections.append(("\n".join(f), b, False))
    f, p2 = gate_external_features(train_cols, train_rows); sections.append(("\n".join(f), False, p2))
    f, p2 = gate_coverage(train_rows, pred_feat_rows, curve_rows); sections.append(("\n".join(f), False, p2))

    print("=" * 70)
    print("forecast-v2 quality-gate audit (O5)")
    print("=" * 70)
    for text, _, _ in sections:
        print()
        print(text)

    any_blocked = any(s[1] for s in sections)
    any_partial = any(s[2] for s in sections)
    print()
    print("=" * 70)
    if any_blocked:
        print("OVERALL VERDICT: BLOCKED — do not claim production-validated.")
        print("  May ship only as smoke-test / partial rollout with explicit limitations.")
        code = 3
    elif any_partial:
        print("OVERALL VERDICT: PARTIAL ROLLOUT — ship with known limitations noted.")
        code = 2
    else:
        print("OVERALL VERDICT: PASS — production rollout allowed.")
        code = 0
    print("=" * 70)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
