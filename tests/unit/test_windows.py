"""Windowing and splitting: the two rules that decide what the model is trained on.

Both live in the core and use no array library, so these tests run on every Python in the matrix
rather than only where the training extra can be installed. That is the point of putting the rules
there (research R5, R6).
"""

from __future__ import annotations

import math
import random

import pytest

from caravan.data.windows import SPLIT_NAMES, plan_split, plan_windows
from caravan.manifest.errors import (
    RULE_DATASET_NO_SAMPLES,
    RULE_SPLIT_EMPTY,
    RunRuleFailure,
)

FRACTIONS = {"train": 0.7, "val": 0.15, "test": 0.15}


def labels_for(pattern: list[tuple[str, int]]) -> list[str]:
    """A record sequence written as ``[(label, count), ...]``."""
    out: list[str] = []
    for label, count in pattern:
        out.extend([label] * count)
    return out


def test_windows_are_consecutive_and_do_not_overlap() -> None:
    plan = plan_windows(labels_for([("normal", 12)]), window=4)
    assert plan.kept == (0, 4, 8)
    assert plan.labels == ("normal", "normal", "normal")
    assert plan.discarded_mixed == 0
    assert plan.dropped_remainder == 0


def test_the_trailing_remainder_is_dropped_and_counted() -> None:
    plan = plan_windows(labels_for([("normal", 10)]), window=4)
    assert plan.kept == (0, 4)
    assert plan.dropped_remainder == 2


def test_a_window_whose_records_disagree_is_discarded_and_counted() -> None:
    # Two pure windows around one that straddles the change of label. The straddling window is
    # never given a label: majority voting has no answer for a tie, and the last record's label
    # mislabels the tail of every burst (FR-025).
    plan = plan_windows(labels_for([("normal", 6), ("dos", 6)]), window=4)
    assert plan.kept == (0, 8)
    assert plan.labels == ("normal", "dos")
    assert plan.discarded_mixed == 1


def test_without_a_window_one_record_is_one_sample() -> None:
    # FR-024's second sentence. No manifest can reach this while the only registered template
    # requires a window (CF-6), so it is proven directly against the rule.
    plan = plan_windows(labels_for([("normal", 2), ("dos", 1)]), window=None)
    assert plan.kept == (0, 1, 2)
    assert plan.labels == ("normal", "normal", "dos")
    assert plan.window is None


def test_ds_6_when_fewer_records_than_one_window() -> None:
    with pytest.raises(RunRuleFailure) as error:
        plan_windows(labels_for([("normal", 10)]), window=64)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_NO_SAMPLES
    assert "10 records" in finding.problem and "64" in finding.problem


def test_ds_6_when_every_window_straddles_a_change_of_label() -> None:
    with pytest.raises(RunRuleFailure) as error:
        plan_windows(labels_for([("normal", 2), ("dos", 2), ("normal", 2), ("dos", 2)]), window=4)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_NO_SAMPLES
    assert finding.found["windows_discarded_mixed"] == 2
    assert finding.found["windows_examined"] == 2


def test_ds_6_on_an_empty_sequence() -> None:
    with pytest.raises(RunRuleFailure) as error:
        plan_windows([], window=None)
    assert error.value.finding.rule == RULE_DATASET_NO_SAMPLES


# --- the split ---------------------------------------------------------------------------------


def expected_cut(indices: list[int], seed: int) -> dict[str, list[int]]:
    """The procedure of ``contracts/dataset.md``, written out independently.

    Deliberately a second implementation rather than a call into the first: it is how a change to
    the procedure gets noticed instead of being blessed by the test that was changed with it.
    """
    order = sorted(indices)
    random.Random(seed).shuffle(order)
    sizes = {name: math.floor(len(order) * FRACTIONS[name]) for name in SPLIT_NAMES}
    sizes["train"] += len(order) - sum(sizes.values())  # the largest fraction takes the leftover
    out: dict[str, list[int]] = {}
    cursor = 0
    for name in SPLIT_NAMES:
        out[name] = sorted(order[cursor : cursor + sizes[name]])
        cursor += sizes[name]
    return out


