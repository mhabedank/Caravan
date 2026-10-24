"""Mean absolute error, mean squared error, its root and R², for a ``number`` output (feature 008).

Core module, standard library only, like the rest of what decides a verdict: the int8 gate of a
``number`` output judges the increase of the mean absolute error, so the arithmetic is tested on
every Python and readable without a framework.

R² compares the error with the spread of the truth. When the truth is constant it has no spread,
and R² is undefined: it is reported as ``None``, never as 0 or 1, because either would be a number
nobody measured.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def regression_metrics(truth: Sequence[float], predicted: Sequence[float]) -> dict[str, float | None]:
    """MAE, MSE, RMSE and R² of one set of predictions, in the column's unit."""
    if len(truth) != len(predicted):
        raise ValueError("the truth and the predictions differ in length")
    if not truth:
        raise ValueError("a split with no samples cannot be measured")
    count = len(truth)
    errors = [float(guess) - float(actual) for actual, guess in zip(truth, predicted, strict=True)]
    mae = sum(abs(error) for error in errors) / count
    mse = sum(error * error for error in errors) / count
    mean = sum(float(value) for value in truth) / count
    spread = sum((float(value) - mean) ** 2 for value in truth)
    r2 = None if spread == 0.0 else 1.0 - (mse * count) / spread
    return {"mae": mae, "mse": mse, "rmse": math.sqrt(mse), "r2": r2}
