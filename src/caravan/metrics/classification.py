"""Accuracy, macro precision, recall and F1, per-class recall — all from one confusion matrix.

Every number leaves here as a ``QualityMetric``, which cannot be constructed without the split, the
dataset version and the sample count it was measured against. That is what makes SC-003 structural
rather than a habit: there is no path from a computation to a report that could drop the provenance
even by accident.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from caravan.run.report import ConfusionMatrix, QualityMetric


def confusion_matrix(
    true_indices: Sequence[int],
    predicted_indices: Sequence[int],
    class_count: int,
) -> np.ndarray:
    """Rows are the truth, columns the prediction — the orientation every report here uses."""
    matrix = np.zeros((class_count, class_count), dtype=np.int64)
    for truth, prediction in zip(true_indices, predicted_indices, strict=True):
        matrix[truth, prediction] += 1
    return matrix


def _ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Per-class ratio with 0 where the class has no cases.

    A class the model never predicted has no precision, and a class with no examples has no
    recall. Both are reported as 0 rather than omitted or left as a quiet NaN: a macro average
    over a silently shortened list of classes is the kind of number that flatters a model.
    """
    out = np.zeros(numerator.shape, dtype=np.float64)
    np.divide(numerator, denominator, out=out, where=denominator > 0)
    return out


def metrics_from_matrix(
    matrix: np.ndarray,
    labels: Sequence[str],
    *,
    split: str,
    dataset_version: str,
) -> tuple[list[QualityMetric], ConfusionMatrix]:
    """The fixed, documented set for classification, and the matrix it came from."""
    total = int(matrix.sum())
    true_positive = np.diag(matrix).astype(np.int64)
    predicted = matrix.sum(axis=0)
    actual = matrix.sum(axis=1)

    precision = _ratio(true_positive, predicted)
    recall = _ratio(true_positive, actual)
    f1 = _ratio(2 * precision * recall, precision + recall)

    def metric(name: str, value: float | dict[str, float]) -> QualityMetric:
        return QualityMetric(
            name=name,
            value=value,
            split=split,
            dataset_version=dataset_version,
            samples=total,
        )

    accuracy = float(true_positive.sum() / total) if total else 0.0
    out = [
        metric("accuracy", round(accuracy, 6)),
        metric("precision_macro", round(float(precision.mean()), 6)),
        metric("recall_macro", round(float(recall.mean()), 6)),
        metric("f1_macro", round(float(f1.mean()), 6)),
        metric(
            "recall_per_class",
            {label: round(float(value), 6) for label, value in zip(labels, recall, strict=True)},
        ),
    ]
    return out, ConfusionMatrix(
        labels=tuple(labels),
        rows=tuple(tuple(int(cell) for cell in row) for row in matrix),
        split=split,
        dataset_version=dataset_version,
    )
