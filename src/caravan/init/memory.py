"""What the model will cost on each board, before it is built (feature 013, research R13).

The layers the built model will have, reduced to the records ``build``'s fit check reads, from the
inputs, the window, the template and its parameters. The floors and verdicts are then computed by
the same functions ``build`` uses (``caravan.targets.fit``), so the panel and the check that stops a
build before training cannot disagree about method. They are lower bounds, labelled as such: a
pass is not a claim that the model fits (Principle IV).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from caravan.manifest.resolve import EMBEDDING_SIZE_CAP
from caravan.targets.fit import FitFloor, FitVerdict, LayerRecord, dense_record, floors, verdicts

LABEL = "lower bounds, estimated before building; caravan build checks them again"
BAR = 24


@dataclass(frozen=True)
class Feature:
    """One input as the estimate needs it: its type and, for a category, its vocabulary size."""

    name: str
    type: str
    vocabulary: int = 0


@dataclass(frozen=True)
class Estimate:
    records: tuple[LayerRecord, ...]
    flash: FitFloor
    ram: FitFloor
    verdicts: tuple[FitVerdict, ...]

    def exceeds(self, board: str) -> bool:
        return any(v.board == board and v.verdict != "below" for v in self.verdicts)


def _channels(feature: Feature) -> int:
    if feature.type == "category":
        return min(feature.vocabulary, EMBEDDING_SIZE_CAP)
    return 1


def input_records(features: Sequence[Feature], window: int | None) -> tuple[list[LayerRecord], int]:
    """The inputs and their preprocessing, as ``builders/frontend.py`` makes them."""
    steps = window or 1
    records: list[LayerRecord] = [
        LayerRecord(kind="input", name=feature.name, output_elements=steps) for feature in features
    ]
    for feature in features:
        if feature.type != "category":
            continue
        width = _channels(feature)
        records.append(
            LayerRecord(
                kind="constant", name=f"{feature.name}_onehot", kernel_elements=feature.vocabulary
            )
        )
        records.append(
            LayerRecord(
                kind="dense",
                name=f"{feature.name}_embedding",
                kernel_elements=(feature.vocabulary + 1) * width,
                input_elements=steps * (feature.vocabulary + 1),
                output_elements=steps * width,
            )
        )
    channels = sum(_channels(feature) for feature in features)
    if len(features) > 1:
        records.append(
            LayerRecord(
                kind="concat",
                name="features",
                input_elements=steps * channels,
                output_elements=steps * channels,
            )
        )
    return records, channels


def _head(width: int, output_type: str, classes: int) -> list[LayerRecord]:
    """The output layer: the classes of a category, one unit for binary and number, none for an
    anomaly score (``builders/frontend.py``)."""
    if output_type == "anomaly":
        return []
    return [dense_record("output", width, classes if output_type == "category" else 1)]


def body(
    spec: Any,
    params: Mapping[str, Any],
    window: int | None,
    channels: int,
    output_type: str,
    classes: int,
) -> list[LayerRecord]:
    """The template's layers from its own ``layers`` field, then the head of the output type.

    A template without ``layers`` (a third-party one) contributes nothing: no estimate rather than
    a wrong one.
    """
    if spec is None or spec.layers is None:
        return []
    model = spec.parameters.model_validate(dict(params))
    records, width = spec.layers(model, window or 1, channels)
    return [*records, *_head(width, output_type, classes)]  # type: ignore[list-item]


def estimate(
    features: Sequence[Feature],
    window: int | None,
    template: Any,
    params: Mapping[str, Any],
    output_type: str,
    classes: int,
    quantization: str,
    boards: Sequence[Any],
) -> Estimate:
    """The records, the two floors and one verdict per board and resource."""
    records, channels = input_records(features, window)
    records += body(template, params, window, channels, output_type, classes)
    flash, ram = floors(records, quantization)
    return Estimate(tuple(records), flash, ram, tuple(verdicts([flash, ram], boards)))


def _size(count: int) -> str:
    if count >= 1024 * 1024:
        return f"{count / (1024 * 1024):.1f} MB"
    if count >= 1024:
        return f"{count / 1024:.1f} KB"
    return f"{count} B"


def _bar(used: int, available: int | None) -> str:
    if not available:
        return "?" * BAR
    filled = min(BAR, math.ceil(BAR * used / available)) if used else 0
    return "█" * filled + "·" * (BAR - filled)


def panel(result: Estimate, boards: Sequence[Any]) -> list[str]:
    """Text lines: per board, flash and RAM floors against the board's figure."""
    lines: list[str] = []
    for board in boards:
        for resource, floor in (("flash", result.flash), ("RAM", result.ram)):
            verdict = next(
                v
                for v in result.verdicts
                if v.board == board.board and v.resource == floor.resource
            )
            available = verdict.board_bytes
            share = f"{floor.floor_bytes / available:.0%}" if available else "?"
            mark = "✗" if verdict.verdict != "below" else "✓"
            lines.append(
                f"{board.board:<10} {resource:<5} ≥ {_size(floor.floor_bytes):>9} of "
                f"{_size(available or 0):>9}  {_bar(floor.floor_bytes, available)} "
                f"{share:>5} {mark}"
            )
    peak = result.ram.counted_layers[0] if result.ram.counted_layers else "—"
    lines.append(f"RAM peak at {peak}; {LABEL}")
    return lines
