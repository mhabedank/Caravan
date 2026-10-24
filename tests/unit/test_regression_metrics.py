"""MAE, MSE, RMSE and R² on hand-computed cases (feature 008, ``caravan.metrics.regression``)."""

from __future__ import annotations

import pytest

from caravan.metrics.regression import regression_metrics


def test_a_hand_computed_case() -> None:
    # Errors 1, -1, 2: |e| mean 4/3, e² mean 2, RMSE √2. Truth 1, 2, 3 has spread 2.
    metrics = regression_metrics([1.0, 2.0, 3.0], [2.0, 1.0, 5.0])
    assert metrics["mae"] == pytest.approx(4 / 3)
    assert metrics["mse"] == pytest.approx(2.0)
    assert metrics["rmse"] == pytest.approx(2.0**0.5)
    assert metrics["r2"] == pytest.approx(1 - 6 / 2)


def test_a_perfect_prediction() -> None:
    metrics = regression_metrics([1.0, 5.0], [1.0, 5.0])
    assert metrics == {"mae": 0.0, "mse": 0.0, "rmse": 0.0, "r2": 1.0}


def test_r2_of_a_constant_truth_is_undefined_and_said_so() -> None:
    # The truth has no spread, so R² would divide by zero: reported as None, never as 0 or 1.
    metrics = regression_metrics([2.0, 2.0, 2.0], [1.0, 2.0, 3.0])
    assert metrics["r2"] is None
    assert metrics["mae"] == pytest.approx(2 / 3)


def test_empty_or_unequal_inputs_are_refused() -> None:
    with pytest.raises(ValueError, match="no samples"):
        regression_metrics([], [])
    with pytest.raises(ValueError, match="length"):
        regression_metrics([1.0], [1.0, 2.0])