def test_the_split_follows_the_written_procedure_including_the_leftover() -> None:
    plan = plan_windows(labels_for([("normal", 40)]), window=4)  # 10 samples, one label
    split = plan_split(plan, FRACTIONS, stratified=True, seed=1, labels=["normal"])
    expected = expected_cut(list(range(10)), seed=1)

    assert split.counts == {"train": 8, "val": 1, "test": 1}
    assert list(split.train) == expected["train"]
    assert list(split.val) == expected["val"]
    assert list(split.test) == expected["test"]


def test_the_parts_are_disjoint_and_complete() -> None:
    plan = plan_windows(labels_for([("normal", 40), ("dos", 40)]), window=4)
    split = plan_split(plan, FRACTIONS, stratified=True, seed=7, labels=["normal", "dos"])
    seen = list(split.train) + list(split.val) + list(split.test)
    assert sorted(seen) == list(range(plan.samples))
    assert len(set(seen)) == len(seen)


def test_the_same_seed_gives_the_same_split_and_another_seed_does_not() -> None:
    plan = plan_windows(labels_for([("normal", 80)]), window=4)
    first = plan_split(plan, FRACTIONS, stratified=True, seed=42, labels=["normal"])
    again = plan_split(plan, FRACTIONS, stratified=True, seed=42, labels=["normal"])
    other = plan_split(plan, FRACTIONS, stratified=True, seed=43, labels=["normal"])
    assert first.train == again.train
    assert first.train != other.train


def test_stratified_splits_each_label_separately() -> None:
    plan = plan_windows(labels_for([("normal", 40), ("dos", 40)]), window=4)
    split = plan_split(plan, FRACTIONS, stratified=True, seed=3, labels=["normal", "dos"])
    assert split.per_label_counts == {
        "normal": {"train": 8, "val": 1, "test": 1},
        "dos": {"train": 8, "val": 1, "test": 1},
    }


def test_an_unstratified_split_still_reports_per_label_counts() -> None:
    plan = plan_windows(labels_for([("normal", 40), ("dos", 40)]), window=4)
    split = plan_split(plan, FRACTIONS, stratified=False, seed=3, labels=["normal", "dos"])
    # 20 samples in one pool floor to 14/3/3, where two stratified pools of 10 floor to 8/1/1
    # each and so give 16/2/2. Flooring per pool is why stratifying changes the totals.
    assert split.counts == {"train": 14, "val": 3, "test": 3}
    totals = {
        label: sum(split.per_label_counts[label][name] for name in SPLIT_NAMES)
        for label in ("normal", "dos")
    }
    assert totals == {"normal": 10, "dos": 10}


def test_ds_8_when_a_part_comes_out_empty() -> None:
    # Four samples at 0.15 floor to zero. The manifest already forbids a zero fraction, so an
    # empty part means the data is too small for the manifest — which is the author's to fix.
    plan = plan_windows(labels_for([("normal", 16)]), window=4)
    with pytest.raises(RunRuleFailure) as error:
        plan_split(plan, FRACTIONS, stratified=True, seed=1, labels=["normal"])
    finding = error.value.finding
    assert finding.rule == RULE_SPLIT_EMPTY
    assert finding.path == "preprocessing.split.probabilities"
    assert "4 samples" in finding.problem


def test_ds_8_names_the_label_that_ran_out() -> None:
    # One rare class among a common one: the split as a whole is fine, the rare label is not, and
    # a message that only said "the test split is empty" would send the author to the wrong place.
    plan = plan_windows(labels_for([("normal", 400), ("dos", 16)]), window=4)
    with pytest.raises(RunRuleFailure) as error:
        plan_split(plan, FRACTIONS, stratified=True, seed=1, labels=["normal", "dos"])
    assert error.value.finding.rule == RULE_SPLIT_EMPTY
    assert "'dos'" in error.value.finding.problem
