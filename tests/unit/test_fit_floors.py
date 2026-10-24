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


# --- feature 008: inputs, vocabularies and the concatenation of the features (T029) -------------

#: The typed pilot's front: four numbers and a category of 32 codes, window 64, an embedding of 4.
TYPED_INPUTS = tuple(
    LayerRecord("input", name, output_elements=64) for name in ("can_id", "dlc", "b0", "b1", "b2")
)
VOCABULARY = LayerRecord(
    "constant", "can_id_onehot", kernel_elements=32, input_elements=64, output_elements=64 * 33
)
EMBEDDING = LayerRecord(
    "dense",
    "can_id_embedding",
    kernel_elements=33 * 4,
    bias_elements=0,
    input_elements=64 * 33,
    output_elements=64 * 4,
)
CONCAT = LayerRecord("concat", "features", input_elements=64 * 4 + 4 * 64, output_elements=64 * 8)
TYPED_DENSE = LayerRecord(
    "dense",
    "hidden_1",
    kernel_elements=512 * 32,
    bias_elements=32,
    input_elements=512,
    output_elements=32,
)


def typed_records() -> tuple[LayerRecord, ...]:
    return (*TYPED_INPUTS, VOCABULARY, EMBEDDING, CONCAT, TYPED_DENSE, OUTPUT)


def test_the_flash_floor_counts_the_vocabulary_and_the_embedding() -> None:
    flash, _ = floors(typed_records(), "int8")
    expected = (
        32 * 4  # the vocabulary, int32
        + 33 * 4  # the embedding, an int8 dense kernel without bias
        + 512 * 32
        + 32 * 4  # the first hidden layer
        + 32 * 4
        + 4 * 4  # the output layer
    )
    assert flash.floor_bytes == expected
    assert "can_id_onehot" in flash.counted_layers and "can_id_embedding" in flash.counted_layers


def test_the_ram_floor_is_the_larger_of_the_inputs_and_the_peak_layer() -> None:
    # The one-hot into the embedding is 64 x 33 values in and 64 x 4 out, 2,368 int8 bytes, more
    # than the five inputs' 1,280 bytes at 4 bytes per value.
    _, ram = floors(typed_records(), "int8")
    assert ram.floor_bytes == 64 * 33 + 64 * 4
    assert ram.counted_layers == ("can_id_embedding",)


def test_the_inputs_set_the_ram_floor_when_they_are_the_peak() -> None:
    # Five inputs of 64 values at 4 bytes: 1,280 bytes, live together before the first operator.
    small = LayerRecord("dense", "head", kernel_elements=8, input_elements=2, output_elements=4)
    _, ram = floors((*TYPED_INPUTS, small), "int8")
    assert ram.floor_bytes == 5 * 64 * 4
    assert set(ram.counted_layers) == {"can_id", "dlc", "b0", "b1", "b2"}


def test_a_large_concatenation_sets_the_ram_floor_when_it_is_the_peak() -> None:
    wide = LayerRecord("concat", "features", input_elements=4000, output_elements=4000)
    _, ram = floors((*TYPED_INPUTS, wide), "int8")
    assert ram.floor_bytes == 8000
    assert ram.counted_layers == ("features",)
