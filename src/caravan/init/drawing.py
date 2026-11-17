"""The network as text: one box per layer that holds weights or moves data (FR-032).

Drawn from the same layer records the memory estimate uses, so the drawing, the memory panel and
``build`` describe one model. Normalisation, activation and dropout are not drawn: they hold no
weights the board stores separately and do not change a shape.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from caravan.init.memory import Feature, body, input_records

WIDTH = 40


def _box(title: str, detail: str, note: str = "") -> list[str]:
    inner = WIDTH - 4
    text = f"{title:<13}{detail}"[:inner]
    return [
        "┌─┴" + "─" * (WIDTH - 4) + "┐",
        "│ " + text.ljust(inner) + " │" + (f"  {note}" if note else ""),
        "└─┬" + "─" * (WIDTH - 4) + "┘",
    ]


def draw(
    features: Sequence[Feature],
    window: int | None,
    template: Any,
    params: Mapping[str, Any],
    output_type: str,
    classes: int,
) -> list[str]:
    """The lines of the drawing, top (inputs) to bottom (the answer)."""
    records, channels = input_records(features, window)
    layers = body(template, params, window, channels, output_type, classes)
    steps = window or 1
    names = ", ".join(feature.name for feature in features)
    embedded = [record for record in records if record.kind == "dense"]
    lines = [f"inputs  {names}"]
    if embedded:
        lines.append(
            "        categories embedded: "
            + ", ".join(
                f"{r.name.removesuffix('_embedding')} → {r.output_elements // steps}"
                for r in embedded
            )
        )
    lines += [f"        {steps} rows x {channels} channels", "  │"]
    if not layers:
        lines += _box(getattr(template, "identifier", "?"), "no drawing for this template")
    depth = channels
    for record in layers:
        weights = record.kernel_elements + record.bias_elements
        note = f"{weights:,} weights" if weights else ""
        if record.kind == "dense":
            detail = f"dense {record.input_elements} → {record.output_elements}"
        elif record.kind == "conv":
            depth = record.bias_elements or depth
            detail = f"conv  → {record.output_elements // depth} x {depth}"
        else:
            detail = f"pool  → {record.output_elements // depth} x {depth}"
        lines += _box(record.name, detail, note)
    lines[-1] = lines[-1].replace("┬", "─")
    answer = {
        "category": f"one score per class ({classes})",
        "binary": "one probability",
        "number": "one value, in the column's unit",
        "anomaly": "the reconstruction error: the anomaly score",
    }[output_type]
    lines.append(f"answer  {answer}")
    return lines
