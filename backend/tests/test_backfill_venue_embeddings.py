"""Unit tests for the venue_embeddings backfill script, with Gemini and
the DB layer faked out."""

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import backfill_venue_embeddings as backfill_module  # noqa: E402


VENUE = {
    "venue_id": "v_1001",
    "name": "Central Park Urgent Care",
    "venue_type": "clinic",
    "address": "150 E 42nd St, New York, NY 10017",
    "opening_hours": "Mon-Sun: 08:00 AM - 10:00 PM",
    "phone": "+1 (212) 661-8139",
    "accessible_status": "full_access",
    "accessibility_features": '["ramp", "lift"]',
    "language_tags": '["EN", "FR"]',
    "supported_services": '["Bilingual Staff (French)"]',
}


class _FakeCursor:
    def __init__(self, venues, embeddings_table):
        self._venues = venues
        self._embeddings_table = embeddings_table
        self._result = None

    def execute(self, query, params=()):
        query = " ".join(query.split())
        if query.startswith("SELECT * FROM venues WHERE venue_id"):
            self._result = [v for v in self._venues if v["venue_id"] == params[0]]
        elif query.startswith("SELECT * FROM venues"):
            self._result = list(self._venues)
        elif query.startswith("INSERT INTO venue_embeddings"):
            venue_id, embedding, text_snapshot, model_version = params
            self._embeddings_table[venue_id] = {
                "embedding": embedding,
                "text_snapshot": text_snapshot,
                "model_version": model_version,
            }
        else:
            raise AssertionError(f"Unexpected query: {query!r}")

    def fetchall(self):
        return self._result


def test_build_text_snapshot_includes_key_fields():
    snapshot = backfill_module._build_text_snapshot(VENUE)

    assert "Central Park Urgent Care (clinic)" in snapshot
    assert "150 E 42nd St" in snapshot
    assert "ramp" in snapshot
    assert "FR" in snapshot
    assert "Bilingual Staff (French)" in snapshot


def test_backfill_writes_embedding_for_each_venue(monkeypatch):
    embeddings_table = {}

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor([VENUE], embeddings_table)

    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor([VENUE], embeddings_table)

    monkeypatch.setattr(backfill_module.db, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(backfill_module.db, "db_transaction", fake_db_transaction)
    monkeypatch.setattr(backfill_module.gemini_client, "embed_text", lambda text: [0.1, 0.2, 0.3])

    count = backfill_module.backfill()

    assert count == 1
    assert "v_1001" in embeddings_table
    assert embeddings_table["v_1001"]["model_version"] == backfill_module.MODEL_VERSION


def test_backfill_dry_run_does_not_write(monkeypatch):
    embeddings_table = {}

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor([VENUE], embeddings_table)

    monkeypatch.setattr(backfill_module.db, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(backfill_module.gemini_client, "embed_text", lambda text: [0.1, 0.2])

    count = backfill_module.backfill(dry_run=True)

    assert count == 1
    assert embeddings_table == {}


def test_backfill_single_venue_id(monkeypatch):
    embeddings_table = {}
    other_venue = {**VENUE, "venue_id": "v_9999"}

    @contextmanager
    def fake_db_cursor():
        yield _FakeCursor([VENUE, other_venue], embeddings_table)

    @contextmanager
    def fake_db_transaction():
        yield _FakeCursor([VENUE, other_venue], embeddings_table)

    monkeypatch.setattr(backfill_module.db, "db_cursor", fake_db_cursor)
    monkeypatch.setattr(backfill_module.db, "db_transaction", fake_db_transaction)
    monkeypatch.setattr(backfill_module.gemini_client, "embed_text", lambda text: [0.1])

    count = backfill_module.backfill(venue_id="v_1001")

    assert count == 1
    assert list(embeddings_table.keys()) == ["v_1001"]
