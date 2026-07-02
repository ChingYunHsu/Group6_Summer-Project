"""Shared utilities for healthcare coverage scripts.

Extracted from duplicated code across batch, discovery, phased, validate,
build_label_view, and sync scripts.
"""

from __future__ import annotations

import os
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


# ── Path resolution ────────────────────────────────────────────


def resolve_path(path: str | Path) -> Path:
    """Resolve CLI paths relative to the calling script's directory."""
    p = Path(path)
    if p.is_absolute():
        return p
    return (Path(__file__).parent / p).resolve()


# ── Venue loading ──────────────────────────────────────────────


def load_uncovered_healthcare(
    label_file: Path,
    statuses: frozenset[str] = frozenset({"api_not_checked"}),
) -> pd.DataFrame:
    """Load healthcare venues whose label_status is in *statuses*.

    Parameters
    ----------
    label_file : Path
        Path to venue_label_status CSV.
    statuses : frozenset[str]
        Which label_status values to include.
        Use ``{"api_not_checked"}`` for batch-style queries.
        Use ``{"api_not_checked", "search_not_matched"}`` for discovery-style.
    """
    labels = pd.read_csv(label_file)
    required = {"venue_id", "venue_type", "label_status", "name", "latitude", "longitude"}
    missing = required - set(labels.columns)
    if missing:
        raise ValueError(f"Missing required columns in {label_file}: {sorted(missing)}")

    uncovered = labels[
        (labels["venue_type"] == "healthcare")
        & (labels["label_status"].isin(statuses))
    ].copy()
    return uncovered.sort_values(["district", "venue_id"]).reset_index(drop=True)


# ── Name matching ──────────────────────────────────────────────


def normalize_name(value) -> str:
    """Lowercase, collapse whitespace, ``&`` → ``and``."""
    return " ".join(str(value or "").lower().replace("&", " and ").split())


def name_similarity(left, right) -> float:
    """SequenceMatcher ratio (0–1) on normalised names."""
    left_norm = normalize_name(left)
    right_norm = normalize_name(right)
    if not left_norm or not right_norm:
        return 0.0
    return round(SequenceMatcher(None, left_norm, right_norm).ratio(), 4)


# ── API key guard ──────────────────────────────────────────────


def require_api_key(
    dry_run: bool,
    confirm_live_api: bool,
) -> str | None:
    """Return the SerpAPI key if the caller is allowed to make live calls.

    Exits with SystemExit on policy violation.  Returns ``None`` in dry-run
    mode (caller should skip API calls).
    """
    if dry_run:
        return None
    if not confirm_live_api:
        raise SystemExit("Refusing live API run without --confirm-live-api.")
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise SystemExit("SERPAPI_API_KEY is required for live API runs.")
    return api_key


# ── Label status updates ───────────────────────────────────────


def apply_label_updates(
    labels: pd.DataFrame,
    result_lookup: dict,
    *,
    id_column: str = "venue_id",
    filter_mask: pd.Series | None = None,
    has_popular_times_col: str = "has_popular_times",
    checked_at: str | None = None,
    default_note: str = "",
) -> pd.DataFrame:
    """Apply SerpAPI results to label DataFrame rows.

    For each row where *id_column* matches a key in *result_lookup* (and
    *filter_mask* is True if given), set the standard label columns:

    ``label_status, ml_eligible, prediction_source, display_level,
    serpapi_checked_at, serpapi_place_id, review_count, rating, notes``

    Parameters
    ----------
    labels : DataFrame
        Modified in-place and returned.
    result_lookup : dict
        ``{venue_or_place_id: dict-like with has_popular_times, ...}``
    id_column : str
        Column in *labels* to match against keys of *result_lookup*.
    filter_mask : Series or None
        Additional boolean mask; only matching rows are updated.
    has_popular_times_col : str
        Key inside each dict in *result_lookup* that indicates popular times.
    checked_at : str or None
        Timestamp string; defaults to current UTC time.
    default_note : str
        Written to the ``notes`` column for every updated row.
    """
    from datetime import datetime, timezone

    if not checked_at:
        checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if filter_mask is None:
        filter_mask = pd.Series(True, index=labels.index)

    mask = filter_mask & labels[id_column].isin(result_lookup)

    for index, row in labels[mask].iterrows():
        result = result_lookup[row[id_column]]
        has_pt = bool(result.get(has_popular_times_col, False))
        labels.at[index, "label_status"] = (
            "has_popular_times" if has_pt else "no_popular_times"
        )
        labels.at[index, "ml_eligible"] = has_pt
        labels.at[index, "prediction_source"] = (
            "ml_model" if has_pt else "rule_fallback"
        )
        labels.at[index, "display_level"] = "quiet" if has_pt else "no_data"
        labels.at[index, "serpapi_checked_at"] = checked_at
        labels.at[index, "serpapi_place_id"] = result.get("serpapi_place_id")
        labels.at[index, "review_count"] = result.get(
            "reviews", result.get("review_count")
        )
        labels.at[index, "rating"] = result.get("rating")
        if default_note:
            labels.at[index, "notes"] = default_note

    return labels
