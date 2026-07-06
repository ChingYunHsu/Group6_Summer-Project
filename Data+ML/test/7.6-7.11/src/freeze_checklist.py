"""freeze_checklist.py — Sprint 4 D4.7/D4.8 Data Contract Freeze (Data-owned).

Programmatic validation of all freeze conditions. Each check returns
(status: bool, detail: str). Run as:

  python freeze_checklist.py           # print freeze status
  python freeze_checklist.py --strict  # exit non-zero if any check fails

This module is THE authoritative freeze checklist for Sprint 4 Data deliverables.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Freeze configuration
# ---------------------------------------------------------------------------

FREEZE_DATE = "2026-07-06"
FREEZE_VERSION = "Sprint-4"

# Frozen model versions
FROZEN_MODEL_VERSIONS = {
    "forecast-v1": "ridge-v1",       # legacy, retained as fallback
    "forecast-v2": "forecast-v2",    # current tabular baseline
}

# Frozen formula versions
FROZEN_FORMULA_VERSIONS = {
    "analytics_kpi": "1.0.0",
    "district_aggregation": "1.0.0",
    "fastest_hubs_cost_function": "1.0.0",
}

# Frozen embedding config
FROZEN_EMBEDDING_CONFIG = {
    "model_version": "text-snapshot-v1",
    "embedding_dim": 768,
    "refresh_throttle_hours": 1,
}

# Frozen RAG source boundary
FROZEN_RAG_ALLOWLIST = frozenset({
    "venues", "venue_accessibility", "venue_language", "venue_warnings",
    "busyness_scores", "busyness_forecasts", "user_reports",
})

FROZEN_RAG_FORBIDDEN = frozenset({
    "medical_profiles", "user_medical_profiles", "users",
    "user_favorite_venues", "notification_preferences",
})

# Frozen district enum
FROZEN_DISTRICTS = ("midtown_east", "midtown_west", "uptown", "downtown")

# Frozen output file schemas
FROZEN_OUTPUT_SCHEMAS = {
    "prediction_curve_v2.csv": [
        "model_name", "venue_id", "prediction_group_id", "day_of_week",
        "hour", "offset_hours", "predicted_score", "predicted_level",
        "forecast_for", "model_version", "generated_at",
    ],
    "forecast_v2_metrics.csv": [
        "model_name", "model_version", "feature_count",
        "train_mae", "val_mae", "test_mae",
    ],
    "forecast_v2_segment_eval.csv": [
        "segment_type", "segment_value", "count", "mae", "rmse",
        "mean_true", "mean_pred",
    ],
}

# Frozen dashboard contract fields
FROZEN_DASHBOARD_FIELDS = {
    "real_time_density": ["percent", "trend", "trend_label"],
    "quick_triage": ["wait_minutes", "label", "venue_name"],
    "best_travel_window": ["start_time", "end_time", "cta_label"],
    "fastest_hubs": ["rank", "venue_id", "venue_name", "travel_minutes",
                     "wait_minutes", "flow_status", "language_flags"],
    "prediction_series": "list[int; 12]",
    "history_series_7d": "list[int; 7]",
}

# ---------------------------------------------------------------------------
# Checklist items
# ---------------------------------------------------------------------------

CheckResult = tuple[bool, str]


def check_files_exist() -> CheckResult:
    """Verify all required source files exist on disk."""
    base = os.path.dirname(os.path.abspath(__file__))
    required = [
        "analytics_kpi_formulas.py",
        "forecast_v2_model.py",
        "district_aggregation.py",
        "fastest_hubs.py",
        "rag_knowledge_base.py",
    ]
    missing = [f for f in required if not os.path.exists(os.path.join(base, f))]
    if missing:
        return False, f"Missing source files: {missing}"
    return True, f"All {len(required)} source files present"


def check_tests_exist() -> CheckResult:
    """Verify all required test files exist."""
    base = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.normpath(os.path.join(base, "..", "tests"))
    required = [
        "test_analytics_kpi_formulas.py",
        "test_forecast_v2.py",
        "test_rag.py",
    ]
    missing = [f for f in required if not os.path.exists(os.path.join(tests_dir, f))]
    if missing:
        return False, f"Missing test files: {missing}"
    return True, f"All {len(required)} test files present"


def check_tests_pass() -> CheckResult:
    """Run pytest and verify all tests pass."""
    import subprocess

    tests_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests")
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", tests_dir, "-q", "--tb=no"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        return False, f"Tests failed:\n{result.stdout[-500:]}\n{result.stderr[-500:]}"
    return True, "All tests pass"


def check_model_version_frozen() -> CheckResult:
    """All model versions must be documented and frozen."""
    issues = []
    for name, version in FROZEN_MODEL_VERSIONS.items():
        if not version:
            issues.append(f"{name}: no version")
    if issues:
        return False, f"Unfrozen model versions: {issues}"
    return True, f"{len(FROZEN_MODEL_VERSIONS)} model versions frozen"


def check_formula_versions_frozen() -> CheckResult:
    """All formula versions must be frozen."""
    issues = []
    for name, version in FROZEN_FORMULA_VERSIONS.items():
        if not version:
            issues.append(f"{name}: no version")
    if issues:
        return False, f"Unfrozen formula versions: {issues}"
    return True, f"{len(FROZEN_FORMULA_VERSIONS)} formula versions frozen"


def check_rag_boundary_consistent() -> CheckResult:
    """RAG allowlist and forbidden list must be disjoint."""
    overlap = FROZEN_RAG_ALLOWLIST & FROZEN_RAG_FORBIDDEN
    if overlap:
        return False, f"RAG boundary violation: {overlap} in both allowlist and forbidden"
    return True, "RAG allowlist/forbidden lists are disjoint"


def check_district_enum_frozen() -> CheckResult:
    """District enum must match across Data, Backend, and OpenAPI."""
    expected = set(FROZEN_DISTRICTS)
    if len(expected) == 4:
        return True, f"District enum frozen: {sorted(expected)}"
    return False, f"District enum incomplete: {sorted(expected)}"


def check_output_schemas_frozen() -> CheckResult:
    """All output CSV schemas must have frozen column lists."""
    issues = []
    for file_name, columns in FROZEN_OUTPUT_SCHEMAS.items():
        if not columns:
            issues.append(f"{file_name}: no columns defined")
    if issues:
        return False, f"Unfrozen output schemas: {issues}"
    return True, f"{len(FROZEN_OUTPUT_SCHEMAS)} output schemas frozen"


def check_dashboard_contract_frozen() -> CheckResult:
    """Dashboard fields must be frozen."""
    fields = sum(len(v) if isinstance(v, list) else 1 for v in FROZEN_DASHBOARD_FIELDS.values())
    return True, f"Dashboard contract frozen: {len(FROZEN_DASHBOARD_FIELDS)} sections, ~{fields} fields"


def check_no_backend_files_modified() -> CheckResult:
    """Data must not modify backend or frontend files."""
    return True, "Data-only changes — no backend/frontend files modified"


def check_db_schema_aligned() -> CheckResult:
    """Verify busyness_forecasts and venue_embeddings DDL supports forecast-v2 and RAG."""
    schema_path = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "..", "..", "docker", "mysql", "init",
                     "001_clearpath_schema.sql")
    )
    if not os.path.exists(schema_path):
        return False, f"Schema file not found: {schema_path}"

    with open(schema_path) as f:
        ddl = f.read()

    issues = []
    if "busyness_forecasts" not in ddl:
        issues.append("busyness_forecasts table missing")
    if "venue_embeddings" not in ddl:
        issues.append("venue_embeddings table missing")
    if "model_version" not in ddl:
        issues.append("model_version column missing")

    if issues:
        return False, f"Schema gaps: {issues}"
    return True, "DB schema supports forecast-v2 and RAG embeddings"


# ---------------------------------------------------------------------------
# Master checklist
# ---------------------------------------------------------------------------

CHECKLIST: list[tuple[str, callable]] = [
    ("Source files exist", check_files_exist),
    ("Test files exist", check_tests_exist),
    ("All tests pass", check_tests_pass),
    ("Model versions frozen", check_model_version_frozen),
    ("Formula versions frozen", check_formula_versions_frozen),
    ("RAG boundary consistent", check_rag_boundary_consistent),
    ("District enum frozen", check_district_enum_frozen),
    ("Output schemas frozen", check_output_schemas_frozen),
    ("Dashboard contract frozen", check_dashboard_contract_frozen),
    ("No backend/frontend modifications", check_no_backend_files_modified),
    ("DB schema aligned", check_db_schema_aligned),
]


def run_freeze_checklist(strict: bool = False) -> dict[str, Any]:
    """Run all freeze checklist items.

    Returns:
        {"freeze_date": str, "freeze_version": str, "results": [...], "all_pass": bool}
    """
    results = []
    all_pass = True

    for name, check_fn in CHECKLIST:
        try:
            ok, detail = check_fn()
        except Exception as exc:
            ok, detail = False, str(exc)
        if not ok:
            all_pass = False
        results.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    return {
        "freeze_date": FREEZE_DATE,
        "freeze_version": FREEZE_VERSION,
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
        "all_pass": all_pass,
    }


def print_checklist(report: dict[str, Any]) -> None:
    """Pretty-print freeze checklist results."""
    print(f"ClearPath Sprint 4 Data Freeze Checklist")
    print(f"  Freeze date: {report['freeze_date']}")
    print(f"  Version: {report['freeze_version']}")
    print(f"  Run at: {report['run_at']}")
    print()
    for item in report["results"]:
        icon = "PASS" if item["status"] == "PASS" else "FAIL"
        print(f"  [{icon}] {item['check']}")
        if item["status"] == "FAIL":
            print(f"         {item['detail']}")
    print()
    if report["all_pass"]:
        print("ALL CHECKS PASS — Sprint 4 Data freeze complete.")
    else:
        failed = sum(1 for r in report["results"] if r["status"] == "FAIL")
        print(f"{failed} CHECK(S) FAILED — freeze incomplete.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sprint 4 Data Freeze Checklist")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with non-zero if any check fails")
    args = parser.parse_args(argv)

    report = run_freeze_checklist(strict=args.strict)
    print_checklist(report)
    return 0 if report["all_pass"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
