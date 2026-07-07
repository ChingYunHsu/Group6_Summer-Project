"""Aggressive boundary/value stress tests for district_leaderboard.py.

district_leaderboard.py is placeholder scaffolding standing in for the
real district-aggregation/leaderboard cost function until it's frozen
elsewhere (see module docstring). These tests exist to prove the
*shape* of both functions never throws on degenerate input — empty
input, all-missing scores, single-item, duplicate/tied scores, and a
large-N stress run — so whatever the real formula ends up being can be
swapped in against an already-hardened contract.
"""

import pytest

from district_leaderboard import aggregate_district_stats, rank_leaderboard


# ── aggregate_district_stats ────────────────────────────────────────────

def test_aggregate_empty_input_returns_empty_dict():
    assert aggregate_district_stats([]) == {}


def test_aggregate_none_input_returns_empty_dict():
    assert aggregate_district_stats(None) == {}


def test_aggregate_single_venue_single_district():
    stats = aggregate_district_stats([{"borough": "Manhattan", "busyness_percent": 40, "open_now": True}])
    assert stats["Manhattan"]["venue_count"] == 1
    assert stats["Manhattan"]["avg_busyness_percent"] == 40
    assert stats["Manhattan"]["open_now_count"] == 1


def test_aggregate_missing_borough_buckets_as_unknown():
    stats = aggregate_district_stats([{"busyness_percent": 10}])
    assert "Unknown" in stats
    assert stats["Unknown"]["venue_count"] == 1


def test_aggregate_all_venues_missing_busyness_percent_avoids_div_by_zero():
    stats = aggregate_district_stats(
        [
            {"borough": "Queens"},
            {"borough": "Queens", "busyness_percent": None},
        ]
    )
    assert stats["Queens"]["venue_count"] == 2
    assert stats["Queens"]["avg_busyness_percent"] is None  # never 0/0


def test_aggregate_mixed_present_and_missing_scores_averages_only_present():
    stats = aggregate_district_stats(
        [
            {"borough": "Brooklyn", "busyness_percent": 20},
            {"borough": "Brooklyn", "busyness_percent": None},
            {"borough": "Brooklyn", "busyness_percent": 60},
        ]
    )
    assert stats["Brooklyn"]["venue_count"] == 3
    assert stats["Brooklyn"]["avg_busyness_percent"] == 40  # (20+60)/2, not /3


def test_aggregate_non_numeric_busyness_percent_is_ignored_not_crashed():
    stats = aggregate_district_stats([{"borough": "Bronx", "busyness_percent": "not-a-number"}])
    assert stats["Bronx"]["avg_busyness_percent"] is None


def test_aggregate_zero_busyness_percent_is_not_treated_as_missing():
    # 0 is falsy but a legitimate score — must not be filtered out like None.
    stats = aggregate_district_stats([{"borough": "Manhattan", "busyness_percent": 0}])
    assert stats["Manhattan"]["avg_busyness_percent"] == 0


def test_aggregate_multiple_districts_are_independent():
    stats = aggregate_district_stats(
        [
            {"borough": "Manhattan", "busyness_percent": 100},
            {"borough": "Queens", "busyness_percent": 0},
        ]
    )
    assert stats["Manhattan"]["avg_busyness_percent"] == 100
    assert stats["Queens"]["avg_busyness_percent"] == 0
    assert len(stats) == 2


def test_aggregate_large_n_stress_does_not_raise():
    venues = [
        {"borough": f"district_{i % 7}", "busyness_percent": i % 101, "open_now": i % 2 == 0}
        for i in range(20_000)
    ]
    stats = aggregate_district_stats(venues)
    assert len(stats) == 7
    assert sum(d["venue_count"] for d in stats.values()) == 20_000


# ── rank_leaderboard ─────────────────────────────────────────────────────

def test_leaderboard_empty_input_returns_empty_list():
    assert rank_leaderboard([]) == []


def test_leaderboard_single_venue():
    result = rank_leaderboard([{"venue_id": "v1", "busyness_percent": 50}])
    assert result == [{"rank": 1, "venue_id": "v1", "busyness_percent": 50}]


def test_leaderboard_sorts_ascending_by_busyness():
    result = rank_leaderboard(
        [
            {"venue_id": "busy", "busyness_percent": 90},
            {"venue_id": "quiet", "busyness_percent": 5},
            {"venue_id": "mid", "busyness_percent": 50},
        ]
    )
    assert [row["venue_id"] for row in result] == ["quiet", "mid", "busy"]
    assert [row["rank"] for row in result] == [1, 2, 3]


def test_leaderboard_missing_scores_sort_last_not_crashed():
    result = rank_leaderboard(
        [
            {"venue_id": "no_score"},
            {"venue_id": "has_score", "busyness_percent": 10},
        ]
    )
    assert [row["venue_id"] for row in result] == ["has_score", "no_score"]


def test_leaderboard_all_missing_scores_still_returns_all_ranked():
    result = rank_leaderboard([{"venue_id": "a"}, {"venue_id": "b"}, {"venue_id": "c"}])
    assert len(result) == 3
    assert [row["rank"] for row in result] == [1, 2, 3]


def test_leaderboard_tied_scores_broken_deterministically_by_venue_id():
    result = rank_leaderboard(
        [
            {"venue_id": "z", "busyness_percent": 30},
            {"venue_id": "a", "busyness_percent": 30},
        ]
    )
    assert [row["venue_id"] for row in result] == ["a", "z"]


def test_leaderboard_limit_beyond_length_does_not_raise_index_error():
    result = rank_leaderboard([{"venue_id": "only_one", "busyness_percent": 1}], limit=1000)
    assert len(result) == 1


def test_leaderboard_limit_zero_returns_empty_list():
    result = rank_leaderboard([{"venue_id": "x", "busyness_percent": 1}], limit=0)
    assert result == []


def test_leaderboard_negative_limit_clamped_to_zero_not_negative_slice():
    # A naive venues[:limit] with a negative limit would silently drop the
    # tail instead of raising — assert the clamp keeps behavior sane.
    result = rank_leaderboard(
        [{"venue_id": "x", "busyness_percent": 1}, {"venue_id": "y", "busyness_percent": 2}],
        limit=-5,
    )
    assert result == []


def test_leaderboard_extreme_values_do_not_raise():
    result = rank_leaderboard(
        [
            {"venue_id": "inf", "busyness_percent": float("inf")},
            {"venue_id": "neg_inf", "busyness_percent": float("-inf")},
            {"venue_id": "zero", "busyness_percent": 0},
        ]
    )
    assert [row["venue_id"] for row in result] == ["neg_inf", "zero", "inf"]


def test_leaderboard_large_n_stress_does_not_raise_and_stays_sorted():
    venues = [{"venue_id": f"v{i}", "busyness_percent": (i * 37) % 1000} for i in range(20_000)]
    result = rank_leaderboard(venues, limit=50)

    assert len(result) == 50
    scores = [row["busyness_percent"] for row in result]
    assert scores == sorted(scores)


@pytest.mark.parametrize("limit", [None, 0, 1, -1, 10_000])
def test_leaderboard_never_raises_across_limit_boundary_values(limit):
    venues = [{"venue_id": f"v{i}", "busyness_percent": i} for i in range(5)]
    result = rank_leaderboard(venues, limit=limit)
    assert isinstance(result, list)
