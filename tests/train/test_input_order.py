"""The converter reorders inputs; the contract binds every one by name (T024, US3).

Feature 008. A model of the typed pilot has five inputs, and the converted file does not keep the
manifest's order (research note, section 4). That is measured here and said out loud if it ever
changes. What must hold either way: ``model/interface.json`` gives each input's name, position,
element type, shape and type, and feeding inputs at the contract's positions — the way a
microcontroller runtime binds, ``interpreter.input(i)`` — reproduces the trained model's classes.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from tests.support import FIXTURE_COLUMNS
from tests.train.test_typed_pilot import exported, raw_test_windows  # noqa: F401  (fixture)


@pytest.fixture
def contract(exported) -> dict:  # noqa: F811
    return json.loads((exported / "model" / "interface.json").read_text(encoding="utf-8"))


def test_the_converted_order_differs_from_the_manifests(contract) -> None:
    by_position = [
        entry["name"] for entry in sorted(contract["inputs"], key=lambda e: e["position"])
    ]
    assert sorted(by_position) == sorted(FIXTURE_COLUMNS)
    # Measured on 2026-10-24 (TF 2.21.0). If this ever fails, the converter has started keeping
    # the manifest's order: the binding by name still holds, and this note should say so.
    assert by_position != list(FIXTURE_COLUMNS), "the converter now keeps the manifest's order"


def test_every_input_is_described_for_binding(contract) -> None:
    for entry in contract["inputs"]:
        assert set(entry) >= {"name", "position", "dtype", "shape", "type"}
        assert entry["shape"] == [1, contract["window_size"]]
        assert entry["dtype"] == ("int32" if entry["type"] == "category" else "float32")
    assert sorted(entry["position"] for entry in contract["inputs"]) == list(range(5))


def test_feeding_by_the_contracts_positions_reproduces_the_trained_classes(
    exported,  # noqa: F811
    contract,
) -> None:
    import keras
    from ai_edge_litert.interpreter import Interpreter

    import caravan.templates.builders.preprocessing  # noqa: F401  (registers the layers)

    inputs, _ = raw_test_windows(exported)
    trained = keras.saving.load_model(exported / "model" / "trained.keras")
    expected = np.argmax(trained.predict(inputs, verbose=0)["label"], axis=1)

    interpreter = Interpreter(model_path=str(exported / "model" / "model.tflite"))
    interpreter.allocate_tensors()
    details = interpreter.get_input_details()
    output = interpreter.get_output_details()[contract["outputs"][0]["position"]]
    got = []
    for index in range(len(expected)):
        for entry in contract["inputs"]:
            detail = details[entry["position"]]
            interpreter.set_tensor(detail["index"], inputs[entry["name"]][index : index + 1])
        interpreter.invoke()
        got.append(int(np.argmax(interpreter.get_tensor(output["index"])[0])))
    budget = 0.02
    assert float((np.array(got) == expected).mean()) >= 1 - budget
