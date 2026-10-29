"""Where a plane stops fitting a stack of two-dimensional blocks (feature 010, research R3).

A two-dimensional convolution shortens each axis by the same arithmetic a one-dimensional one
shortens its sequence by, independently of the other axis — kernel, stride, padding and pooling
are given per axis. So the plane is walked one axis at a time with ``sequence.py``'s verified
formulas, and nothing here is new arithmetic: only the bookkeeping of which axis is which.

Core: the manifest validates without a framework, and this is checked at validation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from caravan.templates.sequence import smallest_window, walk

#: The axes in the order a plane's shape lists them, and the word a message uses for each.
AXES = ("rows", "columns")


def as_pair(value: Any) -> tuple[int, int] | None:
    """An int or a [rows, columns] pair as a pair; ``None`` stays ``None``."""
    if value is None:
        return None
    if isinstance(value, int):
        return (value, value)
    rows, columns = value
    return (int(rows), int(columns))


def axis_blocks(blocks: Sequence[Mapping[str, Any]], axis: int) -> list[dict[str, Any]]:
    """The blocks as one axis sees them, in the form ``sequence.walk`` reads."""
    out = []
    for block in blocks:
        kernel = as_pair(block["kernel"])
        stride = as_pair(block.get("stride", 1))
        pool = as_pair(block.get("pool"))
        assert kernel is not None and stride is not None
        out.append(
            {
                "kernel": kernel[axis],
                "stride": stride[axis],
                "padding": block.get("padding", "valid"),
                "pool": None if pool is None else pool[axis],
            }
        )
    return out


@dataclass(frozen=True)
class PlaneOutcome:
    """Where a walk through the blocks stopped, on which axis; or the plane left at the end."""

    fits: bool
    axis: str | None = None
    failed_block: int | None = None
    size_there: int | None = None
    kernel_there: int | None = None
    smallest: int | None = None
    #: What remains of each axis after the last block, when every known axis fits.
    final: tuple[int | None, int | None] = (None, None)


def walk_plane(
    rows: int | None, columns: int | None, blocks: Sequence[Mapping[str, Any]]
) -> PlaneOutcome:
    """Walk each known axis through the blocks; report the first axis that does not fit."""
    final: list[int | None] = [None, None]
    for axis, size in enumerate((rows, columns)):
        if size is None:
            continue
        per_axis = axis_blocks(blocks, axis)
        outcome = walk(int(size), per_axis)
        if not outcome.fits:
            position = outcome.failed_block
            assert position is not None
            return PlaneOutcome(
                fits=False,
                axis=AXES[axis],
                failed_block=position,
                size_there=outcome.length_there,
                kernel_there=int(per_axis[position - 1]["kernel"]),
                smallest=smallest_window(per_axis),
            )
        final[axis] = outcome.length_there
    return PlaneOutcome(fits=True, final=(final[0], final[1]))
