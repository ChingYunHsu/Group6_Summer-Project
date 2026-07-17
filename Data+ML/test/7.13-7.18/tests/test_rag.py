"""Tests for RAG knowledge base — Sprint 4 D4.6.

Covers:
  - Multilingual query fixtures (EN/ZH/FR) → correct venue/context retrieval
  - Forbidden-source regression: medical_profiles / user_medical_profiles
    must NEVER appear in embedding text, retrieval SQL, or prompts
  - Source allowlist validation
  - Text snapshot content verification
  - Embedding refresh throttle
  - Stub embedding determinism

Run: python -m pytest Data+ML/test/7.13-7.18/tests/test_rag.py -v
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from rag_knowledge_base import (
    EMBEDDING_DIM,
    MODEL_VERSION,
    RAG_FORBIDDEN_SOURCES,
    RAG_SOURCE_ALLOWLIST,
    REFRESH_THROTTLE_HOURS,
    build_venue_text_snapshot,
    can_refresh_embeddings,
    embedding_upsert_sql,
    generate_stub_embedding,
    run_embedding_pipeline,
    validate_rag_sources,
)


# ============================================================================
# Multilingual Fixtures
# ============================================================================

def _venue_en() -> dict:
    return {
        "venue_id": "v_1001",
        "name": "Central Park Urgent Care",
        "venue_type": "healthcare",
        "address": "123 W 59th St, New York, NY 10019",
        "borough": "Manhattan",
        "district": "midtown_west",
        "latitude": 40.7681,
        "longitude": -73.9819,
        "opening_hours": "Mon-Fri 08:00-20:00, Sat-Sun 09:00-18:00",
    }


def _venue_zh() -> dict:
    return {
        "venue_id": "v_2001",
        "name": "唐人街社区诊所",
        "venue_type": "clinic",
        "address": "125 Walker St, New York, NY 10013",
        "borough": "Manhattan",
        "district": "downtown",
        "latitude": 40.7175,
        "longitude": -73.9992,
        "opening_hours": "每天 09:00-19:00",
    }


def _venue_fr() -> dict:
    return {
        "venue_id": "v_3001",
        "name": "Pharmacie Française",
        "venue_type": "pharmacy",
        "address": "45 Rue de Lafayette, New York, NY 10009",
        "borough": "Manhattan",
        "district": "midtown_east",
        "latitude": 40.7282,
        "longitude": -73.9877,
        "opening_hours": "Lun-Sam 09:00-21:00, Dim 10:00-18:00",
    }


def _accessibility_full() -> dict:
    return {
        "venue_id": "v_1001",
        "wheelchair_friendly": True,
        "step_free_route": True,
        "accessible_toilet": True,
        "entrance_width_cm": 120,
    }


def _language_en_fr() -> dict:
    return {
        "venue_id": "v_1001",
        "language_tag": json.dumps(["EN", "FR"]),
        "language_support_level": "full",
    }


def _language_zh_en() -> dict:
    return {
        "venue_id": "v_2001",
        "language_tag": json.dumps(["ZH", "EN"]),
        "language_support_level": "full",
    }


def _warning_active() -> dict:
    return {
        "venue_id": "v_1001",
        "active_warning": True,
        "warning_detail": "Elevator under maintenance — use stairs",
    }


def _score_moderate() -> dict:
    return {
        "venue_id": "v_1001",
        "score": 55,
        "level": "moderate",
        "estimated_wait_minutes": 12,
    }


def _reports() -> list[dict]:
    return [
        {"venue_id": "v_1001", "issue_type": "long_wait", "status": "active",
         "description": "Waiting room full, estimated 30 min wait"},
        {"venue_id": "v_1001", "issue_type": "closed", "status": "resolved",
         "description": "Was temporarily closed for cleaning"},
    ]


# ============================================================================
# Text Snapshot Tests
# ============================================================================

class TestTextSnapshot:
    def test_snapshot_includes_venue_core_fields(self):
        snapshot = build_venue_text_snapshot(_venue_en())
        assert "Central Park Urgent Care" in snapshot
        assert "healthcare" in snapshot
        assert "123 W 59th St" in snapshot
        assert "midtown_west" in snapshot

    def test_snapshot_includes_accessibility(self):
        snapshot = build_venue_text_snapshot(_venue_en(), accessibility=_accessibility_full())
        assert "wheelchair accessible" in snapshot
        assert "step-free route" in snapshot
        assert "accessible toilet" in snapshot
        assert "120cm" in snapshot

    def test_snapshot_includes_language_info(self):
        snapshot = build_venue_text_snapshot(_venue_en(), language_info=_language_en_fr())
        assert "EN" in snapshot
        assert "FR" in snapshot
        assert "full" in snapshot

    def test_snapshot_includes_warnings(self):
        snapshot = build_venue_text_snapshot(_venue_en(), warnings=_warning_active())
        assert "WARNING" in snapshot
        assert "Elevator under maintenance" in snapshot

    def test_snapshot_includes_busyness(self):
        snapshot = build_venue_text_snapshot(_venue_en(), latest_score=_score_moderate())
        assert "moderate" in snapshot
        assert "55" in snapshot
        assert "12 min" in snapshot

    def test_snapshot_includes_reports(self):
        snapshot = build_venue_text_snapshot(_venue_en(), recent_reports=_reports())
        assert "Recent Reports" in snapshot
        assert "long_wait" in snapshot

    def test_snapshot_never_contains_medical_data(self):
        """FORBIDDEN-SOURCE REGRESSION: medical fields must not appear."""
        # Simulate a venue row that somehow has medical data injected
        contaminated = {**_venue_en(), "allergies": "Penicillin", "blood_type": "O+"}
        snapshot = build_venue_text_snapshot(contaminated)
        assert "Penicillin" not in snapshot
        assert "O+" not in snapshot
        assert "allergies" not in snapshot.lower()
        assert "blood_type" not in snapshot.lower()

    def test_snapshot_never_contains_user_personal_data(self):
        """FORBIDDEN-SOURCE REGRESSION: personal/contact data must not appear."""
        contaminated = {**_venue_en(), "email": "user@example.com", "phone": "+1-555-0100"}
        snapshot = build_venue_text_snapshot(contaminated)
        # phone is a venue field (not user), but email from user table must not appear
        # The build function only uses known fields, so this is inherently safe
        assert "user@example.com" not in snapshot.lower() if "email" not in _venue_en() else True

    # --- Multilingual snapshots ---

    def test_chinese_venue_snapshot_preserves_name(self):
        snapshot = build_venue_text_snapshot(_venue_zh())
        assert "唐人街社区诊所" in snapshot
        assert "downtown" in snapshot

    def test_french_venue_snapshot_preserves_name(self):
        snapshot = build_venue_text_snapshot(_venue_fr())
        assert "Pharmacie Française" in snapshot
        assert "midtown_east" in snapshot


# ============================================================================
# Embedding Tests
# ============================================================================

class TestEmbeddings:
    def test_stub_embedding_is_deterministic(self):
        text = "Central Park Urgent Care — wheelchair accessible"
        e1 = generate_stub_embedding(text)
        e2 = generate_stub_embedding(text)
        assert e1 == e2

    def test_stub_embedding_different_for_different_text(self):
        e1 = generate_stub_embedding("Central Park Urgent Care")
        e2 = generate_stub_embedding("Brooklyn Bridge Pharmacy")
        assert e1 != e2

    def test_stub_embedding_correct_dimension(self):
        e = generate_stub_embedding("test venue")
        assert len(e) == EMBEDDING_DIM

    def test_stub_embedding_l2_normalized(self):
        e = generate_stub_embedding("test venue")
        norm = np.sqrt(sum(x * x for x in e))
        assert abs(norm - 1.0) < 1e-10

    def test_multilingual_embeddings_differ(self):
        """EN, ZH, FR snapshots for same venue type produce different embeddings."""
        e_en = generate_stub_embedding(build_venue_text_snapshot(_venue_en()))
        e_zh = generate_stub_embedding(build_venue_text_snapshot(_venue_zh()))
        e_fr = generate_stub_embedding(build_venue_text_snapshot(_venue_fr()))
        assert e_en != e_zh
        assert e_en != e_fr
        assert e_zh != e_fr


# ============================================================================
# Source Validation (FORBIDDEN-SOURCE REGRESSION)
# ============================================================================

class TestSourceValidation:
    def test_allowlist_passes_clean_sources(self):
        ok, violations = validate_rag_sources({"venues", "busyness_scores", "user_reports"})
        assert ok
        assert len(violations) == 0

    def test_forbidden_medical_profiles_blocked(self):
        ok, violations = validate_rag_sources({"venues", "medical_profiles"})
        assert not ok
        assert any("medical_profiles" in v for v in violations)

    def test_forbidden_user_medical_profiles_blocked(self):
        ok, violations = validate_rag_sources({"user_medical_profiles", "venues"})
        assert not ok
        assert any("user_medical_profiles" in v for v in violations)

    def test_forbidden_users_table_blocked(self):
        ok, violations = validate_rag_sources({"users"})
        assert not ok
        assert any("users" in v for v in violations)

    def test_forbidden_notification_preferences_blocked(self):
        ok, violations = validate_rag_sources({"notification_preferences"})
        assert not ok

    def test_forbidden_user_favorites_blocked(self):
        ok, violations = validate_rag_sources({"user_favorite_venues"})
        assert not ok

    def test_unknown_source_flagged(self):
        ok, violations = validate_rag_sources({"some_new_table"})
        assert not ok
        assert any("UNKNOWN" in v for v in violations)

    def test_all_allowed_sources_pass(self):
        """Every source in the allowlist must pass validation."""
        ok, violations = validate_rag_sources(set(RAG_SOURCE_ALLOWLIST))
        assert ok, f"Allowlist sources should all pass: {violations}"

    def test_all_forbidden_sources_fail(self):
        """Every forbidden source must be caught."""
        for source in RAG_FORBIDDEN_SOURCES:
            ok, violations = validate_rag_sources({source})
            assert not ok, f"{source} should be blocked but wasn't"


# ============================================================================
# Pipeline Tests
# ============================================================================

class TestPipeline:
    def test_pipeline_generates_snapshots_for_all_venues(self):
        venues = pd.DataFrame([_venue_en(), _venue_zh(), _venue_fr()])
        result = run_embedding_pipeline(venues, dry_run=True)
        assert len(result) == 3
        assert all(result["model_version"] == MODEL_VERSION)

    def test_pipeline_embeddings_have_correct_dim(self):
        venues = pd.DataFrame([_venue_en(), _venue_zh()])
        result = run_embedding_pipeline(venues, dry_run=True)
        assert (result["embedding_dim"] == EMBEDDING_DIM).all()

    def test_pipeline_with_accessibility_and_language(self):
        venues = pd.DataFrame([_venue_en()])
        acc = pd.DataFrame([_accessibility_full()])
        lang = pd.DataFrame([_language_en_fr()])
        result = run_embedding_pipeline(venues, accessibility=acc, languages=lang, dry_run=True)
        snapshot = result.iloc[0]["text_snapshot"]
        assert "wheelchair" in snapshot
        assert "EN" in snapshot

    def test_pipeline_with_warnings_and_scores(self):
        venues = pd.DataFrame([_venue_en()])
        warn = pd.DataFrame([_warning_active()])
        scores = pd.DataFrame([_score_moderate()])
        result = run_embedding_pipeline(venues, warnings=warn, scores=scores, dry_run=True)
        snapshot = result.iloc[0]["text_snapshot"]
        assert "WARNING" in snapshot
        assert "moderate" in snapshot

    def test_pipeline_empty_venues_handled(self):
        venues = pd.DataFrame(columns=["venue_id", "name", "venue_type"])
        result = run_embedding_pipeline(venues, dry_run=True)
        assert len(result) == 0


# ============================================================================
# SQL Generation Tests
# ============================================================================

class TestEmbeddingSQL:
    def test_upsert_sql_is_idempotent(self):
        sql = embedding_upsert_sql("v_1001", "[0.1, 0.2]", "Test snapshot", MODEL_VERSION)
        assert "INSERT INTO venue_embeddings" in sql
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert "v_1001" in sql
        assert MODEL_VERSION in sql

    def test_upsert_sql_escapes_single_quotes(self):
        sql = embedding_upsert_sql("v_1001", "[0.1]", "O'Brien's Clinic", MODEL_VERSION)
        assert "O\\'Brien\\'s Clinic" in sql


# ============================================================================
# Throttle Tests
# ============================================================================

class TestThrottle:
    def test_first_run_always_allowed(self):
        ok, msg = can_refresh_embeddings(None)
        assert ok

    def test_recent_run_throttled(self):
        just_now = datetime.now() - timedelta(minutes=30)
        ok, msg = can_refresh_embeddings(just_now)
        assert not ok
        assert "throttled" in msg

    def test_old_run_allowed(self):
        old = datetime.now() - timedelta(hours=2)
        ok, msg = can_refresh_embeddings(old)
        assert ok

    def test_exactly_one_hour_allowed(self):
        exactly = datetime.now() - timedelta(hours=1)
        ok, _ = can_refresh_embeddings(exactly)
        assert ok


# ============================================================================
# RAG Data Boundary Integration Tests
# ============================================================================

class TestRAGDataBoundary:
    """End-to-end data boundary tests: ensure the RAG pipeline NEVER leaks
    forbidden data into snapshots, embeddings, or SQL."""

    FORBIDDEN_TERMS = [
        "allergies", "conditions", "medications", "blood_type",
        "emergency_contact", "medical_profile", "user_medical",
        "password_hash", "email_verified",
    ]

    def test_snapshot_field_allowlist_no_leakage(self):
        """All fields in text snapshot must come from allowed venue data only."""
        snapshot = build_venue_text_snapshot(
            _venue_en(),
            accessibility=_accessibility_full(),
            language_info=_language_en_fr(),
            warnings=_warning_active(),
            latest_score=_score_moderate(),
            recent_reports=_reports(),
        )
        lower = snapshot.lower()
        for term in self.FORBIDDEN_TERMS:
            assert term not in lower, f"Forbidden term '{term}' found in snapshot"

    def test_embedding_sql_references_only_allowed_table(self):
        """All generated SQL must write to venue_embeddings only."""
        sql = embedding_upsert_sql("v_test", "[0.1]", "test", MODEL_VERSION)
        assert "venue_embeddings" in sql
        for forbidden in RAG_FORBIDDEN_SOURCES:
            assert forbidden not in sql.lower(), f"Forbidden table '{forbidden}' in SQL"

    def test_rag_allowlist_and_forbidden_are_disjoint(self):
        """Critical: allowlist and forbidden lists must have zero overlap."""
        overlap = RAG_SOURCE_ALLOWLIST & RAG_FORBIDDEN_SOURCES
        assert len(overlap) == 0, f"Overlap between allowlist and forbidden: {overlap}"

    def test_forbidden_sources_not_in_allowlist(self):
        """Double-check each forbidden source is truly not in allowlist."""
        for forbidden in RAG_FORBIDDEN_SOURCES:
            assert forbidden not in RAG_SOURCE_ALLOWLIST, (
                f"{forbidden} is in both allowlist and forbidden — this is a critical config error"
            )
