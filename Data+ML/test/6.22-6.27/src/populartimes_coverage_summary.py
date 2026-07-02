"""Offline Popular Times coverage summary helpers.

This module reads already-generated DB/SerpAPI result files and computes
display tables for the notebook. It does not call SerpAPI or any other API.

API WARNING:
    Do not import or call venue_serpapi.py from this module. That script can
    perform live SerpAPI requests and consume quota.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


SCOPE_TYPES = ["healthcare", "restroom"]
COVERED_STATUSES = {"has_popular_times", "no_popular_times", "search_matched_unvalidated"}


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    """Return the standard project paths used by the notebook."""
    root = project_root or Path(__file__).resolve().parents[4]
    output_dir = root / "Data+ML/test/6.22-6.27/output"
    coverage_view_file = output_dir / "venue_label_status_coverage_view.csv"
    return {
        "project_root": root,
        "venue_file": root / "Data+ML/test/6.8-6.12_DB/tests/output/venues_clean.csv",
        "output_dir": output_dir,
        "label_file": coverage_view_file if coverage_view_file.exists() else output_dir / "venue_label_status.csv",
        "metadata_file": output_dir / "run_metadata.json",
    }


def safe_pct(numerator: float, denominator: float) -> float:
    """Return percentage rounded to one decimal place."""
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def load_inputs(
    venue_file: Path,
    label_file: Path,
    metadata_file: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Load venue CSV, SerpAPI label CSV, and run metadata JSON."""
    for path in [venue_file, label_file, metadata_file]:
        if not path.exists():
            raise FileNotFoundError(path)

    venues = pd.read_csv(venue_file)
    labels = pd.read_csv(label_file)
    metadata = json.loads(metadata_file.read_text())
    return venues, labels, metadata


def filter_scope(
    venues: pd.DataFrame,
    labels: pd.DataFrame,
    scope_types: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep only healthcare/restroom venues and matching SerpAPI labels."""
    types = scope_types or SCOPE_TYPES
    db_scope = venues[venues["venue_type"].isin(types)].copy()
    label_scope = labels[labels["venue_id"].isin(db_scope["venue_id"])].copy()
    return db_scope, label_scope


def build_type_summary(
    db_scope: pd.DataFrame,
    label_scope: pd.DataFrame,
    scope_types: list[str] | None = None,
) -> pd.DataFrame:
    """Compute DB count, SerpAPI checked count, and Popular Times count by type."""
    types = scope_types or SCOPE_TYPES
    rows: list[dict[str, Any]] = []

    for venue_type in types:
        db_count = int((db_scope["venue_type"] == venue_type).sum())
        type_labels = label_scope[label_scope["venue_type"] == venue_type]
        checked = int(type_labels["label_status"].isin(COVERED_STATUSES).sum())
        has_popular_times = int(type_labels["label_status"].eq("has_popular_times").sum())

        rows.append({
            "venue_type": venue_type,
            "db_count": db_count,
            "serpapi_checked": checked,
            "serpapi_coverage_pct_of_db": safe_pct(checked, db_count),
            "has_popular_times": has_popular_times,
            "popular_times_pct_of_db": safe_pct(has_popular_times, db_count),
            "popular_times_pct_of_checked": safe_pct(has_popular_times, checked),
        })

    summary = pd.DataFrame(rows)
    total_db = int(summary["db_count"].sum())
    total_checked = int(summary["serpapi_checked"].sum())
    total_popular = int(summary["has_popular_times"].sum())

    total = pd.DataFrame([{
        "venue_type": "TOTAL",
        "db_count": total_db,
        "serpapi_checked": total_checked,
        "serpapi_coverage_pct_of_db": safe_pct(total_checked, total_db),
        "has_popular_times": total_popular,
        "popular_times_pct_of_db": safe_pct(total_popular, total_db),
        "popular_times_pct_of_checked": safe_pct(total_popular, total_checked),
    }])
    return pd.concat([summary, total], ignore_index=True)


def build_status_breakdown(
    label_scope: pd.DataFrame,
    scope_types: list[str] | None = None,
) -> pd.DataFrame:
    """Return label_status counts by venue_type."""
    types = scope_types or SCOPE_TYPES
    status = (
        label_scope
        .groupby(["venue_type", "label_status"])
        .size()
        .unstack(fill_value=0)
        .reindex(types, fill_value=0)
    )
    status["total"] = status.sum(axis=1)
    return status.reset_index()


def build_district_summary(label_scope: pd.DataFrame) -> pd.DataFrame:
    """Compute DB, SerpAPI coverage, and Popular Times counts by district/type."""
    summary = (
        label_scope
        .assign(
            serpapi_checked=lambda df: df["label_status"].isin(COVERED_STATUSES),
            has_popular_times=lambda df: df["label_status"].eq("has_popular_times"),
        )
        .groupby(["district", "venue_type"])
        .agg(
            db_count=("venue_id", "count"),
            serpapi_checked=("serpapi_checked", "sum"),
            has_popular_times=("has_popular_times", "sum"),
        )
        .reset_index()
    )
    summary["serpapi_coverage_pct_of_db"] = (
        summary["serpapi_checked"] / summary["db_count"] * 100
    ).round(1)
    summary["popular_times_pct_of_db"] = (
        summary["has_popular_times"] / summary["db_count"] * 100
    ).round(1)
    return summary.sort_values(["district", "venue_type"]).reset_index(drop=True)


def build_summary_bundle(
    venue_file: Path,
    label_file: Path,
    metadata_file: Path,
) -> dict[str, Any]:
    """Load files and return all display tables used by the notebook."""
    venues, labels, metadata = load_inputs(venue_file, label_file, metadata_file)
    db_scope, label_scope = filter_scope(venues, labels)
    return {
        "venues": venues,
        "labels": labels,
        "metadata": metadata,
        "db_scope": db_scope,
        "label_scope": label_scope,
        "type_summary": build_type_summary(db_scope, label_scope),
        "status_breakdown": build_status_breakdown(label_scope),
        "district_summary": build_district_summary(label_scope),
        "unmatched_in_scope_count": len(set(db_scope["venue_id"]) - set(label_scope["venue_id"])),
    }
