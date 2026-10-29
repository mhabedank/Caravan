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

#: Layer kinds certain to remain an operator of their own after conversion. The concatenation of
#: the features joins every input's channels (feature 008) and is a CONCATENATION on the target.
COUNTED_KINDS: tuple[str, ...] = ("dense", "conv", "pooling", "concat")

#: Bytes per element of a model input since feature 008: float32 for a number, int32 for a code
#: (research R2, R11), whatever the quantization of the rest.
INPUT_ELEMENT_BYTES = 4
#: An image arrives as raw 8-bit pixels (feature 010, research R6).
IMAGE_ELEMENT_BYTES = 1
#: Bytes per element of a preprocessing constant kept in flash: a category's vocabulary is int32.
CONSTANT_ELEMENT_BYTES = 4

#: Bytes per element by the stated quantization: kernel, bias, activation. At int8 the converter
#: stores kernels as int8 and biases as int32; at float16 weights are halved and activations stay
#: float32; with no quantization everything is float32.
ELEMENT_BYTES: dict[str, tuple[int, int, int]] = {
    "int8": (1, 4, 1),
    "float16": (2, 2, 4),
    "none": (4, 4, 4),
}

FLASH_METHOD = (
    "kernel and bias elements of every dense and convolution layer (a category's embedding is a "
    "dense kernel) at the stated quantization's element size, and every category vocabulary at "
    "4 bytes per entry; normalisation layers are not counted, because they fold into the "
    "convolution"
)
RAM_METHOD = (
    "the larger of: every model input together at its element size (4 bytes; 1 for an image's "
    "pixels), or the largest input plus "
    "output of a dense, convolution, pooling or concatenation layer at the stated quantization's "
    "activation size; layers that may vanish, be fused or run in place are not counted"
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
    #: Bytes per element of a model input: 4, or 1 for an image (feature 010).
    element_bytes: int = INPUT_ELEMENT_BYTES


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
    constants = [record for record in records if record.kind == "constant"]
    flash = FitFloor(
        resource="flash",
        floor_bytes=sum(
            record.kernel_elements * kernel_bytes + record.bias_elements * bias_bytes
            for record in weighted
        )
        + sum(record.kernel_elements * CONSTANT_ELEMENT_BYTES for record in constants),
        method=FLASH_METHOD,
        counted_layers=tuple(record.name for record in (*weighted, *constants)),
    )

    # Every model input is allocated at once and filled before the first operator runs.
    inputs = [record for record in records if record.kind == "input"]
    inputs_bytes = sum(record.output_elements * record.element_bytes for record in inputs)
    counted = [record for record in records if record.kind in COUNTED_KINDS]
    peak = (
        max(counted, key=lambda record: record.input_elements + record.output_elements)
        if counted
        else None
    )
    peak_bytes = (
        (peak.input_elements + peak.output_elements) * activation_bytes if peak is not None else 0
    )
    if inputs_bytes > peak_bytes:
        ram = FitFloor("ram", inputs_bytes, RAM_METHOD, tuple(record.name for record in inputs))
    elif peak is not None:
        ram = FitFloor("ram", peak_bytes, RAM_METHOD, (peak.name,))
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
