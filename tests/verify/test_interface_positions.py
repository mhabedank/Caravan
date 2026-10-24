"""Names to positions, read from the model file (feature 006, research R4 and R5).

The microcontroller runtime binds by position in subgraph 0 and reads no signature, so the contract
must say, for each declared name, which position the file actually uses — found through the
signature, never assumed from the declaration. Runs with no training framework installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from caravan.manifest.errors import RULE_DECLARED_NAME_NOT_IN_MODEL, RunRuleFailure
from caravan.runtime.flatbuffer import read_bindings

MODELS = Path(__file__).resolve().parents[1] / "fixtures" / "models"


def test_the_declared_names_resolve_to_positions_with_the_tensors_parameters() -> None:
    from ai_edge_litert.interpreter import Interpreter

    path = MODELS / "example-int8.tflite"
    frames, attack = read_bindings(path, inputs=["frames"], outputs=["attack"])

    interpreter = Interpreter(model_path=str(path))
    detail_in = interpreter.get_input_details()[frames.position]
    detail_out = interpreter.get_output_details()[attack.position]
    assert (frames.role, attack.role) == ("input", "output")
    assert frames.tensor_index == detail_in["index"]
    assert attack.tensor_index == detail_out["index"]
    assert list(frames.shape) == list(detail_in["shape"])
    assert frames.element_type == "int8" == attack.element_type
    assert (frames.scale, frames.zero_point) == pytest.approx(detail_in["quantization"])
    assert (attack.scale, attack.zero_point) == pytest.approx(detail_out["quantization"])


def test_a_float_model_has_no_quantization_parameters() -> None:
    frames, attack = read_bindings(
        MODELS / "example-float.tflite", inputs=["frames"], outputs=["attack"]
    )
    assert frames.element_type == "float32"
    assert frames.scale is None and frames.zero_point is None
    assert attack.scale is None


def test_a_name_the_signature_does_not_carry_is_refused_by_name() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        read_bindings(MODELS / "example-int8.tflite", inputs=["frames"], outputs=["verdict"])
    finding = caught.value.finding
    assert finding.rule == RULE_DECLARED_NAME_NOT_IN_MODEL
    assert finding.found == "verdict"
    assert "attack" in finding.accepted


def test_the_typed_models_positions_are_the_interpreters() -> None:
    # Feature 008: the position the contract states is the index interpreter.input(i) takes.
    from ai_edge_litert.interpreter import Interpreter

    from tests.verify.conftest import TYPED_INPUTS, TYPED_OUTPUT

    path = MODELS / "example-typed.tflite"
    bindings = read_bindings(path, inputs=list(TYPED_INPUTS), outputs=[TYPED_OUTPUT])
    details = Interpreter(model_path=str(path)).get_input_details()
    for binding in bindings:
        if binding.role == "input":
            assert details[binding.position]["index"] == binding.tensor_index
            assert details[binding.position]["dtype"].__name__ == TYPED_INPUTS[binding.name]
