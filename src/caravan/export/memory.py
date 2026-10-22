"""What can honestly be said about a model's working memory from the file alone.

Two figures, bounding different things in different directions, and the difference between them is
the reason this module exists rather than one line summing tensor sizes:

* ``read_write_total`` — the sum of the non-constant tensors. An **upper** bound on the tensor
  area, because a runtime reuses one buffer for tensors whose lifetimes do not overlap. It is not a
  bound on the whole arena in either direction, because scratch buffers are not in it.
* ``peak_live`` — the largest amount live at one moment. A **lower** bound on the arena: no planner,
  however good, can hold less than what is live at once.

The export publishes the second and calls it a floor. Publishing the first under that name was the
first design here, and it was wrong — recorded in ``specs/004-export/research.md`` R2 rather than
quietly fixed, because the arithmetic is the argument.

Core, with no dependency at all: the claim most worth checking should be checkable in an
installation with no extra installed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class TensorLifetime:
    """One non-constant tensor, and the span of nodes over which it must exist.

    ``first_node`` is ``-1`` for a graph input, which exists before any operator runs, and
    ``last_node`` is the node count for a graph output, which must survive the last one. Both are
    inclusive.
    """

    index: int
    bytes: int
    first_node: int
    last_node: int

    def live_at(self, node: int) -> bool:
        return self.first_node <= node <= self.last_node


def read_write_total(lifetimes: Iterable[TensorLifetime]) -> int:
    """The sum of the non-constant tensors: an upper bound on the tensor area."""
    return sum(lifetime.bytes for lifetime in lifetimes)


def peak_live(lifetimes: Iterable[TensorLifetime], *, nodes: int) -> int:
    """The largest amount live at one node: a floor under the working memory.

    Evaluated at each node rather than at each lifetime boundary because the two agree and the
    first is obvious: a tensor's span is inclusive, so every moment that matters is a node.
    """
    spans = tuple(lifetimes)
    if not spans:
        return 0
    return max(
        (sum(span.bytes for span in spans if span.live_at(node)) for node in range(nodes + 1)),
        default=0,
    )
