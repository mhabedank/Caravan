"""The runner skeleton: a handover, with its limits written into it."""

from __future__ import annotations

from dataclasses import dataclass

from caravan.export import skeleton
from caravan.export.c_array import array_name
from caravan.runtime.flatbuffer import OperatorRecord
from caravan.targets.registry import default_registry


@dataclass
class Graph:
    operators: tuple
    input_shape: tuple
    output_shape: tuple
    working_memory_floor: int


GRAPH = Graph(
    operators=(
        OperatorRecord(name="RESHAPE", builtin_code=22, version=1, nodes=1),
        OperatorRecord(name="FULLY_CONNECTED", builtin_code=9, version=4, nodes=3),
        OperatorRecord(name="SOFTMAX", builtin_code=25, version=2, nodes=1),
    ),
    input_shape=(1, 64, 5),
    output_shape=(1, 4),
    working_memory_floor=640,
)


def generate(identifier: str = "stm32h743") -> str:
    board = default_registry().get(identifier)
    assert board is not None
    return skeleton.generate(
        board=board,
        graph=GRAPH,
        model_stem="model_data",
        array_name=array_name("model_data"),
        accelerated=2,
        operators_total=3,
        input_name="frames",
        output_name="attack",
    )


def test_it_names_the_runtime_the_board_declares() -> None:
    board = default_registry().get("stm32h743")
    assert board is not None
    assert board.toolchain.runtime in generate()


def test_it_references_both_generated_headers() -> None:
    text = generate()
    assert '#include "model_data.h"' in text
    assert '#include "resolver.h"' in text
    assert "g_model_data" in text


def test_the_arena_is_a_named_constant_with_the_floor_in_its_comment() -> None:
    text = generate()
    assert "constexpr int kArenaBytes" in text
    assert "640 bytes" in text


def test_it_says_the_floor_is_not_the_figure_the_board_needs() -> None:
    # The sentence is the deliverable here, not the number.
    text = generate()
    assert "NOT the figure this board needs" in text
    assert "scratch buffers" in text


def test_it_says_caravan_has_not_built_it() -> None:
    assert "has NOT compiled, linked or run this file" in generate()


def test_the_arena_start_is_above_the_floor_and_a_round_number() -> None:
    for floor in (0, 1, 640, 4096, 100_000):
        start = skeleton.arena_start(floor)
        assert start >= floor
        assert start % skeleton.ARENA_GRANULARITY == 0


def test_each_board_gets_its_own_compiler_and_library() -> None:
    arm = generate("stm32h743")
    xtensa = generate("esp32")
    assert "arm-none-eabi-gcc" in arm and "cmsis-nn" in arm
    assert "arm-none-eabi-gcc" not in xtensa and "esp-nn" in xtensa


def test_it_is_deterministic() -> None:
    assert generate() == generate()


def test_the_clock_reads_as_a_number_a_person_would_write() -> None:
    assert "480 MHz" in generate("stm32h743")


def test_it_binds_by_the_named_positions_never_by_a_literal_index() -> None:
    # Principle VIII in 3.0.0: a runner binds by name. The converter does not keep the declared
    # order (feature 006, research R4), so a literal 0 would be right only by luck.
    for identifier in ("s32k144", "stm32h743", "esp32"):
        text = generate(identifier)
        assert "input(0)" not in text and "output(0)" not in text
        assert "interpreter.input(g_model_data_input_frames)" in text
        assert "interpreter.output(g_model_data_output_attack)" in text
