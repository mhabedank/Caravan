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


def binding(name: str, dtype: str, shape: list[int], position: int) -> dict:
    return {"name": name, "element_type": dtype, "shape": shape, "position": position}


#: Five inputs, as the typed pilot has them: numbers as float32, codes as int32 (feature 008).
INPUTS = [
    binding("b2", "float32", [1, 64], 0),
    binding("can_id", "int32", [1, 64], 1),
    binding("b1", "float32", [1, 64], 2),
    binding("dlc", "float32", [1, 64], 3),
    binding("b0", "float32", [1, 64], 4),
]
OUTPUT = binding("label", "float32", [1, 4], 0)


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
        inputs=INPUTS,
        output=OUTPUT,
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


def test_it_binds_every_input_by_its_named_position_never_by_a_literal_index() -> None:
    # Principle VIII: a runner binds by name. The converter does not keep the manifest's order
    # (feature 006, research R4), so a literal index would be right only by luck.
    for identifier in ("s32k144", "stm32h743", "esp32"):
        text = generate(identifier)
        assert "input(0)" not in text and "output(0)" not in text
        for name in ("b2", "can_id", "b1", "dlc", "b0"):
            assert f"interpreter.input(g_model_data_input_{name})" in text
        assert "interpreter.output(g_model_data_output_label)" in text


def test_each_input_is_filled_with_raw_values_of_its_own_type() -> None:
    # SC-005 (feature 008): float for a number, int32 for a code, nothing scaled by the firmware.
    text = generate()
    assert "Fill_can_id(interpreter.input(g_model_data_input_can_id)->data.i32, 64);" in text
    assert "Fill_dlc(interpreter.input(g_model_data_input_dlc)->data.f, 64);" in text
    assert "static void Fill_can_id(int32_t* values, int count);" in text
    assert "static void UseOutput(const float* output, int count);" in text


def test_it_contains_no_scale_zero_point_mean_or_vocabulary() -> None:
    # SC-005: everything that turns a raw value into what the network sees is inside the model.
    text = generate().lower()
    for word in ("scale", "zero_point", "zero point", "mean", "vocab", "int8_t*"):
        assert word not in text, word


# --- feature 009: the arena a board actually used, from the runtime ----------------------------


def test_it_reports_the_arena_the_runtime_used_after_allocation() -> None:
    # Principle IV: the runner obtains the figure from the runtime rather than recomputing it.
    text = generate()
    assert "static void ReportArena(size_t bytes);" in text
    allocate = text.index("AllocateTensors()")
    report = text.index("ReportArena(interpreter.arena_used_bytes());")
    assert report > allocate


def test_it_says_the_reported_arena_is_measured_on_the_board() -> None:
    text = generate()
    assert "measured" in text
    assert "on the board it runs on" in text
