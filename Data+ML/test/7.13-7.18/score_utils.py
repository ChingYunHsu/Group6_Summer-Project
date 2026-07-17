"""score_utils.py — Shared score utilities for forecast-v2.

Consolidates clamp_score and score_to_level that were duplicated across 3 files.
"""

from __future__ import annotations

import numpy as np

# ── Constants ─────────────────────────────────────────────────────────────────
SCORE_CLAMP = (0, 100)
BUSY_LEVEL_THRESHOLDS: list[tuple[int, int, str]] = [
    (0, 30, "quiet"),
    (30, 70, "moderate"),
    (70, 101, "busy"),
]
BUSY_LABELS = ("quiet", "moderate", "busy")


def clamp_score(value: float) -> int:
    """Round + clamp to [0, 100]."""
    return max(SCORE_CLAMP[0], min(SCORE_CLAMP[1], round(float(value))))


def score_to_level(score: float, no_data_level: str | None = None) -> str:
    """Map 0-100 score → quiet/moderate/busy.

    Args:
        score: 0-100 busyness score.
        no_data_level: If provided and score is NaN/None, return this value
                       instead of the default threshold-based level.
    """
    import numpy as np
    if no_data_level is not None and (score is None or (isinstance(score, float) and np.isnan(score))):
        return no_data_level
    for lo, hi, label in BUSY_LEVEL_THRESHOLDS:
        if lo <= score < hi:
            return label
    return "busy"
