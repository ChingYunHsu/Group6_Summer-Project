"""rag_knowledge_base.py — Sprint 4 D4.5 RAG Knowledge Base & Embeddings (Data-owned).

Generates venue text snapshots from allowed public operational data sources,
produces embedding vectors (stub for local dev; real model in production),
and writes to the venue_embeddings table.

Allowed sources (frozen Sprint 4):
  - venues
  - venue_accessibility
  - venue_language
  - venue_warnings
  - busyness_scores
  - busyness_forecasts
  - user_reports

FORBIDDEN sources (must NEVER enter embeddings or prompts):
  - medical_profiles
  - user_medical_profiles
  - user preferences, favorites, notification settings
  - Any user-identifying records

Embedding refresh throttling: ≥ 1 hour between refresh cycles.
Embedding generation is NOT on the user request path.

Usage:
  python rag_knowledge_base.py --dry-run       # generate snapshots only
  python rag_knowledge_base.py --execute        # write to venue_embeddings
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_VERSION = "text-snapshot-v1"
EMBEDDING_DIM = 768  # Gemini text-embedding-004 dimension
REFRESH_THROTTLE_HOURS = 1

# Frozen allowlist of SQL tables/views for RAG context
RAG_SOURCE_ALLOWLIST = frozenset({
    "venues",
    "venue_accessibility",
    "venue_language",
    "venue_warnings",
    "busyness_scores",
    "busyness_forecasts",
    "user_reports",
})

# FORBIDDEN — retrieval SQL must never reference these
RAG_FORBIDDEN_SOURCES = frozenset({
    "medical_profiles",
    "user_medical_profiles",
    "users",               # only for auth, not for RAG context
    "user_favorite_venues",
    "notification_preferences",
})


# ---------------------------------------------------------------------------
# Text snapshot generation
# ---------------------------------------------------------------------------

def build_venue_text_snapshot(
    venue: dict[str, Any],
    accessibility: Optional[dict[str, Any]] = None,
    language_info: Optional[dict[str, Any]] = None,
    warnings: Optional[dict[str, Any]] = None,
    latest_score: Optional[dict[str, Any]] = None,
    recent_reports: Optional[list[dict[str, Any]]] = None,
) -> str:
    """Build a searchable text snapshot for one venue.

    The snapshot is a structured natural-language block that the embedding
    model can encode for semantic search. It MUST only include data from
    allowed sources.

    Args:
        venue: Row from venues table.
        accessibility: Row from venue_accessibility.
        language_info: Row from venue_language.
        warnings: Row from venue_warnings.
        latest_score: Latest row from busyness_scores.
        recent_reports: List of active user_reports for this venue.

    Returns:
        Multiline text block suitable for embedding.
    """
    parts = []

    # Core identity
    name = venue.get("name", "Unknown Venue")
    venue_type = venue.get("venue_type", "unknown")
    parts.append(f"Venue: {name}")
    parts.append(f"Type: {venue_type}")
    if venue.get("address"):
        parts.append(f"Address: {venue['address']}")
    if venue.get("borough"):
        parts.append(f"Borough: {venue['borough']}")
    if venue.get("district"):
        parts.append(f"District: {venue['district']}")

    # Location
    if venue.get("latitude") and venue.get("longitude"):
        parts.append(f"Location: ({venue['latitude']}, {venue['longitude']})")

    # Opening hours
    if venue.get("opening_hours"):
        parts.append(f"Opening Hours: {venue['opening_hours']}")

    # Accessibility
    if accessibility:
        acc_parts = []
        if accessibility.get("wheelchair_friendly"):
            acc_parts.append("wheelchair accessible")
        if accessibility.get("step_free_route"):
            acc_parts.append("step-free route available")
        if accessibility.get("accessible_toilet"):
            acc_parts.append("accessible toilet")
        if accessibility.get("entrance_width_cm"):
            acc_parts.append(f"entrance width {accessibility['entrance_width_cm']}cm")
        if acc_parts:
            parts.append("Accessibility: " + ", ".join(acc_parts))

    # Language support
    if language_info:
        lang_parts = []
        if language_info.get("language_support_level"):
            lang_parts.append(f"support level: {language_info['language_support_level']}")
        if language_info.get("language_tag"):
            tags = language_info["language_tag"]
            if isinstance(tags, str):
                tags = json.loads(tags)
            if isinstance(tags, list):
                lang_parts.append(f"languages: {', '.join(tags)}")
        if lang_parts:
            parts.append("Language: " + "; ".join(lang_parts))

    # Warnings
    if warnings and warnings.get("active_warning"):
        warn_text = warnings.get("warning_detail", "Active warning in effect")
        parts.append(f"WARNING: {warn_text}")

    # Current busyness
    if latest_score:
        level = latest_score.get("level", "no_data")
        score = latest_score.get("score", "N/A")
        wait = latest_score.get("estimated_wait_minutes", "N/A")
        parts.append(f"Current Status: {level} (score: {score}, wait: {wait} min)")

    # Recent reports
    if recent_reports:
        parts.append(f"Recent Reports ({len(recent_reports)}):")
        for report in recent_reports[:5]:  # cap at 5 for snapshot size
            issue = report.get("issue_type", "unknown")
            desc = report.get("description", "")
            status = report.get("status", "active")
            parts.append(f"  - [{status}] {issue}: {desc}"[:200])

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Embedding generation (stub)
# ---------------------------------------------------------------------------

def generate_stub_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Generate a deterministic stub embedding from text hash.

    In production, this is replaced by Gemini text-embedding-004 API call.
    The stub uses SHA-256 of the text to seed a reproducible vector so that
    retrieval tests can run without API keys.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # Use hash bytes to seed a deterministic vector via numpy
    # numpy RandomState requires seed in [0, 2**32 - 1]
    seed = int.from_bytes(h[:4], "big")
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim).astype(np.float64)
    vec = vec / np.linalg.norm(vec)  # L2 normalize
    return vec.tolist()


# ---------------------------------------------------------------------------
# Embedding SQL writer
# ---------------------------------------------------------------------------

def embedding_upsert_sql(
    venue_id: str,
    embedding_json: str,
    text_snapshot: str,
    model_version: str,
) -> str:
    """Generate idempotent INSERT ... ON DUPLICATE KEY UPDATE for venue_embeddings.

    Returns a parameter-free SQL string for dry-run auditing.
    """
    escaped_snapshot = text_snapshot.replace("\\", "\\\\").replace("'", "\\'")
    return (
        f"INSERT INTO venue_embeddings (venue_id, embedding, text_snapshot, model_version) VALUES "
        f"('{venue_id}', '{embedding_json}', '{escaped_snapshot}', '{model_version}') "
        f"ON DUPLICATE KEY UPDATE "
        f"embedding = VALUES(embedding), "
        f"text_snapshot = VALUES(text_snapshot), "
        f"model_version = VALUES(model_version), "
        f"generated_at = CURRENT_TIMESTAMP;"
    )


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_embedding_pipeline(
    venues: pd.DataFrame,
    accessibility: Optional[pd.DataFrame] = None,
    languages: Optional[pd.DataFrame] = None,
    warnings: Optional[pd.DataFrame] = None,
    scores: Optional[pd.DataFrame] = None,
    reports: Optional[pd.DataFrame] = None,
    dry_run: bool = True,
) -> pd.DataFrame:
    """Run the full embedding pipeline: snapshot → embed → (optional) write.

    Args:
        venues: All venue rows from allowed sources.
        accessibility: venue_accessibility rows.
        languages: venue_language rows.
        warnings: venue_warnings rows.
        scores: Latest busyness_scores per venue.
        reports: Active user_reports per venue.
        dry_run: If True, only generate snapshots and embeddings; skip DB write.

    Returns:
        DataFrame with [venue_id, text_snapshot, embedding_dim, model_version, generated_at].
    """
    # Build lookup dicts
    acc_map = {} if accessibility is None else accessibility.set_index("venue_id").to_dict("index")
    lang_map = {} if languages is None else languages.set_index("venue_id").to_dict("index")
    warn_map = {} if warnings is None else warnings.set_index("venue_id").to_dict("index")
    score_map = {} if scores is None else scores.set_index("venue_id").to_dict("index")

    report_map: dict[str, list[dict]] = {}
    if reports is not None and not reports.empty:
        for _, row in reports.iterrows():
            vid = row.get("venue_id")
            if vid:
                report_map.setdefault(vid, []).append(row.to_dict())

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    for _, venue in venues.iterrows():
        vid = venue["venue_id"]
        snapshot = build_venue_text_snapshot(
            venue.to_dict(),
            accessibility=acc_map.get(vid),
            language_info=lang_map.get(vid),
            warnings=warn_map.get(vid),
            latest_score=score_map.get(vid),
            recent_reports=report_map.get(vid),
        )
        embedding = generate_stub_embedding(snapshot)

        results.append({
            "venue_id": vid,
            "text_snapshot": snapshot,
            "embedding": embedding,
            "embedding_dim": len(embedding),
            "model_version": MODEL_VERSION,
            "generated_at": generated_at,
        })

        if not dry_run:
            sql = embedding_upsert_sql(vid, json.dumps(embedding), snapshot, MODEL_VERSION)
            # In production, execute this SQL against the DB

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Source validation
# ---------------------------------------------------------------------------

def validate_rag_sources(sources_referenced: set[str]) -> tuple[bool, list[str]]:
    """Validate that only allowed sources are referenced in RAG SQL/prompts.

    Args:
        sources_referenced: Set of table/view names used in retrieval.

    Returns:
        (is_valid, list_of_violations)
    """
    violations = []
    for source in sources_referenced:
        if source in RAG_FORBIDDEN_SOURCES:
            violations.append(f"FORBIDDEN: {source} — must not be accessed by RAG retrieval")
        elif source not in RAG_SOURCE_ALLOWLIST:
            violations.append(f"UNKNOWN: {source} — not in RAG allowlist, needs review")
    return len(violations) == 0, violations


# ---------------------------------------------------------------------------
# Throttle check
# ---------------------------------------------------------------------------

def can_refresh_embeddings(last_generated_at: Optional[datetime]) -> tuple[bool, str]:
    """Check if embedding refresh is allowed (≥ 1 hour since last run)."""
    if last_generated_at is None:
        return True, "No previous generation — refresh allowed"
    elapsed = datetime.now() - last_generated_at
    if elapsed >= timedelta(hours=REFRESH_THROTTLE_HOURS):
        return True, f"Last refresh {elapsed.total_seconds() / 3600:.1f}h ago — refresh allowed"
    return False, f"Last refresh {elapsed.total_seconds() / 3600:.1f}h ago — throttled (min {REFRESH_THROTTLE_HOURS}h)"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAG embedding pipeline (Sprint 4 D4.5)")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Generate snapshots + embeddings only (no DB write)")
    parser.add_argument("--execute", action="store_true",
                        help="Write embeddings to venue_embeddings table")
    parser.add_argument("--venue-csv", help="Path to venues CSV for offline testing")
    args = parser.parse_args(argv)

    if args.venue_csv:
        venues = pd.read_csv(args.venue_csv)
        result = run_embedding_pipeline(venues, dry_run=not args.execute)
        print(f"Generated {len(result)} venue embeddings")
        print(f"  Model version: {MODEL_VERSION}")
        print(f"  Embedding dim: {EMBEDDING_DIM}")
        if args.execute:
            print("  Mode: --execute (would write to DB)")
        else:
            print("  Mode: --dry-run (no DB writes)")
        sample = result.iloc[0]
        print(f"\nSample snapshot for {sample['venue_id']}:")
        print(sample["text_snapshot"][:500])
    else:
        print("RAG embedding pipeline ready.")
        print(f"  Model version: {MODEL_VERSION}")
        print(f"  Embedding dim: {EMBEDDING_DIM}")
        print(f"  Allowed sources: {sorted(RAG_SOURCE_ALLOWLIST)}")
        print(f"  Use --venue-csv to process venue data")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
