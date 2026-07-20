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

Confirmed live: Gemini's embedding API has a real per-minute rate limit,
and with ~4,800 venues queued sequentially with no delay at all, hitting
a 429 partway through is expected, not a fluke. Two things added to
handle this:
  - Already-embedded venues (from a previous run, including one that got
    cut short by a 429) are skipped on the next run, rather than
    redoing work and wasting quota before reaching new venues.
  - A 429 specifically triggers a wait-and-retry (a few attempts, with
    increasing delay) rather than immediately crashing the whole run.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import requests  # noqa: E402

from app import create_app  # noqa: E402
import db  # noqa: E402
import gemini_client  # noqa: E402

MODEL_VERSION = gemini_client.EMBEDDING_MODEL

# Conservative delay between successful calls, and retry behaviour
# specifically for 429s. Tune DELAY_SECONDS down if this turns out to be
# unnecessarily slow for whatever the real per-minute quota is — this is
# a cautious starting point, not a value confirmed against Google's
# actual documented limit for this specific API key/tier.
DELAY_SECONDS = 1.0
MAX_RETRIES = 5
RETRY_BACKOFF_SECONDS = 30


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


def _fetch_already_embedded_ids(cursor) -> set:
    cursor.execute("SELECT venue_id FROM venue_embeddings")
    return {row["venue_id"] for row in cursor.fetchall()}


def _embed_with_retry(text_snapshot: str):
    """Wraps gemini_client.embed_text with a wait-and-retry specifically
    for 429s — everything else still raises immediately, since a 429 is
    the one failure mode that's expected to resolve itself with time,
    not something that indicates a real problem with this specific
    request."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return gemini_client.embed_text(text_snapshot)
        except requests.exceptions.HTTPError as error:
            is_rate_limit = (
                error.response is not None and error.response.status_code == 429
            )

            if not is_rate_limit or attempt == MAX_RETRIES:
                raise

            wait_seconds = RETRY_BACKOFF_SECONDS * attempt
            print(
                f"  Rate limited (attempt {attempt}/{MAX_RETRIES}) — "
                f"waiting {wait_seconds}s before retrying..."
            )
            time.sleep(wait_seconds)


def backfill(venue_id: str | None = None, dry_run: bool = False) -> int:
    with db.db_cursor() as cursor:
        venues = _fetch_venues(cursor, venue_id)
        already_embedded = _fetch_already_embedded_ids(cursor)

    # --venue-id always processes that one venue regardless of whether
    # it's already embedded, matching the original script's explicit-
    # target behaviour. The full-run path (no --venue-id) skips anything
    # already done, so re-running after a 429 resumes from where it
    # actually stopped instead of redoing completed work.
    if not venue_id:
        before_count = len(venues)
        venues = [v for v in venues if v["venue_id"] not in already_embedded]
        skipped = before_count - len(venues)
        if skipped:
            print(f"Skipping {skipped} venue(s) already embedded from a previous run.")

    if not venues:
        print("No matching venues found.")
        return 0

    embedded_count = 0
    for i, venue in enumerate(venues):
        text_snapshot = _build_text_snapshot(venue)
        embedding = _embed_with_retry(text_snapshot)

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

        # No delay after the very last venue — nothing left to wait for.
        if i < len(venues) - 1:
            time.sleep(DELAY_SECONDS)

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