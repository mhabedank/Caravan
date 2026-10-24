"""A split the data decides (feature 007, research R9, FR-017 to FR-019).

Pure arithmetic over labels and parts, so it runs on every Python in the matrix, like the split by
fractions it sits beside.
"""

from __future__ import annotations

import pytest

from caravan.data.windows import plan_split, plan_windows
from caravan.manifest.errors import RULE_SPLIT_EMPTY, RunRuleFailure

LABELS = ("a", "b")


def windows(spec: list[tuple[str, str]], size: int = 4) -> tuple[list[str], list[str]]:
    """Records for whole windows, each given as (label, part)."""
    labels, parts = [], []
    for label, part in spec:
        labels += [label] * size
        parts += [part] * size
    return labels, parts


def test_each_window_takes_the_part_its_records_name() -> None:
    labels, parts = windows([("a", "train"), ("b", "train"), ("a", "val"), ("b", "test")])
    plan = plan_windows(labels, 4, parts=parts)
    assert plan.parts == ("train", "train", "val", "test")
    split = plan_split(plan, None, stratified=False, seed=None, labels=LABELS, column="split")
    assert (split.train, split.val, split.test) == ((0, 1), (2,), (3,))
    assert split.source == "column:split"
    assert split.stratified is False
    assert split.seed is None
    assert split.per_label_counts == {
        "a": {"train": 1, "val": 1, "test": 0},
        "b": {"train": 1, "val": 0, "test": 1},
    }


def test_a_window_naming_two_parts_is_discarded_and_counted() -> None:
    labels, parts = windows([("a", "train"), ("a", "val"), ("b", "test")])
    parts[4:6] = ["test", "test"]  # the second window: half val, half test
    plan = plan_windows(labels, 4, parts=parts)
    assert plan.samples == 2
    assert plan.discarded_mixed_split == 1
    assert plan.discarded_mixed == 0


def test_a_window_mixed_both_ways_counts_as_mixed_by_label() -> None:
    labels, parts = windows([("a", "train"), ("a", "val"), ("b", "test")])
    labels[4:6] = ["b", "b"]
    parts[4:6] = ["test", "test"]
    plan = plan_windows(labels, 4, parts=parts)
    assert plan.discarded_mixed == 1
    assert plan.discarded_mixed_split == 0


def test_an_empty_part_is_refused_naming_the_column() -> None:
    labels, parts = windows([("a", "train"), ("b", "train"), ("a", "test")])
    plan = plan_windows(labels, 4, parts=parts)
    with pytest.raises(RunRuleFailure) as caught:
        plan_split(plan, None, stratified=False, seed=None, labels=LABELS, column="split")
    finding = caught.value.finding
    assert finding.rule == RULE_SPLIT_EMPTY
    assert finding.path == "dataset.split.column"
    assert "val" in finding.problem and "'split'" in finding.problem


def test_without_parts_nothing_changes() -> None:
    labels, _ = windows([("a", "train"), ("b", "train")])
    plan = plan_windows(labels, 4)
    assert plan.parts is None
    assert plan.discarded_mixed_split == 0
