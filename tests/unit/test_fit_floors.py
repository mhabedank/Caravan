"""The fit check's arithmetic, on hand-built layer records (feature 006, contracts/fit-check.md).

Core arithmetic, so it runs on every Python with no framework. The property everything rests on: a
floor counts only what is certain to exist after conversion, so it is a lower bound — and a model
it stops can never fit the board that stopped it (Principle V).
"""

from __future__ import annotations

import pytest

from caravan.manifest.errors import RULE_FLOOR_EXCEEDS_BOARD, RunRuleFailure
from caravan.targets.fit import (
    NOT_A_FIT_CLAIM,
    LayerRecord,
    check,
    floors,
    verdicts,
)
from caravan.targets.registry import default_registry

DENSE = LayerRecord(
    "dense",
    "hidden_1",
    kernel_elements=320 * 32,
    bias_elements=32,
    input_elements=320,
    output_elements=32,
)
OUTPUT = LayerRecord(
    "dense",
    "output",
    kernel_elements=32 * 4,
    bias_elements=4,
    input_elements=32,
    output_elements=4,
)
FLATTEN = LayerRecord("excluded", "flatten", input_elements=320, output_elements=320)
CONV = LayerRecord(
    "conv",
    "conv_1",
    kernel_elements=5 * 5 * 16,
    bias_elements=16,
    input_elements=64 * 5,
    output_elements=30 * 16,
)
POOL = LayerRecord("pooling", "pool_1", input_elements=30 * 16, output_elements=15 * 16)


def board(identifier: str):
    found = default_registry().get(identifier)
    assert found is not None
    return found


@pytest.mark.parametrize(
    ("quantization", "kernel", "bias"), [("int8", 1, 4), ("float16", 2, 2), ("none", 4, 4)]
)
def test_the_weight_floor_counts_kernels_and_biases_at_the_stated_size(
    quantization: str, kernel: int, bias: int
) -> None:
    flash, _ = floors((DENSE, OUTPUT, FLATTEN), quantization)
    assert flash.resource == "flash"
    assert flash.floor_bytes == (320 * 32 + 32 * 4) * kernel + (32 + 4) * bias
    assert flash.counted_layers == ("hidden_1", "output")


@pytest.mark.parametrize(("quantization", "size"), [("int8", 1), ("float16", 4), ("none", 4)])
def test_the_memory_floor_is_the_largest_input_plus_output(quantization: str, size: int) -> None:
    _, ram = floors((CONV, POOL, DENSE), quantization)
    # conv_1: 320 + 480 = 800; pool_1: 480 + 240 = 720; hidden_1: 320 + 32 = 352.
    assert ram.floor_bytes == 800 * size
    assert ram.counted_layers == ("conv_1",)


def test_excluded_layers_never_contribute() -> None:
    # A Flatten may run in place, a ReLU is fused into its convolution: counting either could make
    # the floor exceed the truth, and then the check could stop a model that fits.
    big = LayerRecord("excluded", "relu", input_elements=10**6, output_elements=10**6)
    flash, ram = floors((DENSE, big), "int8")
    assert ram.counted_layers == ("hidden_1",)
    assert flash.counted_layers == ("hidden_1",)


def test_a_model_with_nothing_counted_has_floors_of_zero() -> None:
    flash, ram = floors((FLATTEN,), "int8")
    assert flash.floor_bytes == 0
    assert ram.floor_bytes == 0


def test_a_floor_within_every_board_passes_with_estimated_figures() -> None:
    record = check((DENSE, OUTPUT), "int8", [board("s32k144"), board("esp32")])
    assert record["provenance"] == "estimated"
    assert record["not_a_fit_claim"] == NOT_A_FIT_CLAIM
    assert {(v["board"], v["resource"]) for v in record["verdicts"]} == {
        ("s32k144", "flash"),
        ("s32k144", "ram"),
        ("esp32", "flash"),
        ("esp32", "ram"),
    }
    assert all(v["verdict"] == "below" for v in record["verdicts"])
    assert all(v["board_source"] for v in record["verdicts"])


def test_a_floor_above_a_board_fails_naming_every_failing_board_and_resource() -> None:
    # 320 x 2048 int8 weights = 655,360 bytes, above the s32k144's 524,288 and within the others.
    wide = LayerRecord(
        "dense",
        "hidden_1",
        kernel_elements=320 * 2048,
        bias_elements=2048,
        input_elements=320,
        output_elements=2048,
    )
    with pytest.raises(RunRuleFailure) as caught:
        check((wide,), "int8", [board("s32k144"), board("stm32h743"), board("esp32")])
    finding = caught.value.finding
    assert finding.rule == RULE_FLOOR_EXCEEDS_BOARD
    assert finding.path == "export.targets"
    assert len(finding.found) == 1
    assert finding.found[0].startswith("s32k144 flash:")
    assert "no training can make" in finding.problem


def test_verdicts_record_the_shortfall() -> None:
    flash, ram = floors((DENSE,), "int8")
    tiny = board("s32k144").model_copy(update={"flash_kb": 1.0, "ram_kb": 0.25})
    found = verdicts((flash, ram), [tiny])
    by_resource = {v.resource: v for v in found}
    assert by_resource["flash"].verdict == "exceeds"
    assert by_resource["flash"].shortfall_bytes == flash.floor_bytes - 1024
    assert by_resource["ram"].verdict == "exceeds"
    assert by_resource["ram"].shortfall_bytes == ram.floor_bytes - 256


def test_a_board_without_a_figure_fails_rather_than_passes() -> None:
    # Unknown is not within budget (Principle V). The board schema makes this unreachable today;
    # the check does not depend on that staying true.
    flash, ram = floors((DENSE,), "int8")
    unknown = board("s32k144").model_copy(update={"ram_kb": None})
    found = {v.resource: v for v in verdicts((flash, ram), [unknown])}
    assert found["ram"].verdict == "unknown"
    with pytest.raises(RunRuleFailure):
        check((DENSE,), "int8", [unknown])
