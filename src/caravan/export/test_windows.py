"""Test windows for a board: raw inputs from the test part, with the host's int8 answers.

Feature 009.

A board run proves something only against a reference, and the reference here is the one the
accuracy gate measured: the quantized model, run on the host by the measurement runtime, on windows
of the same test part (``caravan.data.test_part``). Never the float model (FR-004).

The header this writes is what lets a firmware stay model-agnostic: everything that differs between
models — the inputs, their element types, the output's decision rule, the labels — is reached
through it and ``model_data.h``, so the board guide's firmware runs any exported model unchanged
(contracts/test-windows.md).

Core module: numpy and the runtime are imported inside the functions that need them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HEADER_NAME = "test_windows.h"

#: The selection rules, as the record and the header name them.
ROUND_ROBIN = "round-robin by class"
TEST_ORDER = "test order"

#: The C element type and the tensor's TfLite type and data member, per boundary element type.
_C_TYPES = {
    "float32": ("float", "kTfLiteFloat32", "f"),
    "int32": ("int32_t", "kTfLiteInt32", "i32"),
    "int8": ("int8_t", "kTfLiteInt8", "int8"),
}


def select(targets: Sequence[Any], classes: int, count: int, output_type: str) -> list[int]:
    """Positions in the test part, in the order the board runs them.

    A ``category`` or ``binary`` output takes the classes in turn, in label order, keeping test
    order within a class, so every class appears before any appears twice. A ``number`` output has
    no classes and takes the first ``count`` windows.
    """
    if output_type == "number":
        return list(range(min(count, len(targets))))
    by_class: list[list[int]] = [[] for _ in range(classes)]
    for position, target in enumerate(targets):
        by_class[int(target)].append(position)
    chosen: list[int] = []
    depth = 0
    while len(chosen) < count and any(depth < len(members) for members in by_class):
        for members in by_class:
            if depth < len(members) and len(chosen) < count:
                chosen.append(members[depth])
        depth += 1
    return chosen


def decide(scores: Any, output: Mapping[str, Any]) -> Any:
    """The decision under the output's rule, per window, as float, as ``Decide`` returns it.

    Argmax for a category, the threshold for a binary, the value itself for a number. Class indices
    are small integers, so they are exact as float, and the board compares them with ``==``.
    """
    import numpy as np

    if output["type"] == "category":
        return np.argmax(scores, axis=1).astype(np.float64)
    if output["type"] == "binary":
        return (scores.reshape(-1) >= float(output["threshold"])).astype(np.float64)
    return scores.reshape(-1).astype(np.float64)


@dataclass(frozen=True)
class TestWindows:
    """What the export wrote for a board, and the record of it."""

    asked: int
    available: int
    positions: tuple[int, ...]
    rule: str
    per_class: dict[str, int]
    score_step: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": f"model/{HEADER_NAME}",
            "asked": self.asked,
            "written": len(self.positions),
            "available": self.available,
            "split": "test",
            "selection": self.rule,
            "per_class": self.per_class,
            "score_step": self.score_step,
            "host_reference": "the int8 model, run on the host by the measurement runtime",
        }


def _c_float(value: float) -> str:
    """A float32 value as a C literal that reads back to the same float32."""
    text = repr(float(value))
    if "inf" in text or "nan" in text:  # pragma: no cover - inputs are filled, scores are finite
        raise ValueError(f"a test window holds {text}, which a C initialiser cannot carry")
    if "e" not in text and "." not in text:
        text += ".0"
    return text + "f"


def _row(values: Sequence[Any], element_type: str) -> str:
    if element_type == "float32":
        return ", ".join(_c_float(value) for value in values)
    return ", ".join(str(int(value)) for value in values)


def _table(name: str, c_type: str, rows: Sequence[Sequence[Any]], element_type: str) -> str:
    width = len(rows[0]) if rows else 0
    body = ",\n".join(f"    {{{_row(row, element_type)}}}" for row in rows)
    return f"static const {c_type} {name}[kCount][{width}] = {{\n{body}\n}};"


def _vector(name: str, values: Sequence[float]) -> str:
    body = ", ".join(_c_float(value) for value in values)
    return f"static const float {name}[kCount] = {{{body}}};"


def build(
    *,
    model_path: Path,
    test_features: Mapping[str, Any],
    test_targets: Any,
    output: Mapping[str, Any],
    count: int,
) -> tuple[TestWindows, dict[str, Any], Any, Any, Any]:
    """Select the windows and run them through the quantized model on the host.

    Returns the record, the chosen raw inputs per feature, the expected values, the host's scores
    and the host's decisions, each in the board's run order.
    """
    from caravan.runtime.inspect import output_score_step
    from caravan.runtime.measure import run_model

    labels = _labels(output)
    positions = select(test_targets, len(labels), count, output["type"])
    chosen = {name: values[positions] for name, values in test_features.items()}
    expected = test_targets[positions].astype("float64")
    scores = run_model(model_path, chosen, output["name"])
    decisions = decide(scores, output)
    per_class: dict[str, int] = {}
    if output["type"] != "number":
        for target in expected:
            per_class[labels[int(target)]] = per_class.get(labels[int(target)], 0) + 1
    record = TestWindows(
        asked=count,
        available=len(test_targets),
        positions=tuple(positions),
        rule=TEST_ORDER if output["type"] == "number" else ROUND_ROBIN,
        per_class=per_class,
        score_step=output_score_step(model_path, output["name"]),
    )
    return record, chosen, expected, scores, decisions


def _labels(output: Mapping[str, Any]) -> list[str]:
    """Printable names of the classes, in index order; empty for a number output."""
    fitted = output["preprocessing"].get("fitted", {})
    if output["type"] == "category":
        return [str(label) for label in fitted["labels"]]
    if output["type"] == "binary":
        spellings = fitted.get("spellings", {})
        true_name = fitted.get("true_spelling") or "true"
        false_name = next((s for s, bit in sorted(spellings.items()) if bit == 0), "false")
        return [str(false_name), str(true_name)]
    return []


def _c_string(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def header(
    *,
    record: TestWindows,
    array_name: str,
    bindings: Sequence[Mapping[str, Any]],
    output: Mapping[str, Any],
    chosen: Mapping[str, Any],
    expected: Any,
    scores: Any,
    decisions: Any,
    provenance: Mapping[str, str],
) -> str:
    """The text of ``model/test_windows.h`` (contracts/test-windows.md)."""
    if not record.positions:  # pragma: no cover - the gate needs a non-empty test part first
        raise ValueError("there are no test windows to write")
    output_binding = next(b for b in bindings if b["role"] == "output")
    inputs = [b for b in bindings if b["role"] == "input"]
    output_count = 1
    for dim in output_binding["shape"]:
        output_count *= int(dim)
    labels = _labels(output)
    kind = {"category": "kCategory", "binary": "kBinary", "number": "kNumber"}[output["type"]]

    tables: list[str] = []
    fills: list[str] = []
    for binding in inputs:
        name = binding["name"]
        c_type, tflite_type, member = _C_TYPES[binding["element_type"]]
        rows = [list(window.reshape(-1).tolist()) for window in chosen[name]]
        table = f"kInput_{name}"
        tables.append(f"/* Input {name}: {binding['element_type']}, raw values. */")
        tables.append(_table(table, c_type, rows, binding["element_type"]))
        position = f"{array_name}_input_{name}"
        fills.append(
            f"  {{\n"
            f"    TfLiteTensor* tensor = interpreter.input({position});\n"
            f"    if (tensor == nullptr || tensor->type != {tflite_type} ||\n"
            f"        tensor->bytes != sizeof({table}[0])) {{\n"
            f'      if (failed != nullptr) *failed = "{name}";\n'
            f"      return false;\n"
            f"    }}\n"
            f"    std::memcpy(tensor->data.{member}, {table}[i], sizeof({table}[0]));\n"
            f"  }}"
        )

    score_rows = ",\n".join(
        "    {" + ", ".join(_c_float(value) for value in row.reshape(-1).tolist()) + "}"
        for row in scores
    )
    if output["type"] == "category":
        decide_body = (
            "  int best = 0;\n"
            "  for (int k = 1; k < kOutputCount; ++k) {\n"
            "    if (scores[k] > scores[best]) best = k;\n"
            "  }\n"
            "  return static_cast<float>(best);"
        )
    elif output["type"] == "binary":
        threshold = f"{array_name}_output_{output['name']}_threshold"
        decide_body = f"  return scores[0] >= {threshold} ? 1.0f : 0.0f;"
    else:
        decide_body = "  return scores[0];"
    if labels:
        names = ", ".join(_c_string(label) for label in labels)
        name_body = (
            f"  static const char* const kNames[] = {{{names}}};\n"
            f"  const int index = static_cast<int>(decision);\n"
            f"  if (index < 0 || index >= {len(labels)}) {{\n"
            f'    std::snprintf(buf, 24, "?%d", index);\n'
            f"    return buf;\n"
            f"  }}\n"
            f'  std::snprintf(buf, 24, "%s", kNames[index]);\n'
            f"  return buf;"
        )
    else:
        name_body = (
            '  std::snprintf(buf, 24, "%.4g", static_cast<double>(decision));\n  return buf;'
        )

    counts = ", ".join(f"{label} {n}" for label, n in record.per_class.items()) or "no classes"
    written_line = (
        f"asked {record.asked}, written {len(record.positions)}, available {record.available}"
    )
    nl = "\n"
    return f"""/* test_windows.h — generated by caravan; do not edit.
 *
 * {len(record.positions)} windows of the test part, as raw values, with what the data says and
 * what the int8 model answered on the host. A board runs the same windows and compares
 * (feature 009).
 *
 * Model:          {provenance["model"]}
 * Run:            {provenance["run"]}
 * Dataset:        {provenance["dataset_version"]}
 * Split:          test
 * Selection:      {record.rule}
 * Windows:        {written_line}
 * Per class:      {counts}
 * Host reference: the int8 model, run by ai-edge-litert {provenance["runtime"]};
 *                 never the float model
 * Score step:     {record.score_step!r} (one quantization step of the output)
 *
 * Include it from exactly one translation unit: the arrays are static.
 */
