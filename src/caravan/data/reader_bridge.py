"""Assembling read records into the arrays a model sees.

Core-importable on purpose: ``numpy`` is imported inside the function, so a stage module can
import this without pulling an array library into an installation that has none. The *rule* —
which records form which sample — lives in ``windows.py`` and needs no array library at all; this
is only the stacking.

It is shared rather than copied because two stages must form identical samples from identical
inputs: the quantization stage measures a model on the same test split the training stage used,
and a second implementation of this would be a place for those to drift apart silently.
"""

from __future__ import annotations

from typing import Any


def assemble_samples(records: Any, plan: Any, labels: tuple[str, ...]) -> tuple[Any, Any]:
    """Stack the planned windows into one array, and the labels into class indices."""
    import numpy as np

    index_of = {label: position for position, label in enumerate(labels)}
    if plan.window is None:
        features = records.features
    else:
        features = np.stack([records.features[start : start + plan.window] for start in plan.kept])
    targets = np.array([index_of[label] for label in plan.labels], dtype=np.int64)
    return features, targets
