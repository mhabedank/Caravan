"""The fit check before training: lower bounds against every target board (feature 006).

Core arithmetic over plain records — no framework, so it is tested on every Python. Reading those
records from a built Keras model is the ``fit`` stage's job, behind the training extra.

Principle V lets this check pass without deciding whether the budget holds, and only because every
figure it computes is a **lower bound**. Everything below protects that: only layers certain to
remain operators of their own after conversion are counted (dense, convolution, pooling), and
normalisation, activation, reshaping and dropout layers are not — a normalisation folds into its
convolution, a ReLU fuses into it, a Flatten may run in place, and counting any of them could make a
"floor" exceed the truth. A model this check stops can never fit that board; a model it passes is
still owed the real footprint gate (contracts/fit-check.md).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from caravan.manifest.errors import RULE_FLOOR_EXCEEDS_BOARD, run_rule_error

#: Layer kinds certain to remain an operator of their own after conversion.
COUNTED_KINDS: tuple[str, ...] = ("dense", "conv", "pooling")

#: Bytes per element by the stated quantization: kernel, bias, activation. At int8 the converter
#: stores kernels as int8 and biases as int32; at float16 weights are halved and activations stay
#: float32; with no quantization everything is float32.
ELEMENT_BYTES: dict[str, tuple[int, int, int]] = {
    "int8": (1, 4, 1),
    "float16": (2, 2, 4),
    "none": (4, 4, 4),
}

FLASH_METHOD = (
    "kernel and bias elements of every dense and convolution layer at the stated quantization's "
    "element size; normalisation layers are not counted, because they fold into the convolution"
)
RAM_METHOD = (
    "the largest input plus output of a dense, convolution or pooling layer at the stated "
    "quantization's activation size; layers that may vanish, be fused or run in place are not "
    "counted"
)
NOT_A_FIT_CLAIM = (
    "A pass means only that no lower bound exceeds a board. Whether the model fits is established "
    "after quantization and by emulated verification."
)


@dataclass(frozen=True)
class LayerRecord:
    """One layer of a built model, reduced to what the floors need. Element counts at batch one."""

    kind: str
    name: str
    kernel_elements: int = 0
    bias_elements: int = 0
    input_elements: int = 0
    output_elements: int = 0


@dataclass(frozen=True)
class FitFloor:
    resource: str
    floor_bytes: int
    method: str
    #: For flash, every layer that contributed; for ram, the layer that sets the peak.
    counted_layers: tuple[str, ...]


@dataclass(frozen=True)
class FitVerdict:
    board: str
    resource: str
    floor_bytes: int
    board_bytes: int | None
    board_source: str | None
    #: ``below``, ``exceeds``, or ``unknown`` when the board states no figure — which fails.
    verdict: str
    shortfall_bytes: int | None = None

    def line(self) -> str:
        if self.verdict == "unknown":
            return f"{self.board} {self.resource}: the board description states no figure"
        return (
            f"{self.board} {self.resource}: the floor is {self.floor_bytes:,} bytes and the board "
            f"has {self.board_bytes:,} (short by {self.shortfall_bytes:,})"
        )


def floors(records: Sequence[LayerRecord], quantization: str) -> tuple[FitFloor, FitFloor]:
    """The weight floor (flash) and the working-memory floor (ram) of one model."""
    kernel_bytes, bias_bytes, activation_bytes = ELEMENT_BYTES[quantization]

    weighted = [record for record in records if record.kind in ("dense", "conv")]
    flash = FitFloor(
        resource="flash",
        floor_bytes=sum(
            record.kernel_elements * kernel_bytes + record.bias_elements * bias_bytes
            for record in weighted
        ),
        method=FLASH_METHOD,
        counted_layers=tuple(record.name for record in weighted),
    )

    counted = [record for record in records if record.kind in COUNTED_KINDS]
    if counted:
        peak = max(counted, key=lambda record: record.input_elements + record.output_elements)
        ram = FitFloor(
            resource="ram",
            floor_bytes=(peak.input_elements + peak.output_elements) * activation_bytes,
            method=RAM_METHOD,
            counted_layers=(peak.name,),
        )
    else:
        ram = FitFloor("ram", 0, RAM_METHOD, ())
    return flash, ram


def verdicts(model_floors: Sequence[FitFloor], boards: Sequence[Any]) -> list[FitVerdict]:
    """One verdict per board and resource, against the board description's own figure."""
    out: list[FitVerdict] = []
    for board in boards:
        for floor in model_floors:
            figure = getattr(board, f"{floor.resource}_kb", None)
            source = board.sources.get(f"{floor.resource}_kb")
            if figure is None:
                out.append(
                    FitVerdict(
                        board.board, floor.resource, floor.floor_bytes, None, source, "unknown"
                    )
                )
                continue
            available = int(figure * 1024)
            exceeds = floor.floor_bytes > available
            out.append(
                FitVerdict(
                    board=board.board,
                    resource=floor.resource,
                    floor_bytes=floor.floor_bytes,
                    board_bytes=available,
                    board_source=source,
                    verdict="exceeds" if exceeds else "below",
                    shortfall_bytes=floor.floor_bytes - available if exceeds else None,
                )
            )
    return out


def check(
    records: Sequence[LayerRecord], quantization: str, boards: Sequence[Any]
) -> dict[str, Any]:
    """The record of a pass, or rule F-1 naming every board and resource that fails."""
    model_floors = floors(records, quantization)
    found = verdicts(model_floors, boards)
    failing = [verdict for verdict in found if verdict.verdict != "below"]
    if failing:
        count = len({verdict.board for verdict in failing})
        run_rule_error(
            RULE_FLOOR_EXCEEDS_BOARD,
            "export.targets",
            (
                f"the built model cannot fit {count} target board{'s' if count != 1 else ''} "
                "before any training: a floor is a lower bound, so no training can make this model "
                "fit that board"
            ),
            found=[verdict.line() for verdict in failing],
        )
    return {
        "provenance": "estimated",
        "quantization": quantization,
        "floors": [
            {**asdict(floor), "counted_layers": list(floor.counted_layers)}
            for floor in model_floors
        ],
        "verdicts": [asdict(verdict) for verdict in found],
        "not_a_fit_claim": NOT_A_FIT_CLAIM,
    }
