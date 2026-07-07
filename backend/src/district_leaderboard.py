"""District aggregation and leaderboard sorting.

Placeholder scaffolding: the real busyness/safety cost function is still
being finalized elsewhere. These are deliberately simple, pure functions
(no DB, no Flask) so they can be swapped for the frozen formula later
without touching call sites. Until then they exist purely so the
boundary/stress test suite in tests/test_district_leaderboard_stress.py
has something concrete to hammer for divide-by-zero and out-of-bounds
failures.
"""

from typing import Any


def aggregate_district_stats(venues: list[dict]) -> dict[str, dict[str, Any]]:
    """Group venues by `borough` and compute per-district averages.

    Returns {} for no input. A district with venues that all have a
    missing/None busyness_percent reports avg_busyness_percent as None
    rather than dividing by zero.
    """
    buckets: dict[str, list[dict]] = {}
    for venue in venues or []:
        district = venue.get("borough") or "Unknown"
        buckets.setdefault(district, []).append(venue)

    stats: dict[str, dict[str, Any]] = {}
    for district, district_venues in buckets.items():
        percents = [
            v["busyness_percent"]
            for v in district_venues
            if isinstance(v.get("busyness_percent"), (int, float))
        ]
        stats[district] = {
            "venue_count": len(district_venues),
            "avg_busyness_percent": (sum(percents) / len(percents)) if percents else None,
            "open_now_count": sum(1 for v in district_venues if v.get("open_now")),
        }
    return stats


def rank_leaderboard(venues: list[dict], limit: int | None = None) -> list[dict]:
    """Rank venues ascending by busyness_percent (quietest first); venues
    missing a score sort last, ties broken by venue_id for determinism.

    Returns [] for no input. `limit` is clamped to the available length so
    requesting more entries than exist never raises IndexError.
    """
    if not venues:
        return []

    def cost(venue: dict):
        percent = venue.get("busyness_percent")
        has_score = isinstance(percent, (int, float))
        return (0 if has_score else 1, percent if has_score else 0, venue.get("venue_id") or "")

    ranked = sorted(venues, key=cost)

    effective_limit = len(ranked) if limit is None else max(0, min(limit, len(ranked)))
    top = ranked[:effective_limit]

    return [
        {"rank": index + 1, "venue_id": venue.get("venue_id"), "busyness_percent": venue.get("busyness_percent")}
        for index, venue in enumerate(top)
    ]
