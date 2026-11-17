"""User story 3 of feature 014: every kind of output gets windows (FR-005 to 008, SC-001, SC-002).

Measured on the ``soc`` fixture (a continuous number) and the ``bursts`` fixture (20-row attack
bursts every 200 normal frames), the two shapes the review found the old rule could not serve.
"""

from __future__ import annotations

import pytest

from caravan.data.windows import plan_windows, recordings_from
from caravan.manifest.errors import RULE_WINDOW_COLUMN_OR_VALUE, RunRuleFailure
from tests.support import BURSTS_DATASET, SOC_DATASET
from tests.unit.test_windows_recordings import read_labels


def soc_plan(rule):
    labels, files = read_labels(SOC_DATASET, "soc")
    labels = [repr(float(value)) for value in labels]  # as the reader writes a number output
    return plan_windows(labels, 32, recordings=recordings_from(files), rule=rule), labels, files


def possible(files, window: int) -> int:
    return sum(rows // window for _, rows in files)


def test_a_continuous_number_keeps_its_windows_with_the_newest_row() -> None:
    plan, labels, files = soc_plan("last")
    assert plan.samples >= 0.9 * possible(files, 32)  # SC-001; before feature 014: none
    assert plan.samples == possible(files, 32)
    first = plan.kept[0]
    assert plan.labels[0] == labels[first + 31]


def test_the_mean_rule_averages_the_window() -> None:
    plan, labels, _ = soc_plan("mean")
    start = plan.kept[1]
    expected = sum(float(value) for value in labels[start : start + 32]) / 32
    assert float(plan.labels[1]) == pytest.approx(expected)


def test_all_equal_keeps_none_of_a_continuous_number_and_says_why() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        soc_plan("all_equal")
    assert "disagreed about the label" in caught.value.finding.problem


def bursts():
    labels, files = read_labels(BURSTS_DATASET, "label")
    return labels, recordings_from(files)


def test_short_bursts_vanish_under_all_equal_as_the_review_measured() -> None:
    labels, recordings = bursts()
    plan = plan_windows(labels, 64, recordings=recordings)
    assert "dos" not in plan.labels
    assert plan.discarded_mixed > 0


def test_the_any_rule_keeps_a_burst_window_for_every_burst() -> None:
    labels, recordings = bursts()
    plan = plan_windows(labels, 64, recordings=recordings, rule={"any": "dos"})
    burst_starts = range(100, len(labels), 200)
    for start in burst_starts:
        covering = [
            s
            for s, label in zip(plan.kept, plan.labels, strict=True)
            if label == "dos" and s < start + 20 and start < s + 64
        ]
        assert covering, f"no dos window covers the burst at row {start}"  # SC-002


def test_the_any_rule_falls_back_to_all_equal_for_windows_without_the_value() -> None:
    labels = ["normal"] * 10 + ["idle"] * 10 + ["dos"] * 5 + ["normal"] * 15
    plan = plan_windows(labels, 10, rule={"any": "dos"})
    # [0:10] normal, [10:20] idle, [20:30] holds dos → dos, [30:40] normal.
    assert plan.labels == ("normal", "idle", "dos", "normal")
    # A window mixed of other labels, without the value, is dropped as all_equal would drop it.
    labels = ["normal"] * 5 + ["idle"] * 5 + ["normal"] * 10 + ["dos"] * 10
    mixed = plan_windows(labels, 10, rule={"any": "dos"})
    assert mixed.labels == ("normal", "dos") and mixed.discarded_mixed == 1


def test_the_any_rule_refuses_a_value_the_column_never_holds() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        plan_windows(["normal", "dos"] * 20, 10, rule={"any": "nope"})
    finding = caught.value.finding
    assert finding.rule == RULE_WINDOW_COLUMN_OR_VALUE
    assert finding.accepted == ("dos", "normal")


def test_majority_drops_a_tie_and_counts_it() -> None:
    labels = ["a", "a", "b", "b", "a", "a", "a", "b"]  # a tie, then a majority of a
    plan = plan_windows(labels, 4, rule="majority")
    assert plan.labels == ("a",) and plan.discarded_tied == 1


def test_the_any_rule_makes_one_abnormal_row_an_abnormal_window() -> None:
    labels = ["normal"] * 9 + ["fault"] + ["normal"] * 10
    plan = plan_windows(labels, 10, rule={"any": "fault"})
    assert plan.labels == ("fault", "normal")
