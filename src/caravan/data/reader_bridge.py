"""Assembling read records into the arrays a model sees, one per input feature.

Core-importable on purpose: ``numpy`` is imported inside the functions, so a stage module can
import this without pulling an array library into an installation that has none. The *rule* —
which records form which sample — lives in ``windows.py``; what a value becomes lives in ``fit.py``;
this is the stacking and the mapping by the fitted tables.

It is shared rather than copied because the stages must form identical samples from identical
inputs: the quantization stage measures a model on the same test part the training stage used.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _window_rows(plan: Any) -> Any:
    import numpy as np

    length = plan.window or 1
    starts = np.asarray(plan.kept, dtype=np.int64)
    return starts[:, None] + np.arange(length, dtype=np.int64)[None, :]


def _codes(values: Any, convert: Any) -> Any:
    """Map text cells to int32 through one call per distinct value."""
    import numpy as np

    distinct, inverse = np.unique(values, return_inverse=True)
    table = np.array([convert(str(value)) for value in distinct.tolist()], dtype=np.int32)
    return table[inverse.reshape(values.shape)]


def feature_column(records: Any, feature: Mapping[str, Any]) -> Any:
    """One feature's column as the model's input takes it: float32 raw values or int32 codes.

    A missing number is filled with the fitted fill value; a category becomes its code (the integer
    itself, or 1..V for text); a binary value becomes 0 or 1. Nothing is scaled here: the scaling
    is inside the model, so the firmware passes the same raw values (research R3).
    """
    import numpy as np

    from caravan.data.fit import binary_code, category_code

    fitted = feature["preprocessing"]["fitted"]
    column = records.columns[feature["name"]]
    if feature["type"] == "number":
        return np.where(np.isnan(column), np.float32(fitted["fill"]), column).astype(np.float32)
    if feature["type"] == "category":
        return _codes(column, lambda value: category_code(value, fitted))
    table = fitted["spellings"]

    def to_bit(value: str) -> int:
        return fitted["missing"] if value == "" else binary_code(value, table)

    return _codes(column, to_bit)


def assemble_inputs(
    records: Any, plan: Any, features: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Every planned window, per input feature: name -> (samples, window) array."""
    rows = _window_rows(plan)
    return {feature["name"]: feature_column(records, feature)[rows] for feature in features}


def assemble_targets(plan: Any, output: Mapping[str, Any]) -> Any:
    """What each window should answer: a class index, a 0/1, or the value in the column's unit."""
    import numpy as np

    from caravan.data.fit import binary_code

    fitted = output["preprocessing"]["fitted"]
    if output["type"] == "category":
        index_of = {label: position for position, label in enumerate(fitted["labels"])}
        return np.array([index_of[label] for label in plan.labels], dtype=np.int64)
    if output["type"] == "binary":
        table = fitted["spellings"]
        return np.array([binary_code(label, table) for label in plan.labels], dtype=np.float32)
    return np.array([float(label) for label in plan.labels], dtype=np.float32)


def assemble_samples(
    records: Any,
    plan: Any,
    features: Sequence[Mapping[str, Any]],
    output: Mapping[str, Any],
) -> tuple[dict[str, Any], Any]:
    """The inputs, keyed by feature name, and the targets."""
    return assemble_inputs(records, plan, features), assemble_targets(plan, output)


def select(inputs: Mapping[str, Any], indices: Sequence[int]) -> dict[str, Any]:
    """The samples at these positions, every input alike."""
    chosen = list(indices)
    return {name: values[chosen] for name, values in inputs.items()}
