"""Running an exported model and counting what it got right.

Behind the ``verify`` extra. The one thing in here that is easy to get wrong and impossible to
notice afterwards: an integer input tensor must be fed integer data, quantized with the model's
*own* scale and zero point. Handing it float data is not an error — the runtime reinterprets the
bytes and returns predictions — so the accuracy that comes out is nonsense shaped like a
measurement. That is why the quantization step below is not a convenience.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from caravan.runtime.inspect import TensorRecord


@dataclass(frozen=True)
class SplitMeasurement:
    """What a model does on one split, inseparable from which split that was."""

    accuracy: float
    confusion: tuple[tuple[int, ...], ...]
    samples: int
    split: str
    dataset_version: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "accuracy": round(self.accuracy, 6),
            "samples": self.samples,
            "split": self.split,
            "dataset_version": self.dataset_version,
            "confusion": [list(row) for row in self.confusion],
        }


def quantize_input(values: np.ndarray, tensor: TensorRecord) -> np.ndarray:
    """Convert float features into the integer form the model's input tensor expects.

    The scale and zero point come from the file (``inspect``), never from the data. Float input to
    a float tensor passes through unchanged — the check is on the tensor, not on a flag.
    """
    if tensor.dtype == "float32":
        return values.astype(np.float32)
    if tensor.scale is None:
        raise ValueError(
            f"the model's input tensor is {tensor.dtype} but carries no quantization scale, "
            "so there is no defined way to feed it"
        )
    limits = np.iinfo(np.dtype(tensor.dtype))
    scaled = np.round(values / tensor.scale) + (tensor.zero_point or 0)
    return np.clip(scaled, limits.min, limits.max).astype(np.dtype(tensor.dtype))


def predict(path: Path, features: np.ndarray) -> np.ndarray:
    """One class index per sample, from the model as it is stored.

    The arg-max is taken on the stored output without dequantizing it: dequantization is
    monotonic, so it cannot change which class wins. It would be needed to report a probability,
    which this project does not do here — a probability from an int8 output would carry a
    precision it does not have.
    """
    from ai_edge_litert.interpreter import Interpreter

    from caravan.runtime.inspect import _record

    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    input_tensor = _record(input_detail)

    prepared = quantize_input(features, input_tensor)
    out: list[int] = []
    for sample in prepared:
        interpreter.set_tensor(input_detail["index"], sample[np.newaxis, ...])
        interpreter.invoke()
        out.append(int(np.argmax(interpreter.get_tensor(output_detail["index"])[0])))
    return np.array(out, dtype=np.int64)


def measure(
    path: Path,
    features: np.ndarray,
    targets: Sequence[int],
    label_count: int,
    *,
    split: str,
    dataset_version: str,
) -> SplitMeasurement:
    """Run the model over a split and return what it got right, with what it was run on."""
    predicted = predict(path, features)
    truth = np.asarray(targets, dtype=np.int64)
    if len(truth) == 0:
        raise ValueError("a split with no samples cannot be measured")

    matrix = np.zeros((label_count, label_count), dtype=np.int64)
    for actual, guess in zip(truth, predicted, strict=True):
        matrix[actual, guess] += 1

    return SplitMeasurement(
        accuracy=float((predicted == truth).sum() / len(truth)),
        confusion=tuple(tuple(int(cell) for cell in row) for row in matrix),
        samples=len(truth),
        split=split,
        dataset_version=dataset_version,
    )
