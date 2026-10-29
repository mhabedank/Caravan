"""The interface contract as text (features 006 and 008, contracts/interface.md).

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

MODEL = {"name": "picket-mlp", "version": "0.2.0"}


def binding(name: str, role: str, position: int, dtype: str, shape: list[int]) -> dict:
    return {
        "name": name,
        "role": role,
        "position": position,
        "tensor_index": position,
        "tensor_name": f"serving_default_{name}:0",
        "shape": shape,
        "element_type": dtype,
        "scale": None,
        "zero_point": None,
    }


#: A five-input pilot, in the order the converter gave it (not the manifest's), and its output.
BINDINGS = [
    binding("b2", "input", 0, "float32", [1, 64]),
    binding("can_id", "input", 1, "int32", [1, 64]),
    binding("brake", "input", 2, "int32", [1, 64]),
    binding("gear", "input", 3, "int32", [1, 64]),
    binding("dlc", "input", 4, "float32", [1, 64]),
    binding("label", "output", 0, "float32", [1, 4]),
]
NUMBER = {"normalization": "zscore", "shift": 7.0, "scale": 2.0, "fill": 0.0}
FEATURES = [
    {
        "name": "can_id",
        "type": "category",
        "preprocessing": {
            "fitted": {
                "vocab": [291, 608],
                "codes": [291, 608],
                "text_codes": None,
                "cut": 2,
                "unknown_index": 0,
                "missing": -1,
            }
        },
        "encoder": {"type": "dense", "embedding_size": 2},
    },
    {
        "name": "gear",
        "type": "category",
        "preprocessing": {
            "fitted": {
                "vocab": ["drive", "park"],
                "codes": [1, 2],
                "text_codes": {"drive": 1, "park": 2},
                "cut": 0,
                "unknown_index": 0,
                "missing": 0,
            }
        },
        "encoder": {"type": "onehot"},
    },
    {
        "name": "brake",
        "type": "binary",
        "preprocessing": {
            "fitted": {"spellings": {"off": 0, "on": 1}, "true_spelling": "on", "missing": 0}
        },
    },
    {"name": "dlc", "type": "number", "preprocessing": {"fitted": dict(NUMBER)}},
    {"name": "b2", "type": "number", "preprocessing": {"fitted": dict(NUMBER)}},
]
OUTPUT = {
    "name": "label",
    "type": "category",
    "preprocessing": {"fitted": {"labels": ["dos", "fuzzy", "normal", "replay"]}},
}


def document(output: dict = OUTPUT) -> str:
    return interface_document(MODEL, BINDINGS, FEATURES, output, 64)


def entries() -> dict[str, dict]:
    return {entry["name"]: entry for entry in json.loads(document())["inputs"]}


def test_the_document_is_sorted_indented_and_ends_with_a_newline() -> None:
    text = document()
    assert text.endswith("}\n")
    parsed = json.loads(text)
    assert text == json.dumps(parsed, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def test_the_document_says_which_model_how_to_bind_and_where_the_preprocessing_is() -> None:
    parsed = json.loads(document())
    assert parsed["contract_version"] == 3
    assert parsed["model"] == MODEL
    assert "by position" in parsed["runtime_binding"]
    assert parsed["preprocessing"] == "inside the model; pass raw values"
    assert parsed["window_size"] == parsed["stride"] == 64


def test_every_input_has_its_name_position_dtype_shape_and_type() -> None:
    by_name = entries()
    assert set(by_name) == {"can_id", "gear", "brake", "dlc", "b2"}
    assert by_name["dlc"]["position"] == 4 and by_name["dlc"]["dtype"] == "float32"
    assert by_name["can_id"]["dtype"] == "int32" and by_name["can_id"]["type"] == "category"
    assert by_name["brake"]["shape"] == [1, 64]


def test_every_input_carries_what_was_fitted_for_it() -> None:
    # FR-012: a reader sees what the model does to a raw value.
    by_name = entries()
    assert by_name["dlc"]["fitted"] == NUMBER
    assert by_name["can_id"]["fitted"]["vocab"] == [291, 608]
    assert by_name["can_id"]["fitted"]["cut"] == 2
    assert by_name["brake"]["fitted"]["spellings"] == {"off": 0, "on": 1}


def test_a_text_category_carries_its_code_table_and_an_integer_one_does_not() -> None:
    by_name = entries()
    assert by_name["gear"]["text_codes"] == {"drive": 1, "park": 2}
    assert by_name["can_id"]["text_codes"] is None
    assert by_name["gear"]["encoder"] == {"type": "onehot"}


def test_a_binary_input_carries_its_spellings() -> None:
    assert entries()["brake"]["spellings"] == {"off": 0, "on": 1}


def test_every_input_says_what_to_pass_when_a_reading_is_absent() -> None:
    by_name = entries()
    assert by_name["dlc"]["missing"] == 0.0
    assert by_name["can_id"]["missing"] == -1
    assert by_name["gear"]["missing"] == 0
    assert by_name["brake"]["missing"] == 0


def test_the_output_gives_its_decision_per_type() -> None:
    (category,) = json.loads(document())["outputs"]
    assert category["decision"] == "argmax"
    assert category["labels"] == ["dos", "fuzzy", "normal", "replay"]
    binary = {
        "name": "label",
        "type": "binary",
        "threshold": 0.4,
        "preprocessing": {"fitted": {"spellings": {"no": 0, "yes": 1}, "true_spelling": "yes"}},
    }
    (entry,) = json.loads(document(binary))["outputs"]
    assert entry["decision"] == "threshold" and entry["threshold"] == 0.4
    number = {
        "name": "label",
        "type": "number",
        "clip": [0.0, 10.0],
        "preprocessing": {"fitted": {"normalization": None, "shift": 0.0, "scale": 1.0}},
    }
    (entry,) = json.loads(document(number))["outputs"]
    assert entry["decision"] == "value" and entry["clip"] == [0.0, 10.0]


def header(output: dict = OUTPUT) -> str:
    return header_additions("g_model_data", MODEL, BINDINGS, FEATURES, output)


def test_the_header_has_one_position_per_input_with_its_element_type() -> None:
    text = header()
    assert 'constexpr char g_model_data_model_name[] = "picket-mlp";' in text
    assert "constexpr unsigned int g_model_data_input_dlc = 4;  /* float32[64] — raw value */" in (
        text
    )
    assert "constexpr unsigned int g_model_data_input_b2 = 0;" in text
    assert "constexpr unsigned int g_model_data_output_label = 0;" in text
    assert "constexpr unsigned int g_model_data_output_label_label_count = 4;" in text
    assert "extern const char* const g_model_data_output_label_labels[];" in text


def test_a_category_input_is_said_to_be_an_integer_code() -> None:
    line = next(line for line in header().splitlines() if "input_can_id" in line)
    assert "int32[64]" in line
    assert "integer" in line and "never a rounded number" in line


def test_a_binary_output_states_its_threshold_in_the_header() -> None:
    binary = {
        "name": "label",
        "type": "binary",
        "threshold": 0.5,
        "preprocessing": {"fitted": {"spellings": {}, "true_spelling": "yes"}},
    }
    assert "constexpr float g_model_data_output_label_threshold = 0.5f;" in header(binary)
    assert source_additions("g_model_data", binary) == ""


def test_the_source_defines_the_labels_in_order() -> None:
    source = source_additions("g_model_data", OUTPUT)
    assert source.index('"dos"') < source.index('"fuzzy"') < source.index('"replay"')
    assert "const char* const g_model_data_output_label_labels[] = {" in source


def test_labels_are_escaped_so_no_hex_escape_swallows_the_next_character() -> None:
    assert c_label_literal('a"b\\c') == '"a\\x22" "b\\x5c" "c"'
    assert c_label_literal("aä") == '"a\\xc3" "\\xa4"'
    assert c_label_literal("normal") == '"normal"'
    # A hex digit after an escape is the case the split exists for.
    assert c_label_literal("\tF") == '"\\x09" "F"'


def test_two_emissions_are_byte_identical() -> None:
    assert document() == document()
    assert header() == header()
