"""How well a score separates normal from abnormal, and where to draw the line (feature 010).

Standard library only, so the measurements an anomaly gate is judged by run on every Python in the
matrix and in the core (Principle XII). Three functions, each the textbook definition:

* the area under the ROC curve in its Mann-Whitney form — the probability that a randomly drawn
  abnormal window scores higher than a randomly drawn normal one, ties counting half — which is the
  measure of MLPerf Tiny's anomaly task and of DCASE Task 2 (research R10);
* a percentile by linear interpolation between the closest ranks, the definition numpy uses by
  default, so the documented threshold rule is the familiar one;
* the detection rates at a threshold, with "abnormal" meaning a score at or above it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def auc(normal: Sequence[float], abnormal: Sequence[float]) -> float | None:
    """The area under the ROC curve, abnormal as the positive class; ``None`` with a side empty.

    ``None`` rather than 0.5 or an exception: an AUC over one class is not a number that could be
    within or outside a budget, and the gate must be able to say "cannot decide" (Principle V).
    """
    if not normal or not abnormal:
        return None
    pooled = sorted(
        [(float(value), 0) for value in normal] + [(float(value), 1) for value in abnormal]
    )
    rank_sum = 0.0
    position = 0
    while position < len(pooled):
        end = position
        while end + 1 < len(pooled) and pooled[end + 1][0] == pooled[position][0]:
            end += 1
        # Ranks are 1-based; a run of ties shares the average of the ranks it spans.
        shared = (position + 1 + end + 1) / 2
        rank_sum += shared * sum(kind for _, kind in pooled[position : end + 1])
        position = end + 1
    positives, negatives = len(abnormal), len(normal)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def percentile(values: Sequence[float], percent: float) -> float:
    """The ``percent``-th percentile, interpolating linearly between the closest ranks."""
    if not values:
        raise ValueError("a percentile of no values is not defined")
    if not 0.0 <= percent <= 100.0:
        raise ValueError(f"a percentile lies between 0 and 100, not {percent}")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * percent / 100.0
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def detection(
    normal: Sequence[float], abnormal: Sequence[float], threshold: float
) -> dict[str, float | None]:
    """The share of abnormal windows caught and of normal windows flagged, at ``threshold``."""
    caught = sum(1 for value in abnormal if value >= threshold)
    flagged = sum(1 for value in normal if value >= threshold)
    return {
        "true_positive_rate": caught / len(abnormal) if abnormal else None,
        "false_alarm_rate": flagged / len(normal) if normal else None,
    }
