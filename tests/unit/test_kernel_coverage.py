"""Accelerated kernel coverage: three outcomes, each stated, none silent.

A board saying `accel: cmsis-nn` is a claim about the build and not about the model. What this
checks is that the claim is broken down per operator, that a fallback is recorded as a fallback,
and that every verdict carries the source somebody read and the day they read it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from caravan.runtime.flatbuffer import OperatorRecord
from caravan.targets.kernels import NO_LIBRARY, coverage, default_libraries, load_directory
from caravan.targets.registry import default_registry
from caravan.targets.schema import Accelerator

MLP = (
    OperatorRecord(name="RESHAPE", builtin_code=22, version=1, nodes=1),
    OperatorRecord(name="FULLY_CONNECTED", builtin_code=9, version=4, nodes=3),
    OperatorRecord(name="SOFTMAX", builtin_code=25, version=2, nodes=1),
)

KERNELS = Path(__file__).resolve().parents[2] / "src" / "caravan" / "targets" / "kernels"


def test_an_operator_with_a_kernel_is_accelerated_with_its_evidence() -> None:
    board = default_registry().get("stm32h743")
    assert board is not None
    verdicts = {verdict.operator: verdict for verdict in coverage(MLP, board)}
    assert verdicts["FULLY_CONNECTED"].accelerated
    assert verdicts["FULLY_CONNECTED"].evidence == "fully_connected.cc"
    assert verdicts["FULLY_CONNECTED"].library == "cmsis-nn"


def test_an_operator_without_one_falls_back_and_says_so() -> None:
    # The silent half of the constitution's concern: an operator with no accelerated kernel uses
    # the reference implementation and nothing announces it.
    board = default_registry().get("stm32h743")
    assert board is not None
    verdicts = {verdict.operator: verdict for verdict in coverage(MLP, board)}
    assert not verdicts["RESHAPE"].accelerated
    assert "reference implementation" in verdicts["RESHAPE"].evidence


def test_a_board_with_no_library_gets_a_stated_verdict_for_every_operator() -> None:
    # Not an absent verdict: there is nothing unknown about a board that accelerates nothing.
    board = default_registry().get("stm32h743")
    assert board is not None
    bare = board.model_copy(update={"accel": NO_LIBRARY})
    verdicts = coverage(MLP, bare)
    assert len(verdicts) == len(MLP)
    assert all(not verdict.accelerated and verdict.library is None for verdict in verdicts)
    assert all("declares no accelerated kernel library" in v.evidence for v in verdicts)


def test_every_verdict_carries_a_source_and_a_date() -> None:
    for identifier in ("s32k144", "stm32h743", "esp32"):
        board = default_registry().get(identifier)
        assert board is not None
        for verdict in coverage(MLP, board):
            assert verdict.source
            assert verdict.read_on


def test_the_two_libraries_differ_which_is_why_coverage_is_per_target() -> None:
    libraries = default_libraries()
    assert set(libraries) == {"cmsis-nn", "esp-nn"}
    assert libraries["cmsis-nn"].operators.keys() != libraries["esp-nn"].operators.keys()
    assert "TRANSPOSE" in libraries["cmsis-nn"].operators
    assert "TRANSPOSE" not in libraries["esp-nn"].operators


def test_every_library_the_schema_admits_has_sourced_data() -> None:
    # This is rule X-5's job, done earlier and better. The rule was written to refuse a board
    # naming a library caravan has no data for; the board schema admits `accel` only from a closed
    # list, so that board cannot exist, and the real risk is somebody widening the list without
    # reading a source. That fails here, in continuous integration, instead of in somebody's run.
    from typing import get_args

    admitted = {value for value in get_args(Accelerator) if value != NO_LIBRARY}
    assert admitted == set(default_libraries()), (
        "every accelerated library a board may declare needs a sourced coverage file"
    )


def test_a_library_file_must_be_named_after_its_library() -> None:
    assert set(load_directory(KERNELS)) == {"cmsis-nn", "esp-nn"}


def test_every_source_file_is_either_mapped_or_listed_as_unmapped() -> None:
    # The honest half of the data: one kernel file can register several operators, so an entry is
    # written only once somebody has read it, and a file nobody has read yet is listed rather than
    # dropped. A file that is in neither list would be a silent omission.
    for library in default_libraries().values():
        mapped = set(library.operators.values())
        assert not (mapped & set(library.unmapped)), (
            f"{library.library}: a file cannot be both mapped and unmapped"
        )


def test_an_unknown_library_raises_rather_than_returning_a_blank_verdict() -> None:
    # Unreachable through a validated board description, which is why X-5 was withdrawn. Asserted
    # anyway: if the schema is ever widened, this fails loudly instead of recording "not
    # accelerated" for a library nobody checked.
    board = default_registry().get("stm32h743")
    assert board is not None
    invented = board.model_copy(update={"accel": "fast-nn"})
    with pytest.raises(KeyError):
        coverage(MLP, invented)