#ifndef CARAVAN_TEST_WINDOWS_H_
#define CARAVAN_TEST_WINDOWS_H_

#include <cstdint>
#include <cstdio>
#include <cstring>

#include "model_data.h"
#include "tensorflow/lite/micro/micro_interpreter.h"

namespace caravan_windows {{

enum OutputType {{ kCategory, kBinary, kNumber }};

constexpr int kCount = {len(record.positions)};
constexpr int kOutputCount = {output_count};
constexpr OutputType kOutputType = {kind};
constexpr float kScoreStep = {_c_float(record.score_step)};
constexpr const char* kModelName = {array_name}_model_name;
constexpr const char* kModelVersion = {array_name}_model_version;

{nl.join(tables)}

/* What the data says: a class index (category, binary) or the value (number). */
{_vector("kExpected", expected.tolist())}

/* The int8 model's output on the host, after its DEQUANTIZE. */
static const float kHostScores[kCount][kOutputCount] = {{
{score_rows}
}};

/* The host's decision under Decide(), the same rule a board applies. */
{_vector("kHostDecision", decisions.tolist())}

/* Copies window i into every input tensor, by the named positions of model_data.h. Returns
 * false, naming the input in *failed, when a tensor's type or size is not what this header was
 * made for. */
inline bool FillWindow(tflite::MicroInterpreter& interpreter, int i,
                       const char** failed = nullptr) {{
{nl.join(fills)}
  return true;
}}

/* The decision under the output's rule: {output["type"]}. */
inline float Decide(const float* scores) {{
{decide_body}
}}

/* A short printable name for a decision: the class label, or the value. buf holds 24 bytes.
 */
inline const char* DecisionName(float decision, char* buf) {{
{name_body}
}}

}}  // namespace caravan_windows

#endif  /* CARAVAN_TEST_WINDOWS_H_ */
"""
