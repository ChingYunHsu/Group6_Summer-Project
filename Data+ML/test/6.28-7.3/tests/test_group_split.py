"""SOP 8 — pure-function tests for assign_group_split (group-aware split).

Group-aware split guarantees no `prediction_group_id` leaks across
train/val/test — the core anti-leakage invariant of the ML pipeline.
Offline, no DB, deterministic via the fixed seed.
"""

from __future__ import annotations

import pandas as pd
import pytest

import ml_feature_pipeline as mfp


def _groups(n: int) -> pd.Series:
    return pd.Series([f"grp_{i}" for i in range(n)])


def test_split_ratio_is_approximately_70_15_15():
    splits = mfp.assign_group_split(_groups(100), seed=42)
    counts = splits.value_counts()
    # 70/15/15 with integer rounding
    assert counts["train"] == 70
    assert counts["val"] == 15
    assert counts["test"] == 15


def test_no_group_leaks_across_splits():
    """A prediction_group_id must appear in exactly one split."""
    groups = pd.Series(["A", "A", "B", "B", "C", "C", "D", "D", "E", "E",
                        "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"])
    splits = mfp.assign_group_split(groups, seed=42)

    # collect which split each group lands in
    group_to_split = {}
    for g, s in zip(groups, splits):
        if g in group_to_split:
            assert group_to_split[g] == s, f"group {g} appears in multiple splits"
        else:
            group_to_split[g] = s


def test_split_is_deterministic_for_same_seed():
    g = _groups(50)
    a = mfp.assign_group_split(g, seed=7)
    b = mfp.assign_group_split(g, seed=7)
    assert a.tolist() == b.tolist()


def test_split_only_contains_valid_labels():
    splits = mfp.assign_group_split(_groups(30), seed=42)
    assert set(splits.unique()).issubset({"train", "val", "test"})


def test_split_handles_na_groups():
    groups = pd.Series(["A", "B", None, "C", None, "D"] * 3)
    splits = mfp.assign_group_split(groups, seed=42)
    # NA groups must not crash; their split label is whatever map() yields (test)
    assert len(splits) == len(groups)


def test_every_group_assigned_to_a_split():
    groups = pd.Series(["x", "y", "z", "w", "v", "u", "t", "s", "r", "q"])
    splits = mfp.assign_group_split(groups, seed=1)
    assert splits.notna().all()
