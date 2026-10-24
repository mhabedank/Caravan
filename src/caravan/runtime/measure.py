"""Running an exported model and counting what it got right.

Behind the ``verify`` extra. Since feature 008 a model has one input per feature, fed **by name**
through the model's signature: the converter reorders inputs (research note, section 4), so a
position assumed from the manifest would feed the wrong column without an error.

The one thing in here that is easy to get wrong and impossible to notice afterwards: an integer
input tensor must be fed integer data, quantized with the model's *own* scale and zero point.
Handing it float data is not an error — the runtime reinterprets the bytes and returns predictions —
so the accuracy that comes out is nonsense shaped like a measurement. Caravan's own models take raw
float32 and int32 inputs since feature 008, but a model with an int8 input is still fed correctly.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
    """Convert values into the form the model's input tensor expects.

    The scale and zero point come from the file (``inspect``), never from the data. A float32 or
    int32 tensor takes the values as they are, in its own type — the check is on the tensor, not on
    a flag.
    """
    if tensor.dtype in ("float32", "int32"):
        return values.astype(np.dtype(tensor.dtype))
    if tensor.scale is None:
        raise ValueError(
            f"the model's input tensor is {tensor.dtype} but carries no quantization scale, "
            "so there is no defined way to feed it"
        )
    limits = np.iinfo(np.dtype(tensor.dtype))
    scaled = np.round(values / tensor.scale) + (tensor.zero_point or 0)
    return np.clip(scaled, limits.min, limits.max).astype(np.dtype(tensor.dtype))


def _dequantize(values: np.ndarray, detail: Mapping[str, Any]) -> np.ndarray:
    scale, zero = detail.get("quantization", (0.0, 0))
    if not scale:
        return values.astype(np.float32)
    return (values.astype(np.float32) - zero) * scale


def run_model(
    path: Path, inputs: Mapping[str, np.ndarray] | np.ndarray, output: str | None = None
) -> np.ndarray:
    """The model's output per sample, as float32, shape (samples, units).

    ``inputs`` is a mapping input name -> (samples, ...) array, fed through the signature by name;
    a bare array feeds a model with one input. ``output`` names the output to return; ``None``
    takes the only one.
    """
    from ai_edge_litert.interpreter import Interpreter

    from caravan.runtime.inspect import _record

    interpreter = Interpreter(model_path=str(path))
    runner = interpreter.get_signature_runner()
    input_details = runner.get_input_details()
    output_details = runner.get_output_details()
    if not isinstance(inputs, Mapping):
        (only,) = input_details
        inputs = {only: inputs}
    missing = sorted(set(input_details) - set(inputs))
    if missing:
        raise ValueError(f"no values given for the model's input(s): {', '.join(missing)}")
    name = output if output is not None else next(iter(output_details))
    prepared = {
        key: quantize_input(np.asarray(values), _record(input_details[key]))
        for key, values in inputs.items()
        if key in input_details
    }
    count = len(next(iter(prepared.values())))
    out: list[np.ndarray] = []
    for index in range(count):
        result = runner(**{key: values[index : index + 1] for key, values in prepared.items()})
        out.append(_dequantize(np.asarray(result[name])[0], output_details[name]))
    if not out:
        return np.zeros((0, 0), dtype=np.float32)
    return np.stack(out).reshape(count, -1)


def predict(
    path: Path, features: Mapping[str, np.ndarray] | np.ndarray, output: str | None = None
) -> np.ndarray:
    """One class index per sample, from the model as it is stored.

    The arg-max of the dequantized output: dequantization is monotonic, so it cannot change which
    class wins.
    """
    return np.argmax(run_model(path, features, output), axis=1).astype(np.int64)


def measure(
    path: Path,
    features: Mapping[str, np.ndarray] | np.ndarray,
    targets: Sequence[int],
    label_count: int,
    *,
    split: str,
    dataset_version: str,
    output: str | None = None,
) -> SplitMeasurement:
    """Run the model over a split and return what it got right, with what it was run on."""
    truth = np.asarray(targets, dtype=np.int64)
    if len(truth) == 0:
        raise ValueError("a split with no samples cannot be measured")
    predicted = predict(path, features, output)

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
