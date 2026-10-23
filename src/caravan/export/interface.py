"""The interface contract, as text (feature 006, contracts/interface.md).

Core module: once the model file has been read (``caravan.runtime.flatbuffer.read_bindings``), the
rest is formatting over plain data, and putting it behind an extra would deny it to the default
installation for no reason — the same reasoning that put the other emitters here (feature 004).

Principle VIII in 3.0.0: a model must be usable by someone who does not use Caravan, and a byte
array whose label order and input transformation live only in a run directory is a model nobody
else can feed correctly. So the export says, in a form any reader can parse: which model, every
input and output by name with the position the runtime takes, its shape, type, scale and zero
point, what was done to raw data before the model — stated as none where nothing was — and the
order of the labels. Everything is deterministic, so two exports give the same bytes (FR-027).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

#: Incremented by the first feature that adds an input kind, an output kind or input scaling.
CONTRACT_VERSION = 1

RUNTIME_BINDING = (
    "by position in subgraph 0: interpreter.input(position) / interpreter.output(position)"
)

#: Printable ASCII but for the two characters a C string literal gives meaning to.
_PLAIN = frozenset(range(0x20, 0x7F)) - {ord('"'), ord("\\")}


def interface_document(
    model: Mapping[str, str],
    bindings: Sequence[Mapping[str, Any]],
    declared_input: Mapping[str, Any],
    declared_output: Mapping[str, Any],
) -> str:
    """``model/interface.json``: sorted keys, two-space indentation, one trailing newline."""
    window = declared_input.get("window")
    inputs = [
        {
            **_tensor(binding),
            "transformation": {
                "kind": "series",
                "columns": list(declared_input["columns"]),
                "window": window,
                # Windows do not overlap: the next one starts where this one ended.
                "stride": window,
                # Stated, not omitted: "none" is a statement (Principle VIII). Feature 006 adds no
                # scaling; proposal P5 would.
                "scaling": "none",
            },
        }
        for binding in bindings
        if binding["role"] == "input"
    ]
    outputs = [
        {
            **_tensor(binding),
            "interpretation": {
                "kind": "class",
                "labels": list(declared_output["labels"]),
                # How the train and quantize stages turn scores into a class.
                "decision": "argmax",
            },
        }
        for binding in bindings
        if binding["role"] == "output"
    ]
    document = {
        "contract_version": CONTRACT_VERSION,
        "model": {"name": model["name"], "version": model["version"]},
        "model_file": "model/model.tflite",
        "runtime_binding": RUNTIME_BINDING,
        "inputs": inputs,
        "outputs": outputs,
    }
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _tensor(binding: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "name",
        "position",
        "tensor_index",
        "tensor_name",
        "shape",
        "element_type",
        "scale",
        "zero_point",
    )
    return {key: binding[key] for key in keys}


def c_label_literal(text: str) -> str:
    """A C string literal for any text, the same bytes every time.

    Every byte outside printable ASCII, and every ``"`` and ``\\``, is written as ``\\xNN``, and the
    literal is closed and reopened after each such escape: a C hex escape runs for as long as hex
    digits follow, so ``"\\xc3a"`` would read as one byte rather than two (research R7).
    """
    segments: list[str] = []
    current = ""
    for byte in text.encode("utf-8"):
        if byte in _PLAIN:
            current += chr(byte)
        else:
            segments.append(f"{current}\\x{byte:02x}")
            current = ""
    if current or not segments:
        segments.append(current)
    return " ".join(f'"{segment}"' for segment in segments)


def header_additions(
    array_name: str,
    model: Mapping[str, str],
    bindings: Sequence[Mapping[str, Any]],
    declared_output: Mapping[str, Any],
) -> str:
    """What the header gains: which model, one named position per tensor, the label array."""
    lines = [
        "/* Which model this is: the manifest's model.name and model.version. */",
        f"constexpr char {array_name}_model_name[] = {c_label_literal(model['name'])};",
        f"constexpr char {array_name}_model_version[] = {c_label_literal(model['version'])};",
        "",
        "/* Interface: positions for interpreter.input(i) / interpreter.output(i), read from the",
        " * model file's signature, not from the manifest. Bind by these names, never by a literal",
        " * index: the converter does not guarantee to keep the declared order. */",
    ]
    for binding in bindings:
        lines.append(
            f"constexpr unsigned int {array_name}_{binding['role']}_{binding['name']} = "
            f"{binding['position']};"
        )
    name = declared_output["name"]
    labels = list(declared_output["labels"])
    lines += [
        "",
        f'/* Class labels of output "{name}", in output-unit order. */',
        f"constexpr unsigned int {array_name}_output_{name}_label_count = {len(labels)};",
        f"extern const char* const {array_name}_output_{name}_labels[];",
    ]
    return "\n".join(lines) + "\n"


def source_additions(array_name: str, declared_output: Mapping[str, Any]) -> str:
    """What the source gains: the definition of the label array, in output-unit order."""
    name = declared_output["name"]
    body = "\n".join(f"    {c_label_literal(label)}," for label in declared_output["labels"])
    return f"const char* const {array_name}_output_{name}_labels[] = {{\n{body}\n}};\n"
