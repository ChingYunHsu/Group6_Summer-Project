"""One-off backfill: embed every venue's operational description via
Gemini and upsert into venue_embeddings, so the RAG chatbot's retrieval
(api/chatbot.py's _retrieve_relevant_venues) has something to match
against. Confirmed needed because venue_embeddings is currently empty on
every environment this has been tried against, so every chatbot query
falls through to the mock response.

Usage (from backend/):
    poetry run python scripts/backfill_venue_embeddings.py
    poetry run python scripts/backfill_venue_embeddings.py --venue-id v_1001   # single venue
    poetry run python scripts/backfill_venue_embeddings.py --dry-run          # print, don't write

Requires GEMINI_API_KEY (same env var the Flask app reads via settings.py)
and a reachable MySQL matching DB_HOST/DB_PORT/... in settings.py.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app import create_app  # noqa: E402
import db  # noqa: E402
import gemini_client  # noqa: E402

MODEL_VERSION = gemini_client.EMBEDDING_MODEL


def _build_text_snapshot(venue: dict) -> str:
    """Plain-text operational description fed to the embedding model — the
    chatbot's grounded generation reads this same text back at query time,
    so keep it factual and free of marketing language."""
    lines = [
        f"{venue['name']} ({venue['venue_type']})",
        f"Address: {venue['address']}" if venue.get("address") else None,
        f"Opening hours: {venue['opening_hours']}" if venue.get("opening_hours") else None,
        f"Phone: {venue['phone']}" if venue.get("phone") else None,
        f"Accessibility: {venue['accessible_status']}" if venue.get("accessible_status") else None,
    ]

    accessibility_features = _parse_json_field(venue.get("accessibility_features"))
    if accessibility_features:
        lines.append("Accessibility features: " + ", ".join(accessibility_features))

    language_tags = _parse_json_field(venue.get("language_tags"))
    if language_tags:
        lines.append("Languages supported: " + ", ".join(language_tags))

    supported_services = _parse_json_field(venue.get("supported_services"))
    if supported_services:
        lines.append("Services: " + ", ".join(supported_services))

    return "\n".join(line for line in lines if line)


def _parse_json_field(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return []
    return value or []


def _fetch_venues(cursor, venue_id: str | None) -> list:
    if venue_id:
        cursor.execute("SELECT * FROM venues WHERE venue_id = %s", (venue_id,))
    else:
        cursor.execute("SELECT * FROM venues")
    return cursor.fetchall()


def backfill(venue_id: str | None = None, dry_run: bool = False) -> int:
    with db.db_cursor() as cursor:
        venues = _fetch_venues(cursor, venue_id)

    if not venues:
        print("No matching venues found.")
        return 0

    embedded_count = 0
    for venue in venues:
        text_snapshot = _build_text_snapshot(venue)
        embedding = gemini_client.embed_text(text_snapshot)

        print(f"[{venue['venue_id']}] {len(embedding)}-dim embedding — {text_snapshot.splitlines()[0]}")

        if not dry_run:
            with db.db_transaction() as cursor:
                cursor.execute(
                    "INSERT INTO venue_embeddings (venue_id, embedding, text_snapshot, model_version) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE embedding = VALUES(embedding), "
                    "text_snapshot = VALUES(text_snapshot), model_version = VALUES(model_version), "
                    "generated_at = CURRENT_TIMESTAMP",
                    (venue["venue_id"], json.dumps(embedding), text_snapshot, MODEL_VERSION),
                )

        embedded_count += 1

    return embedded_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue-id", help="Backfill a single venue instead of all venues.")
    parser.add_argument("--dry-run", action="store_true", help="Print embeddings without writing to the DB.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        count = backfill(venue_id=args.venue_id, dry_run=args.dry_run)

    verb = "Would embed" if args.dry_run else "Embedded"
    print(f"{verb} {count} venue(s).")


if __name__ == "__main__":
    main()
