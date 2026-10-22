"""What the conv1d template's operators cost on each built-in board.

The interesting half is the fallback. `MEAN` is what the reducing head converts to, and neither
built-in accelerated library supplies a kernel for it — so the head that saves three quarters of the
parameters pays for them with an operator on the reference implementation. This test is where that
claim is checked rather than remembered.
"""

from __future__ import annotations

import pytest

from caravan.runtime.flatbuffer import OperatorRecord
from caravan.targets.kernels import coverage
from caravan.targets.registry import default_registry

#: The operator set a conv1d with the reducing head produces, measured on the committed fixture.
CONV1D_AVERAGE = tuple(
    OperatorRecord(name=name, builtin_code=code, version=1, nodes=nodes)
    for name, code, nodes in (
        ("RESHAPE", 22, 2),
        ("CONV_2D", 3, 2),
        ("MAX_POOL_2D", 17, 1),
        ("MEAN", 40, 1),
        ("FULLY_CONNECTED", 9, 1),
        ("SOFTMAX", 25, 1),
    )
)

BOARDS = ("s32k144", "stm32h743", "esp32")


@pytest.mark.parametrize("identifier", BOARDS)
def test_every_operator_has_a_verdict_with_its_provenance(identifier: str) -> None:
    board = default_registry().get(identifier)
    assert board is not None
    verdicts = coverage(CONV1D_AVERAGE, board)
    assert len(verdicts) == len(CONV1D_AVERAGE)
    for verdict in verdicts:
        assert verdict.source and verdict.read_on


@pytest.mark.parametrize("identifier", BOARDS)
def test_the_convolution_and_the_pooling_are_accelerated_everywhere(identifier: str) -> None:
    board = default_registry().get(identifier)
    assert board is not None
    by_name = {v.operator: v for v in coverage(CONV1D_AVERAGE, board)}
    for operator in ("CONV_2D", "MAX_POOL_2D", "FULLY_CONNECTED", "SOFTMAX"):
        assert by_name[operator].accelerated, f"{operator} on {identifier}"


@pytest.mark.parametrize("identifier", BOARDS)
def test_the_reduction_falls_back_on_every_board(identifier: str) -> None:
    # The cost of the `average` head, stated per board with its source.
    board = default_registry().get(identifier)
    assert board is not None
    by_name = {v.operator: v for v in coverage(CONV1D_AVERAGE, board)}
    assert not by_name["MEAN"].accelerated
    assert "reference implementation" in by_name["MEAN"].evidence
    assert by_name["MEAN"].source and by_name["MEAN"].read_on


@pytest.mark.parametrize("identifier", BOARDS)
def test_four_of_the_six_are_accelerated(identifier: str) -> None:
    # The number the export prints, asserted so the summary cannot drift from the data.
    board = default_registry().get(identifier)
    assert board is not None
    verdicts = coverage(CONV1D_AVERAGE, board)
    assert sum(1 for v in verdicts if v.accelerated) == 4


def test_the_flattening_head_avoids_the_fallback() -> None:
    # The other side of the trade: without the reduction, only the reshape falls back.
    board = default_registry().get("stm32h743")
    assert board is not None
    flattening = tuple(o for o in CONV1D_AVERAGE if o.name != "MEAN")
    verdicts = coverage(flattening, board)
    falling_back = {v.operator for v in verdicts if not v.accelerated}
    assert falling_back == {"RESHAPE"}
