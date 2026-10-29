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
#: why int32 belongs here and why "all tensors are int8" would be the wrong test. ``bool`` is the
#: result of the EQUAL a category's one-hot compares with (feature 008, research R3): one byte, no
#: floating point.
INTEGER_DTYPES = frozenset({"int8", "int16", "int32", "int64", "uint8", "bool"})

#: What a model's boundary may carry since feature 008 (research R5): an input is the raw value the
#: firmware passes — float32 for a number, int32 for a code — and is followed by the converter's
#: QUANTIZE; an output is float32 after its DEQUANTIZE. An int8 boundary is still integer. Since
#: feature 010 an image arrives as uint8 raw pixels at scale 1, zero point 0 (research R6).
BOUNDARY_INPUT_DTYPES = frozenset({"float32", "int32", "int8", "uint8"})
BOUNDARY_OUTPUT_DTYPES = frozenset({"float32", "int8"})


@dataclass(frozen=True)
class TensorRecord:
    """One tensor, as the file describes it."""

    name: str
    dtype: str
    shape: tuple[int, ...]
    scale: float | None = None
    zero_point: int | None = None
    index: int | None = None

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
    inputs: tuple[TensorRecord, ...]
    outputs: tuple[TensorRecord, ...]
    tensors: tuple[TensorRecord, ...]
    #: Indices of the tensors whose every consumer is a QUANTIZE: the conversion of a raw value
    #: into int8, such as a category's one-hot (feature 008, research R5).
    into_quantize: frozenset[int] = frozenset()

    @property
    def input(self) -> TensorRecord:
        """The first input, for a model that has one."""
        return self.inputs[0]

    @property
    def output(self) -> TensorRecord:
        return self.outputs[0]

    @property
    def dtype_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for tensor in self.tensors:
            counts[tensor.dtype] = counts.get(tensor.dtype, 0) + 1
        return dict(sorted(counts.items()))

    def _boundary(self) -> dict[int, frozenset[str]]:
        allowed: dict[int, frozenset[str]] = {}
        for tensor in self.inputs:
            if tensor.index is not None:
                allowed[tensor.index] = BOUNDARY_INPUT_DTYPES
        for tensor in self.outputs:
            if tensor.index is not None:
                allowed[tensor.index] = BOUNDARY_OUTPUT_DTYPES
        return allowed

    def floating_tensors(self) -> tuple[str, ...]:
        """Tensors that make the model not integer: inside it, anything but an integer type; at its
        boundary, anything but the raw types a firmware passes and receives (research R5)."""
        boundary = self._boundary()
        out: list[str] = []
        for tensor in self.tensors:
            permitted = boundary.get(tensor.index) if tensor.index is not None else None
            if permitted is not None:
                if tensor.dtype not in permitted:
                    out.append(tensor.name)
            elif tensor.index in self.into_quantize and tensor.dtype == "float32":
                continue  # a raw value on its way into int8, like a model input
            elif not tensor.is_integer:
                out.append(tensor.name)
        return tuple(out)

    @property
    def fully_integer(self) -> bool:
        """Computed from the tensor records, never from the setting that was requested."""
        return not self.floating_tensors()

    def as_dict(self) -> dict[str, Any]:
        return {
            "size_bytes": self.size_bytes,
            "fully_integer": self.fully_integer,
            "dtype_counts": self.dtype_counts,
            "inputs": [tensor.as_dict() for tensor in self.inputs],
            "outputs": [tensor.as_dict() for tensor in self.outputs],
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
        index=int(detail["index"]) if "index" in detail else None,
    )


def _into_quantize(path: Path) -> frozenset[int]:
    """Tensors every consumer of which is a QUANTIZE, read from the file's graph."""
    from ai_edge_litert import schema_py_generated as schema

    model = schema.Model.GetRootAsModel(bytearray(path.read_bytes()), 0)
    graph = model.Subgraphs(0)
    quantize = schema.BuiltinOperator.QUANTIZE
    consumers: dict[int, set[int]] = {}
    for node in range(graph.OperatorsLength()):
        operator = graph.Operators(node)
        code = model.OperatorCodes(operator.OpcodeIndex()).BuiltinCode()
        for tensor in operator.InputsAsNumpy():
            consumers.setdefault(int(tensor), set()).add(int(code))
    return frozenset(index for index, codes in consumers.items() if codes == {quantize})


def inspect_model(path: Path) -> ModelInspection:
    """Read a model file and report what it contains.

    Imports the runtime, so this is only ever called with the ``verify`` extra installed.
    """
    from ai_edge_litert.interpreter import Interpreter

    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()

    return ModelInspection(
        into_quantize=_into_quantize(path),
        path=path,
        size_bytes=path.stat().st_size,
        inputs=tuple(_record(detail) for detail in interpreter.get_input_details()),
        outputs=tuple(_record(detail) for detail in interpreter.get_output_details()),
        tensors=tuple(_record(detail) for detail in interpreter.get_tensor_details()),
    )


def output_score_step(path: Path, output_name: str) -> float:
    """One quantization step of a model output, in the output's own unit (feature 009).

    The output reaches the boundary as float32 through a DEQUANTIZE, so its resolution is the scale
    of the int8 tensor that DEQUANTIZE reads; an output that is itself int8 carries its own scale.
    Read from the file's graph, like everything in this module. It is what "the board's score
    differs from the host's by at most one step" is measured in.
    """
    from ai_edge_litert import schema_py_generated as schema
    from ai_edge_litert.interpreter import Interpreter

    runner = Interpreter(model_path=str(path)).get_signature_runner()
    details = runner.get_output_details()
    if output_name not in details:
        raise KeyError(f"the model has no output named {output_name!r}: {sorted(details)}")
    index = int(details[output_name]["index"])

    model = schema.Model.GetRootAsModel(bytearray(path.read_bytes()), 0)
    graph = model.Subgraphs(0)

    def scale_of(tensor_index: int) -> float | None:
        quantization = graph.Tensors(tensor_index).Quantization()
        if quantization is None or quantization.ScaleLength() == 0:
            return None
        scale = float(quantization.Scale(0))
        return scale or None

    own = scale_of(index)
    if own is not None:
        return own
    dequantize = schema.BuiltinOperator.DEQUANTIZE
    for node in range(graph.OperatorsLength()):
        operator = graph.Operators(node)
        if index not in operator.OutputsAsNumpy().tolist():
            continue
        if model.OperatorCodes(operator.OpcodeIndex()).BuiltinCode() == dequantize:
            source = scale_of(int(operator.Inputs(0)))
            if source is not None:
                return source
        break
    raise ValueError(
        f"output {output_name!r} is neither quantized nor produced by a DEQUANTIZE of a quantized "
        "tensor, so it has no quantization step"
    )
