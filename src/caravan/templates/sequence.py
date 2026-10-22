"""How long a sequence is after a block, and where a configuration stops fitting.

Nine lines of arithmetic that decide whether a refusal can be trusted. They are in the core and not
behind the training extra for two reasons: a manifest is validated without a framework, and this is
the part most worth testing on its own.

The formulas were verified against the framework rather than recalled, on fourteen cases including
the two it refuses outright (feature 005, research R5). A wrong formula fails in one of two bad
ways — it refuses a configuration that would have worked, or it lets one through to die inside the
framework with a shape error the author cannot act on — and both are worse than no check.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class _DoesNotFit:
    """The one value that means "this block cannot be applied to this length".

    A sentinel rather than ``None`` because ``None`` is already a legitimate value for "no pooling"
    in a block, and rather than an exception because walking the blocks wants to *report* where it
    stopped, not unwind.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return "DOES_NOT_FIT"

    def __bool__(self) -> bool:
        return False


#: Returned by both functions below when the block cannot be applied.
DOES_NOT_FIT = _DoesNotFit()

Length = int | _DoesNotFit


def length_after_conv(length: int, *, kernel: int, stride: int, padding: str) -> Length:
    """The sequence length after one convolution.

    ``same`` padding never shortens below the stride, which is why a window of 3 survives a kernel
    of 5: the padding is what makes it survive.
    """
    if padding == "same":
        return math.ceil(length / stride)
    if length < kernel:
        return DOES_NOT_FIT
    return math.floor((length - kernel) / stride) + 1


def length_after_pool(length: int, pool: int) -> Length:
    """The sequence length after downsampling, or ``DOES_NOT_FIT`` if nothing would be left."""
    if length < pool:
        return DOES_NOT_FIT
    reduced = math.floor(length / pool)
    return reduced if reduced > 0 else DOES_NOT_FIT


@dataclass(frozen=True)
class WalkOutcome:
    """Where a walk through the blocks got to.

    ``failed_block`` is one-based, because it is written into a message a person reads, and
    ``length_there`` is the length when that block was reached — the two things a refusal needs in
    order to be actionable.
    """

    fits: bool
    length_there: int
    failed_block: int | None = None


def walk(window: int, blocks: Sequence[Mapping[str, Any]]) -> WalkOutcome:
    """Run a window through a sequence of blocks and report where it stopped.

    Each block is read by key — ``kernel``, ``stride``, ``padding``, ``pool`` — so that this
    function needs no import of the template that happens to define them. A fold over no blocks
    returns the window, because a total function is easier to reason about than one with a special
    case at zero.
    """
    length: int = window
    for position, block in enumerate(blocks, start=1):
        after = length_after_conv(
            length,
            kernel=int(block["kernel"]),
            stride=int(block.get("stride", 1)),
            padding=str(block.get("padding", "valid")),
        )
        if after is DOES_NOT_FIT:
            return WalkOutcome(fits=False, length_there=length, failed_block=position)
        length = int(after)

        pool = block.get("pool")
        if pool:
            pooled = length_after_pool(length, int(pool))
            if pooled is DOES_NOT_FIT:
                return WalkOutcome(fits=False, length_there=length, failed_block=position)
            length = int(pooled)
    return WalkOutcome(fits=True, length_there=length)


def smallest_window(blocks: Sequence[Mapping[str, Any]], *, limit: int = 100_000) -> int | None:
    """The shortest window the blocks fit in, found by walking rather than by estimating.

    This is what the refusal offers the author, so it has to be right: an earlier draft of the
    documents guessed 26 for a configuration whose answer is 23. Searching upward is crude and
    costs microseconds on the only sizes that occur.
    """
    for window in range(1, limit + 1):
        if walk(window, blocks).fits:
            return window
    return None  # pragma: no cover - no realistic configuration needs 100,000 samples
