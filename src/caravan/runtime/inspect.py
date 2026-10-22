"""What a model file actually contains, read from the file.

This module exists because of one measurement. The converter prints

    fully_quantize: 0, inference_type: 6, input_inference_type: INT8, output_inference_type: INT8

for a model whose every tensor is int8 or int32 (checked 2026-10-22, TensorFlow 2.21.0). A stage
that read that line as a verdict would report the opposite of the truth. So nothing here consults
a converter, its options, its return value or its log: the file is the only source.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Types that make a model an integer model. Biases are int32 in a fully int8 graph, which is
#: why int32 belongs here and why "all tensors are int8" would be the wrong test.
INTEGER_DTYPES = frozenset({"int8", "int16", "int32", "int64", "uint8"})


@dataclass(frozen=True)
class TensorRecord:
    """One tensor, as the file describes it."""

    name: str
    dtype: str
    shape: tuple[int, ...]
    scale: float | None = None
    zero_point: int | None = None

    @property
    def is_integer(self) -> bool:
        return self.dtype in INTEGER_DTYPES

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "dtype": self.dtype, "shape": list(self.shape)}
        if self.scale is not None:
            out["scale"] = self.scale
            out["zero_point"] = self.zero_point
        return out


@dataclass(frozen=True)
class ModelInspection:
    """Everything this project says about a produced model, and all of it from the file."""

    path: Path
    size_bytes: int
    input: TensorRecord
    output: TensorRecord
    tensors: tuple[TensorRecord, ...]

    @property
    def dtype_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for tensor in self.tensors:
            counts[tensor.dtype] = counts.get(tensor.dtype, 0) + 1
        return dict(sorted(counts.items()))

    @property
    def fully_integer(self) -> bool:
        """Computed from the tensor records, never from the setting that was requested."""
        return all(tensor.is_integer for tensor in self.tensors)

    def floating_tensors(self) -> tuple[str, ...]:
        return tuple(tensor.name for tensor in self.tensors if not tensor.is_integer)

    def as_dict(self) -> dict[str, Any]:
        return {
            "size_bytes": self.size_bytes,
            "fully_integer": self.fully_integer,
            "dtype_counts": self.dtype_counts,
            "input": self.input.as_dict(),
            "output": self.output.as_dict(),
            "tensors": [tensor.as_dict() for tensor in self.tensors],
        }


def _quantization(detail: dict[str, Any]) -> tuple[float | None, int | None]:
    scale, zero = detail.get("quantization", (0.0, 0))
    # A scale of zero is how the runtime says "this tensor is not quantized", not a scale of zero.
    if not scale:
        return None, None
    return float(scale), int(zero)


def _record(detail: dict[str, Any]) -> TensorRecord:
    scale, zero = _quantization(detail)
    return TensorRecord(
        name=str(detail.get("name", "")),
        dtype=detail["dtype"].__name__,
        shape=tuple(int(size) for size in detail["shape"]),
        scale=scale,
        zero_point=zero,
    )


def inspect_model(path: Path) -> ModelInspection:
    """Read a model file and report what it contains.

    Imports the runtime, so this is only ever called with the ``verify`` extra installed.
    """
    from ai_edge_litert.interpreter import Interpreter

    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()

    return ModelInspection(
        path=path,
        size_bytes=path.stat().st_size,
        input=_record(interpreter.get_input_details()[0]),
        output=_record(interpreter.get_output_details()[0]),
        tensors=tuple(_record(detail) for detail in interpreter.get_tensor_details()),
    )
