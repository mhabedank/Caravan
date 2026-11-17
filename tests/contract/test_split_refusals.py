"""The refusals of the splits by recording, group and block (feature 014: DS-18, DS-19, FR-015).

Each names the counts that explain it, so an author can see what is missing rather than only that
something is.
"""

from __future__ import annotations

import pytest

from caravan.data.windows import plan_windows, recordings_from, split_for
from caravan.manifest.errors import (
    RULE_CLASS_NOT_IN_EVERY_PART,
    RULE_TOO_FEW_GROUPS,
    RunRuleFailure,
)

SPEC = {"probabilities": [0.7, 0.15, 0.15], "column": None}


def spec(kind: str, **more) -> dict:
    return {**SPEC, "type": kind, **more}


def refusal(plan, kind: str, labels=("a", "b"), **more):
    with pytest.raises(RunRuleFailure) as caught:
        split_for(plan, spec(kind, **more), seed=42, labels=labels)
    return caught.value.finding


def test_two_recordings_cannot_fill_three_parts() -> None:
    labels = ["a" if (i // 100) % 2 == 0 else "b" for i in range(800)]
    plan = plan_windows(labels, 50, recordings=recordings_from([("x.csv", 400), ("y.csv", 400)]))
    finding = refusal(plan, "recording")
    assert finding.rule == RULE_TOO_FEW_GROUPS
    assert "2" in finding.problem and "3" in finding.problem and "blocked" in finding.problem
    assert finding.found == {"groups": 2, "parts": 3}


def test_the_derived_default_with_two_recordings_blocks_instead_of_refusing() -> None:
    labels = ["a" if (i // 100) % 2 == 0 else "b" for i in range(800)]
    plan = plan_windows(labels, 10, recordings=recordings_from([("x.csv", 400), ("y.csv", 400)]))
    split = split_for(plan, spec("derived"), seed=42, labels=("a", "b"))
    assert split.type == "blocked"


def test_a_class_held_by_one_recording_cannot_reach_every_part() -> None:
    # Five recordings of a, one of b: no assignment puts b in training, validation and test.
    files = [(f"r{i}.csv", 100) for i in range(6)]
    labels = ["a"] * 500 + ["b"] * 100
    plan = plan_windows(labels, 20, recordings=recordings_from(files))
    finding = refusal(plan, "recording")
    assert finding.rule == RULE_CLASS_NOT_IN_EVERY_PART
    assert finding.found["windows_per_class_per_group"]["r5.csv"] == {"b": 5}


def test_a_class_in_too_short_a_stretch_cannot_be_blocked_into_three_parts() -> None:
    # One long stretch of a, and b for only two windows: one block (a block holds at least three
    # windows, so the purge at its edge cannot take most of it).
    labels = ["a"] * 1000 + ["b"] * 40
    plan = plan_windows(labels, 20)
    finding = refusal(plan, "blocked")
    assert finding.rule == RULE_CLASS_NOT_IN_EVERY_PART
    assert finding.found == {"class": "b", "windows": 2, "blocks": 1}
    assert "'b'" in finding.problem


def test_a_number_output_with_too_few_blocks_is_refused_as_too_few_groups() -> None:
    labels = [repr(float(i)) for i in range(40)]
    plan = plan_windows(labels, 20, rule="last")
    finding = refusal(plan, "blocked", labels=())
    assert finding.rule == RULE_TOO_FEW_GROUPS


def test_the_fixed_split_keeps_working_and_respects_recordings() -> None:
    labels = ["a"] * 300
    parts = ["train"] * 150 + ["val"] * 75 + ["test"] * 75
    files = [("p.csv", 150), ("q.csv", 150)]
    plan = plan_windows(labels, 30, parts=parts, recordings=recordings_from(files))
    split = split_for(plan, {"type": "fixed", "column": "part"}, seed=1, labels=("a",))
    assert split.type == "fixed" and split.counts == {"train": 5, "val": 2, "test": 2}
    # No window crosses from p.csv into q.csv at row 150.
    assert all(start + 30 <= 150 or start >= 150 for start in plan.kept)
