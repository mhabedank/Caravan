"""The interface contract, as text (features 006 and 008, contracts/interface.md).

Core module: once the model file has been read (``caravan.runtime.flatbuffer.read_bindings``), the
rest is formatting over plain data, and putting it behind an extra would deny it to the default
installation for no reason.

Principle VIII: a model must be usable by someone who does not use Caravan. Since feature 008 every
input feature is its own model input, bound by name, and each type's preprocessing is inside the
model — so the firmware passes raw values. The contract says, in a form any reader can parse: which
model, every input by name with the position the runtime takes, its element type (float32 for a
number, int32 for a code), its shape and type; for a category the table from text to code when the
data's values are text; the value to pass when a reading is absent; what was fitted, so a reader can
see what the model does to a raw value; and what the output means. Everything is deterministic, so
two exports give the same bytes (FR-027).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

#: 2 since feature 008: one input per feature, raw values in, preprocessing inside the model.
CONTRACT_VERSION = 2

RUNTIME_BINDING = (
    "by position in subgraph 0: interpreter.input(position) / interpreter.output(position)"
)

#: Stated, not omitted: where the preprocessing is is a statement (Principle VIII).
PREPROCESSING = "inside the model; pass raw values"

#: What a firmware does with the output, per type.
DECISIONS = {"category": "argmax", "binary": "threshold", "number": "value"}

#: Printable ASCII but for the two characters a C string literal gives meaning to.
_PLAIN = frozenset(range(0x20, 0x7F)) - {ord('"'), ord("\\")}


def _binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": binding["name"],
        "position": binding["position"],
        "tensor_index": binding["tensor_index"],
        "tensor_name": binding["tensor_name"],
        "shape": list(binding["shape"]),
        "dtype": binding["element_type"],
        "scale": binding["scale"],
        "zero_point": binding["zero_point"],
    }


def input_entry(binding: Mapping[str, Any], feature: Mapping[str, Any]) -> dict[str, Any]:
    """One input: its binding, its type, and what a firmware needs to feed it raw values."""
    fitted = feature["preprocessing"]["fitted"]
    entry: dict[str, Any] = {**_binding(binding), "type": feature["type"], "fitted": fitted}
    if feature["type"] == "number":
        entry["missing"] = fitted["fill"]
    elif feature["type"] == "category":
        entry["encoder"] = dict(feature["encoder"])
        entry["text_codes"] = fitted["text_codes"]
        entry["missing"] = fitted["missing"]
    else:
        entry["spellings"] = fitted["spellings"]
        entry["missing"] = fitted["missing"]
    return entry


def output_entry(binding: Mapping[str, Any], output: Mapping[str, Any]) -> dict[str, Any]:
    """The output: its binding, its type and how a firmware turns it into an answer."""
    fitted = output["preprocessing"]["fitted"]
    entry: dict[str, Any] = {
        **_binding(binding),
        "type": output["type"],
        "decision": DECISIONS[output["type"]],
    }
    if output["type"] == "category":
        entry["labels"] = list(fitted["labels"])
    elif output["type"] == "binary":
        entry["threshold"] = output["threshold"]
        entry["true_spelling"] = fitted["true_spelling"]
    else:
        entry["unit"] = "the column's own"
        entry["clip"] = output.get("clip")
    return entry


def interface_document(
    model: Mapping[str, str],
    bindings: Sequence[Mapping[str, Any]],
    features: Sequence[Mapping[str, Any]],
    output: Mapping[str, Any],
    window_size: int | None,
) -> str:
    """``model/interface.json``: sorted keys, two-space indentation, one trailing newline."""
    by_name = {feature["name"]: feature for feature in features}
    inputs = [
        input_entry(binding, by_name[binding["name"]])
        for binding in bindings
        if binding["role"] == "input"
    ]
    outputs = [output_entry(binding, output) for binding in bindings if binding["role"] == "output"]
    document = {
        "contract_version": CONTRACT_VERSION,
        "model": {"name": model["name"], "version": model["version"]},
        "model_file": "model/model.tflite",
        "runtime_binding": RUNTIME_BINDING,
        "window_size": window_size,
        # Windows do not overlap: the next one starts where this one ended.
        "stride": window_size,
        "preprocessing": PREPROCESSING,
        "inputs": inputs,
        "outputs": outputs,
    }
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


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


def _elements(shape: Sequence[int]) -> int:
    count = 1
    for dim in shape:
        count *= int(dim)
    return count


#: What a firmware writes into an input, per type, for the header's comment.
_MEANING = {
    "number": "raw value",
    "category": "category code, an integer and never a rounded number",
    "binary": "0 or 1",
}


def header_additions(
    array_name: str,
    model: Mapping[str, str],
    bindings: Sequence[Mapping[str, Any]],
    features: Sequence[Mapping[str, Any]],
    output: Mapping[str, Any],
) -> str:
    """What the header gains: which model, one named position per tensor, the output's meaning."""
    types = {feature["name"]: feature["type"] for feature in features}
    lines = [
        "/* Which model this is: the manifest's model.name and model.version. */",
        f"constexpr char {array_name}_model_name[] = {c_label_literal(model['name'])};",
        f"constexpr char {array_name}_model_version[] = {c_label_literal(model['version'])};",
        "",
        "/* Interface: positions for interpreter.input(i) / interpreter.output(i), read from the",
        " * model file's signature, not from the manifest. Bind by these names, never by a literal",
        " * index: the converter does not keep the manifest's order. Every input takes raw values;",
        " * the preprocessing is inside the model. */",
    ]
    for binding in bindings:
        kind = binding["element_type"]
        count = _elements(binding["shape"])
        meaning = (
            _MEANING[types[binding["name"]]]
            if binding["role"] == "input"
            else DECISIONS[output["type"]]
        )
        lines.append(
            f"constexpr unsigned int {array_name}_{binding['role']}_{binding['name']} = "
            f"{binding['position']};  /* {kind}[{count}] — {meaning} */"
        )
    name = output["name"]
    lines.append("")
    if output["type"] == "category":
        labels = list(output["preprocessing"]["fitted"]["labels"])
        lines += [
            f'/* Class labels of output "{name}", in output-unit order: the answer is the arg-max. */',
            f"constexpr unsigned int {array_name}_output_{name}_label_count = {len(labels)};",
            f"extern const char* const {array_name}_output_{name}_labels[];",
        ]
    elif output["type"] == "binary":
        lines += [
            f'/* Output "{name}" is true when its score is at least this. */',
            f"constexpr float {array_name}_output_{name}_threshold = {float(output['threshold'])!r}f;",
        ]
    else:
        lines.append(f'/* Output "{name}" is a value in the unit of its column. */')
    return "\n".join(lines) + "\n"


def source_additions(array_name: str, output: Mapping[str, Any]) -> str:
    """What the source gains: the label array of a ``category`` output, in output-unit order."""
    if output["type"] != "category":
        return ""
    name = output["name"]
    labels = output["preprocessing"]["fitted"]["labels"]
    body = "\n".join(f"    {c_label_literal(label)}," for label in labels)
    return f"const char* const {array_name}_output_{name}_labels[] = {{\n{body}\n}};\n"
