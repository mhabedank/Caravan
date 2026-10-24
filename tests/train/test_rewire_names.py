"""The front-end puts a template's body behind named inputs and leaves the body alone (T020).

Feature 008: one model input per feature, named after it, and a dict output keyed by the output's
name — the converter keeps both in the signature, and the firmware binds by them (feature 006,
research R4). The body is the builder's own layers, in their order, with their shapes: a template
needs no change to be put behind typed features.
"""

from __future__ import annotations

import keras
import numpy as np
import pytest
from ai_edge_litert import schema_py_generated as schema

from caravan.convert.tflite import convert
from caravan.templates.builders import load_builder
from caravan.templates.builders.frontend import build_model

CASES = {
    "mlp": {"hidden": [32, 16], "dropout": 0.1},
    "conv1d": {"blocks": [{"filters": 8, "kernel": 3, "normalise": True, "pool": 2}]},
}
WINDOW = 64
NUMBER = {"normalization": "zscore", "shift": 1.0, "scale": 2.0, "fill": 0.0}
FEATURES = [
    {
        "name": "can_id",
        "type": "category",
        "preprocessing": {
            "fitted": {"vocab": [3, 5], "codes": [3, 5], "text_codes": None, "missing": -1}
        },
        "encoder": {"type": "dense", "embedding_size": 2},
    },
    {"name": "dlc", "type": "number", "preprocessing": {"fitted": dict(NUMBER)}},
    {"name": "b0", "type": "number", "preprocessing": {"fitted": dict(NUMBER)}},
]
OUTPUT = {
    "name": "label",
    "type": "category",
    "preprocessing": {"fitted": {"labels": ["a", "b", "c", "d"]}},
}


def read(blob: bytes):
    model = schema.ModelT.InitFromObj(schema.Model.GetRootAs(blob, 0))
    signature = model.signatureDefs[0]
    inputs = sorted(entry.name.decode() for entry in signature.inputs)
    outputs = [entry.name.decode() for entry in signature.outputs]
    return inputs, outputs


def calibration():
    generator = np.random.default_rng(0)

    def generate():
        for _ in range(20):
            yield {
                "can_id": generator.choice([3, 5, 9], size=(1, WINDOW)).astype(np.int32),
                "dlc": generator.normal(size=(1, WINDOW)).astype(np.float32),
                "b0": generator.normal(size=(1, WINDOW)).astype(np.float32),
            }

    return generate


@pytest.mark.parametrize("template", sorted(CASES))
def test_the_body_is_the_builders_layers_in_order(template: str) -> None:
    keras.utils.set_random_seed(7)
    body = load_builder(template)(CASES[template], (WINDOW, 4), ["a", "b", "c", "d"])
    model = build_model(load_builder(template), CASES[template], FEATURES, OUTPUT, WINDOW)
    tail = [type(layer).__name__ for layer in model.layers[-len(body.layers) :]]
    assert tail == [type(layer).__name__ for layer in body.layers]
    shapes = [tuple(weight.shape) for weight in body.get_weights()]
    assert shapes == [tuple(weight.shape) for weight in model.get_weights()[-len(shapes) :]]


@pytest.mark.parametrize("template", sorted(CASES))
def test_every_input_has_its_name_and_dtype_and_the_output_its_name(template: str) -> None:
    keras.utils.set_random_seed(7)
    model = build_model(load_builder(template), CASES[template], FEATURES, OUTPUT, WINDOW)
    dtypes = {tensor.name.split(":")[0]: str(tensor.dtype) for tensor in model.inputs}
    assert dtypes == {"can_id": "int32", "dlc": "float32", "b0": "float32"}
    inputs, outputs = read(convert(model, "int8", calibration()))
    assert inputs == ["b0", "can_id", "dlc"]
    assert outputs == ["label"]
