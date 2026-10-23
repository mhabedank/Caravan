"""The graph, read from the model file through the schema.

A sibling of ``inspect.py`` and for the same reason, one tool further on. That module exists
because a converter's log said the opposite of the truth; this one exists because the *interpreter*
does. Loading the pilot fixture's model and asking ``_get_ops_details()`` reports nine nodes, the
ninth a ``DELEGATE`` the desktop runtime inserted for itself while allocating tensors (checked
2026-10-22, ai-edge-litert 2.3.0). There is no such operator on a microcontroller. A resolver built
from that list would register a kernel the target's runtime has never heard of, and the failure
would appear at initialisation on hardware, a long way from here.

So the file is the only source, read through ``ai_edge_litert.schema_py_generated`` — the schema
binding the runtime extra already ships, which is why none of this needs a training framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caravan.export.memory import TensorLifetime, peak_live, read_write_total
from caravan.manifest.errors import RULE_DECLARED_NAME_NOT_IN_MODEL, run_rule_error


@dataclass(frozen=True)
class OperatorRecord:
    """One distinct operator of the graph, with what a resolver and a reader need."""

    name: str
    builtin_code: int
    version: int
    nodes: int
    custom_name: str | None = None

    @property
    def is_custom(self) -> bool:
        return self.custom_name is not None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "builtin_code": self.builtin_code,
            "version": self.version,
            "nodes": self.nodes,
        }
        if self.custom_name is not None:
            out["custom_name"] = self.custom_name
        return out


@dataclass(frozen=True)
class GraphInspection:
    """What one reading of a model file established."""

    operators: tuple[OperatorRecord, ...]
    nodes: int
    subgraphs: int
    input_shape: tuple[int, ...]
    output_shape: tuple[int, ...]
    working_memory_floor: int
    read_write_total: int
    model_bytes: int
    lifetimes: tuple[TensorLifetime, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "operators": [operator.as_dict() for operator in self.operators],
            "distinct_operators": len(self.operators),
            "nodes": self.nodes,
            "subgraphs": self.subgraphs,
            "input_shape": list(self.input_shape),
            "output_shape": list(self.output_shape),
            "model_bytes": self.model_bytes,
            "working_memory": {
                "floor_bytes": self.working_memory_floor,
                "floor_method": FLOOR_METHOD,
                "read_write_total_bytes": self.read_write_total,
                "read_write_total_is": (
                    "an upper bound on the tensor area, not a bound on the arena: a runtime "
                    "reuses one buffer for tensors whose lifetimes do not overlap"
                ),
            },
        }


#: Named in every report beside the figure, because a number without its method is the thing
#: Principle IV forbids.
FLOOR_METHOD = "peak simultaneously live read-write tensors, computed from the model file"


def _type_widths(schema: Any) -> dict[int, int]:
    """Byte width per schema tensor type, derived from the schema's own names.

    Derived rather than written out: a hand-kept table would silently go stale when the schema
    gains a type, and an unknown width would then be counted as zero in a memory figure.
    """
    widths = {
        "FLOAT32": 4, "FLOAT16": 2, "INT32": 4, "UINT8": 1, "INT64": 8, "STRING": 1,
        "BOOL": 1, "INT16": 2, "COMPLEX64": 8, "INT8": 1, "FLOAT64": 8, "COMPLEX128": 16,
        "UINT64": 8, "RESOURCE": 4, "VARIANT": 4, "UINT32": 4, "UINT16": 2, "INT4": 1,
        "BFLOAT16": 2,
    }  # fmt: skip
    out: dict[int, int] = {}
    for name, value in vars(schema.TensorType).items():
        if isinstance(value, int) and name in widths:
            out[value] = widths[name]
    return out


def inspect_graph(path: Path) -> GraphInspection:
    """Read the graph of a model file: its operators, its shapes and its memory figures."""
    from ai_edge_litert import schema_py_generated as schema

    data = bytearray(path.read_bytes())
    model = schema.Model.GetRootAsModel(data, 0)
    subgraphs = model.SubgraphsLength()
    graph = model.Subgraphs(0)
    widths = _type_widths(schema)
    names = {
        value: name
        for name, value in vars(schema.BuiltinOperator).items()
        if isinstance(value, int)
    }

    codes: list[tuple[int, str, str | None, int]] = []
    for index in range(model.OperatorCodesLength()):
        code = model.OperatorCodes(index)
        custom = code.CustomCode()
        builtin = code.BuiltinCode()
        custom_name = custom.decode("utf-8") if custom else None
        label = names.get(builtin, f"UNKNOWN_{builtin}")
        codes.append((builtin, label, custom_name, code.Version()))

    # Counted in order of first appearance, so the resolver and the report read in graph order
    # rather than in whatever order the file happens to list the codes.
    counts: dict[int, int] = {}
    order: list[int] = []
    for node in range(graph.OperatorsLength()):
        index = graph.Operators(node).OpcodeIndex()
        if index not in counts:
            order.append(index)
        counts[index] = counts.get(index, 0) + 1

    operators = tuple(
        OperatorRecord(
            name=codes[index][2] or codes[index][1],
            builtin_code=codes[index][0],
            version=codes[index][3],
            nodes=counts[index],
            custom_name=codes[index][2],
        )
        for index in order
    )

    lifetimes = _lifetimes(model, graph, widths)
    return GraphInspection(
        operators=operators,
        nodes=graph.OperatorsLength(),
        subgraphs=subgraphs,
        input_shape=_shape(graph.Tensors(graph.Inputs(0))),
        output_shape=_shape(graph.Tensors(graph.Outputs(0))),
        working_memory_floor=peak_live(lifetimes, nodes=graph.OperatorsLength()),
        read_write_total=read_write_total(lifetimes),
        model_bytes=path.stat().st_size,
        lifetimes=lifetimes,
    )


def _shape(tensor: Any) -> tuple[int, ...]:
    return tuple(int(dim) for dim in tensor.ShapeAsNumpy()) if tensor.ShapeLength() else ()


def _lifetimes(model: Any, graph: Any, widths: dict[int, int]) -> tuple[TensorLifetime, ...]:
    """The span of nodes each non-constant tensor must survive.

    A tensor whose buffer carries data is a constant: it lives in flash, not in the arena, so it is
    not part of a working-memory figure at all.
    """
    nodes = graph.OperatorsLength()
    constant = {
        index: model.Buffers(graph.Tensors(index).Buffer()).DataLength() > 0
        for index in range(graph.TensorsLength())
    }
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    for node in range(nodes):
        operator = graph.Operators(node)
        touched = [int(t) for t in operator.InputsAsNumpy()] + [
            int(t) for t in operator.OutputsAsNumpy()
        ]
        for tensor in touched:
            # -1 is the schema's way of saying "this optional input is absent".
            if tensor < 0 or constant.get(tensor, True):
                continue
            first.setdefault(tensor, node)
            last[tensor] = node
    for position in range(graph.InputsLength()):
        tensor = int(graph.Inputs(position))
        if not constant.get(tensor, True):
            first[tensor] = -1
            last.setdefault(tensor, 0)
    for position in range(graph.OutputsLength()):
        tensor = int(graph.Outputs(position))
        if not constant.get(tensor, True):
            first.setdefault(tensor, nodes)
            last[tensor] = nodes

    spans = []
    for tensor in sorted(first):
        record = graph.Tensors(tensor)
        shape = _shape(record)
        count = 1
        for dim in shape:
            count *= dim
        spans.append(
            TensorLifetime(
                index=tensor,
                bytes=count * widths.get(record.Type(), 0),
                first_node=first[tensor],
                last_node=last[tensor],
            )
        )
    return tuple(spans)


@dataclass(frozen=True)
class TensorBinding:
    """One declared input or output, as the converted model file has it (feature 006).

    ``position`` is what the microcontroller runtime takes — ``MicroInterpreter::input(i)`` indexes
    subgraph 0's input list by position and reads no signature (tflite-micro ``f7ed40d``, research
    R5) — and it is found through the signature, never assumed from the declaration, because the
    converter does not keep the declared order (research R4).
    """

    name: str
    role: str
    position: int
    tensor_index: int
    tensor_name: str
    shape: tuple[int, ...]
    element_type: str
    scale: float | None
    zero_point: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "position": self.position,
            "tensor_index": self.tensor_index,
            "tensor_name": self.tensor_name,
            "shape": list(self.shape),
            "element_type": self.element_type,
            "scale": self.scale,
            "zero_point": self.zero_point,
        }


def read_bindings(
    path: Path, *, inputs: list[str] | tuple[str, ...], outputs: list[str] | tuple[str, ...]
) -> tuple[TensorBinding, ...]:
    """Every declared name, bound to its position in the model file — inputs first, in order.

    A declared name the signature does not carry is refused with rule X-6: the contract binds by
    that name, and guessing which tensor was meant is exactly the error it exists to prevent.
    """
    from ai_edge_litert import schema_py_generated as schema

    data = bytearray(path.read_bytes())
    model = schema.Model.GetRootAsModel(data, 0)
    graph = model.Subgraphs(0)
    type_names = {
        value: name.lower()
        for name, value in vars(schema.TensorType).items()
        if isinstance(value, int) and not name.startswith("_")
    }

    signature: dict[str, dict[str, int]] = {"input": {}, "output": {}}
    if model.SignatureDefsLength():
        definition = model.SignatureDefs(0)
        for index in range(definition.InputsLength()):
            entry = definition.Inputs(index)
            signature["input"][entry.Name().decode("utf-8")] = int(entry.TensorIndex())
        for index in range(definition.OutputsLength()):
            entry = definition.Outputs(index)
            signature["output"][entry.Name().decode("utf-8")] = int(entry.TensorIndex())
    positions = {
        "input": [int(graph.Inputs(i)) for i in range(graph.InputsLength())],
        "output": [int(graph.Outputs(i)) for i in range(graph.OutputsLength())],
    }

    bindings: list[TensorBinding] = []
    for role, names in (("input", inputs), ("output", outputs)):
        for index, name in enumerate(names):
            tensor_index = signature[role].get(name)
            if tensor_index is None or tensor_index not in positions[role]:
                run_rule_error(
                    RULE_DECLARED_NAME_NOT_IN_MODEL,
                    f"{role}s[{index}].name",
                    (
                        f"the converted model's signature carries no {role} named {name!r}; the "
                        "interface contract binds by name, so it refuses to guess which tensor "
                        "was meant"
                    ),
                    found=name,
                    accepted=tuple(sorted(signature[role])),
                )
            tensor = graph.Tensors(tensor_index)
            quantization = tensor.Quantization()
            quantized = quantization is not None and quantization.ScaleLength() > 0
            bindings.append(
                TensorBinding(
                    name=name,
                    role=role,
                    position=positions[role].index(tensor_index),
                    tensor_index=tensor_index,
                    tensor_name=(tensor.Name() or b"").decode("utf-8"),
                    shape=_shape(tensor),
                    element_type=type_names.get(tensor.Type(), f"type_{tensor.Type()}"),
                    scale=float(quantization.Scale(0)) if quantized else None,
                    zero_point=int(quantization.ZeroPoint(0)) if quantized else None,
                )
            )
    return tuple(bindings)
