"""What this feature may not claim, asserted over the artifacts it writes.

Three claims are forbidden and each for its own reason:

* that the skeleton was built — nothing here cross-compiles it;
* that an accelerated kernel will be *selected* — that depends on the build;
* any figure about a target's latency, flash use or memory use — this stage reads a file on a
  desktop.

And one is required: the working-memory figure never travels without its method and without the
sentence saying what it leaves out.
"""

from __future__ import annotations

import json

from caravan.export.artifacts import FLOOR_CAVEAT, RunnerRequirements
from caravan.export.skeleton import generate
from caravan.runtime.flatbuffer import FLOOR_METHOD, OperatorRecord
from caravan.targets.registry import default_registry

#: Words that would turn a lookup into a promise about speed, or a desktop computation into a
#: statement about hardware. Written with their surrounding spaces where the bare substring would
#: match ordinary C++ — " ms " unstripped is a unit, stripped it is half the identifiers in the
#: file, and a check that matches everything checks nothing.
FORBIDDEN = (
    "faster",
    "speedup",
    "latency",
    "milliseconds",
    " ms ",
    "throughput",
    "energy",
    "flash use",
    "will be selected",
    "compiled successfully",
    "builds cleanly",
    "verified on",
)


class Graph:
    operators = (
        OperatorRecord(name="RESHAPE", builtin_code=22, version=1, nodes=1),
        OperatorRecord(name="FULLY_CONNECTED", builtin_code=9, version=4, nodes=3),
    )
    input_shape = (1, 64, 5)
    output_shape = (1, 4)
    working_memory_floor = 640


def test_the_skeleton_claims_no_build() -> None:
    board = default_registry().get("stm32h743")
    assert board is not None
    text = generate(
        board=board,
        graph=Graph(),
        model_stem="model_data",
        array_name="g_model_data",
        accelerated=1,
        operators_total=2,
        inputs=[{"name": "speed", "element_type": "float32", "shape": [1, 64], "position": 0}],
        output={"name": "state", "element_type": "float32", "shape": [1, 4], "position": 0},
    )
    assert "has NOT compiled, linked or run this file" in text
    lowered = text.lower()
    for phrase in FORBIDDEN:
        assert phrase not in lowered, f"the skeleton claims {phrase!r}"


def test_the_floor_never_travels_alone() -> None:
    requirement = RunnerRequirements(
        runtime="tflm",
        operators=("RESHAPE",),
        working_memory_floor=640,
        floor_method=FLOOR_METHOD,
    )
    recorded = requirement.as_dict()
    assert recorded["floor_method"]
    assert recorded["floor_is_not_the_requirement"] == FLOOR_CAVEAT
    assert "not the figure" in recorded["floor_is_not_the_requirement"]
    assert "emulated verification" in recorded["floor_is_not_the_requirement"]


def test_the_figure_is_named_a_floor_and_not_an_arena() -> None:
    # "arena" is the runtime's word for the thing this stage cannot measure, so the field names
    # avoid it: a reader scanning for `arena` should not find a number here.
    recorded = json.dumps(
        RunnerRequirements(
            runtime="tflm",
            operators=("RESHAPE",),
            working_memory_floor=640,
            floor_method=FLOOR_METHOD,
        ).as_dict()
    )
    assert "floor" in recorded
    assert "arena_bytes" not in recorded


def test_a_coverage_verdict_is_about_a_kernel_existing_not_about_speed() -> None:
    from caravan.targets.kernels import coverage

    board = default_registry().get("esp32")
    assert board is not None
    for verdict in coverage(Graph.operators, board):
        lowered = json.dumps(verdict.as_dict()).lower()
        for phrase in FORBIDDEN:
            assert phrase not in lowered, f"a coverage verdict claims {phrase!r}"
