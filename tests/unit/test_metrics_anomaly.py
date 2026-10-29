"""The anomaly measurements against cases small enough to check by hand (feature 010)."""

from __future__ import annotations

import pytest

from caravan.metrics.anomaly import auc, detection, percentile


def test_perfect_separation_is_one() -> None:
    assert auc([0.1, 0.2, 0.3], [0.5, 0.9]) == 1.0


def test_reversed_separation_is_zero() -> None:
    assert auc([0.5, 0.9], [0.1, 0.2]) == 0.0


def test_ties_count_half() -> None:
    # Every abnormal score equals every normal one: no ordering, so one half.
    assert auc([1.0, 1.0], [1.0, 1.0, 1.0]) == 0.5


def test_a_hand_counted_case() -> None:
    # Pairs won by the abnormal side: 0.4 beats 0.1 and 0.3 (2); 0.2 beats 0.1 (1); 0.3 beats 0.1
    # and ties 0.3 (1.5). Of 3 x 2 = 6 pairs, 4.5.
    assert auc([0.1, 0.3], [0.4, 0.2, 0.3]) == pytest.approx(4.5 / 6)


@pytest.mark.parametrize(("normal", "abnormal"), [([], [1.0]), ([1.0], [])])
def test_an_empty_side_has_no_auc(normal: list[float], abnormal: list[float]) -> None:
    assert auc(normal, abnormal) is None


def test_percentile_interpolates_like_the_familiar_definition() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(values, 0) == 1.0
    assert percentile(values, 100) == 5.0
    assert percentile(values, 50) == 3.0
    assert percentile(values, 95) == pytest.approx(4.8)
    assert percentile([7.0], 95) == 7.0


def test_percentile_refuses_what_is_not_defined() -> None:
    with pytest.raises(ValueError):
        percentile([], 50)
    with pytest.raises(ValueError):
        percentile([1.0], 101)


def test_detection_counts_at_or_above_the_threshold() -> None:
    rates = detection([0.1, 0.5, 0.2, 0.3], [0.5, 0.6, 0.1], threshold=0.5)
    assert rates == {"true_positive_rate": 2 / 3, "false_alarm_rate": 1 / 4}
