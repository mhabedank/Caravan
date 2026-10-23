"""The interface contract as text (feature 006, contracts/interface.md).

Core formatting over plain data, so it runs on every Python. What the numbers are is read from the
model file by ``caravan.runtime.flatbuffer.read_bindings``; what is tested here is how they are
written — and that the same reading always gives the same bytes (FR-027).
"""

from __future__ import annotations

import json

from caravan.export.interface import (
    c_label_literal,
    header_additions,
    interface_document,
    source_additions,
)

MODEL = {"name": "picket-mlp", "version": "0.1.0"}
BINDINGS = [
    {
        "name": "frames",
        "role": "input",
        "position": 0,
        "tensor_index": 0,
        "tensor_name": "serving_default_frames:0",
        "shape": [1, 64, 5],
        "element_type": "int8",
        "scale": 4.0,
        "zero_point": -128,
    },
    {
        "name": "attack",
        "role": "output",
        "position": 0,
        "tensor_index": 7,
        "tensor_name": "StatefulPartitionedCall_1:0",
        "shape": [1, 4],
        "element_type": "int8",
        "scale": 0.00390625,
        "zero_point": -128,
    },
]
INPUT = {"name": "frames", "columns": ["can_id", "dlc", "b0", "b1", "b2"], "window": 64}
OUTPUT = {"name": "attack", "labels": ["dos", "fuzzy", "normal", "replay"]}


def document() -> str:
    return interface_document(MODEL, BINDINGS, INPUT, OUTPUT)


def test_the_document_is_sorted_indented_and_ends_with_a_newline() -> None:
    text = document()
    assert text.endswith("}\n")
    parsed = json.loads(text)
    assert text == json.dumps(parsed, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def test_the_document_says_which_model_and_how_to_bind() -> None:
    parsed = json.loads(document())
    assert parsed["contract_version"] == 1
    assert parsed["model"] == MODEL
    assert "by position" in parsed["runtime_binding"]


def test_the_input_states_its_transformation_including_none() -> None:
    (entry,) = json.loads(document())["inputs"]
    assert entry["position"] == 0 and entry["scale"] == 4.0 and entry["zero_point"] == -128
    assert entry["transformation"] == {
        "kind": "series",
        "columns": ["can_id", "dlc", "b0", "b1", "b2"],
        "window": 64,
        "stride": 64,
        "scaling": "none",
    }


def test_the_output_carries_its_labels_in_unit_order() -> None:
    (entry,) = json.loads(document())["outputs"]
    assert entry["interpretation"] == {
        "kind": "class",
        "labels": ["dos", "fuzzy", "normal", "replay"],
        "decision": "argmax",
    }


def test_a_float_tensor_has_null_scale_and_zero_point() -> None:
    floating = [{**binding, "scale": None, "zero_point": None} for binding in BINDINGS]
    parsed = json.loads(interface_document(MODEL, floating, INPUT, OUTPUT))
    assert parsed["inputs"][0]["scale"] is None
    assert parsed["outputs"][0]["zero_point"] is None


def test_no_window_means_one_record_per_sample() -> None:
    parsed = json.loads(interface_document(MODEL, BINDINGS, {**INPUT, "window": None}, OUTPUT))
    transformation = parsed["inputs"][0]["transformation"]
    assert transformation["window"] is None and transformation["stride"] is None


def test_the_header_names_every_constant() -> None:
    header = header_additions("g_model_data", MODEL, BINDINGS, OUTPUT)
    assert 'constexpr char g_model_data_model_name[] = "picket-mlp";' in header
    assert 'constexpr char g_model_data_model_version[] = "0.1.0";' in header
    assert "constexpr unsigned int g_model_data_input_frames = 0;" in header
    assert "constexpr unsigned int g_model_data_output_attack = 0;" in header
    assert "constexpr unsigned int g_model_data_output_attack_label_count = 4;" in header
    assert "extern const char* const g_model_data_output_attack_labels[];" in header


def test_the_source_defines_the_labels_in_order() -> None:
    source = source_additions("g_model_data", OUTPUT)
    assert source.index('"dos"') < source.index('"fuzzy"') < source.index('"replay"')
    assert "const char* const g_model_data_output_attack_labels[] = {" in source


def test_labels_are_escaped_so_no_hex_escape_swallows_the_next_character() -> None:
    assert c_label_literal('a"b\\c') == '"a\\x22" "b\\x5c" "c"'
    assert c_label_literal("aä") == '"a\\xc3" "\\xa4"'
    assert c_label_literal("normal") == '"normal"'
    # A hex digit after an escape is the case the split exists for.
    assert c_label_literal("\tF") == '"\\x09" "F"'


def test_two_emissions_are_byte_identical() -> None:
    assert document() == document()
    assert header_additions("g_model_data", MODEL, BINDINGS, OUTPUT) == header_additions(
        "g_model_data", MODEL, BINDINGS, OUTPUT
    )
