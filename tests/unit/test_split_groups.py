"""User story 2 of feature 014: a test score that measures the model (FR-009 to 014, 018; SC-004).

The splits by recording, by group and by block assign whole groups of windows. Measured here on the
review's leakage example and on the six-recording fixture; pure arithmetic, every Python.
"""

from __future__ import annotations

import pytest

from caravan.data.windows import SPLIT_NAMES, plan_windows, recordings_from, split_for
from tests.support import RECORDINGS_DATASET, leakage_example
from tests.unit.test_windows_recordings import read_labels

SPEC = {"probabilities": [0.7, 0.15, 0.15], "column": None}


def spec(kind: str, **more) -> dict:
    return {**SPEC, "type": kind, **more}


def neighbours_in_training(plan, split) -> int:
    """Test windows with a training window directly beside them in the same recording."""
    train = {(plan.recording_of[p], plan.kept[p]) for p in split.train}
    step = plan.step
    return sum(
        1
        for p in split.test
        if (plan.recording_of[p], plan.kept[p] - step) in train
        or (plan.recording_of[p], plan.kept[p] + step) in train
    )


def shared_rows(plan, split) -> int:
    """Rows that belong to windows of two different parts (FR-018)."""
    owner: dict[int, str] = {}
    shared = 0
    for name in SPLIT_NAMES:
        for p in split.indices(name):
            for row in range(plan.kept[p], plan.kept[p] + plan.length):
                if owner.setdefault(row, name) != name:
                    shared += 1
    return shared


# --- the review's leakage example --------------------------------------------------------------


def test_a_random_split_on_the_review_example_leaks_as_the_review_measured() -> None:
    labels = leakage_example()
    plan = plan_windows(labels, 64)
    split = split_for(plan, spec("random"), seed=42, labels=("a", "b"))
    assert split.counts["test"] == 15
    assert neighbours_in_training(plan, split) >= 10  # the review counted 13 of 15


def test_the_derived_default_on_one_recording_is_blocked_and_does_not_leak() -> None:
    labels = leakage_example()
    plan = plan_windows(labels, 64)
    split = split_for(plan, spec("derived"), seed=42, labels=("a", "b"))
    assert split.type == "blocked" and split.derived
    assert neighbours_in_training(plan, split) == 0  # SC-004: at most 1 in 10; here none
    assert split.purged > 0
    for label in ("a", "b"):
        assert all(split.per_label_counts[label][name] > 0 for name in SPLIT_NAMES)
    assert shared_rows(plan, split) == 0


def test_the_blocked_split_is_reproducible_from_its_seed() -> None:
    labels = leakage_example()
    plan = plan_windows(labels, 64)
    first = split_for(plan, spec("blocked"), seed=7, labels=("a", "b"))
    second = split_for(plan, spec("blocked"), seed=7, labels=("a", "b"))
    assert first == second
    assert first.assignment["test"] and all(
        name.startswith("records[") for name in first.assignment["test"]
    )


# --- by recording -------------------------------------------------------------------------------


def recordings_plan(**more):
    labels, files = read_labels(RECORDINGS_DATASET, "label")
    return plan_windows(labels, 64, recordings=recordings_from(files), **more)


def test_the_derived_default_with_six_recordings_is_by_recording() -> None:
    plan = recordings_plan(rule="last")
    split = split_for(plan, spec("derived"), seed=42, labels=("idle", "move"))
    assert split.type == "recording" and split.derived
    owner: dict[int, str] = {}
    for name in SPLIT_NAMES:
        for p in split.indices(name):
            assert owner.setdefault(plan.recording_of[p], name) == name
    assert sorted(len(files) for files in split.assignment.values()) == [1, 1, 4]
    assert neighbours_in_training(plan, split) == 0
    assert split.purged == 0


def test_the_same_seed_gives_the_same_assignment_and_the_shares_add_up() -> None:
    plan = recordings_plan(rule="last")
    first = split_for(plan, spec("recording"), seed=3, labels=("idle", "move"))
    second = split_for(plan, spec("recording"), seed=3, labels=("idle", "move"))
    assert first.assignment == second.assignment
    assert first.seed >= 3
    assert abs(sum(first.shares.values()) - 1) < 1e-3


# --- by group -----------------------------------------------------------------------------------


def test_a_group_split_keeps_every_value_together_even_when_it_returns() -> None:
    groups = ["v1"] * 200 + ["v2"] * 200 + ["v3"] * 200 + ["v1"] * 200 + ["v4"] * 200
    labels = ["a" if (i // 50) % 2 == 0 else "b" for i in range(1000)]
    plan = plan_windows(labels, 25, groups=groups)
    split = split_for(plan, spec("group", column="vehicle"), seed=1, labels=("a", "b"))
    assert split.type == "group" and split.source == "group:vehicle"
    owner: dict[str, str] = {}
    for name in SPLIT_NAMES:
        for p in split.indices(name):
            assert owner.setdefault(plan.groups[p], name) == name


def test_a_window_spanning_two_groups_is_dropped_and_counted() -> None:
    groups = ["g1"] * 30 + ["g2"] * 30 + ["g3"] * 30
    plan = plan_windows(["a"] * 90, 20, groups=groups)
    # Windows start at 0, 20, 40 and 60; the one at 20 holds rows of g1 and g2.
    assert plan.discarded_mixed_split == 1
    assert plan.kept == (0, 40, 60)


@pytest.mark.parametrize("kind", ["recording", "group", "blocked"])
def test_no_row_is_shared_between_parts_with_overlapping_windows(kind) -> None:
    labels = ["a" if (i // 120) % 2 == 0 else "b" for i in range(2400)]
    groups = [f"g{i // 400}" for i in range(2400)]
    files = [(f"f{i}.csv", 400) for i in range(6)]
    plan = plan_windows(labels, 40, stride=10, recordings=recordings_from(files), groups=groups)
    split = split_for(plan, spec(kind, column="g"), seed=5, labels=("a", "b"))
    assert shared_rows(plan, split) == 0
