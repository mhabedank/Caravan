"""Rewiring a template's model under the declared names changes nothing but the names (R4).

Measured on 2026-10-23 (TF 2.21.0, Keras 3.15.1): the converter keeps an input's name but drops an
output layer's name unless the model returns a dict. So the build rewires every builder's model
into a functional model with a named input and a dict output — and that is only acceptable if no
weight and no operator changes. This test is what holds that.
"""

from __future__ import annotations

import keras
import numpy as np
import pytest
from ai_edge_litert import schema_py_generated as schema

from caravan.convert.tflite import convert
from caravan.stages.build import rewire
from caravan.templates.builders import load_builder

CASES = {
    "mlp": {"hidden": [32, 16], "dropout": 0.1},
    "conv1d": {"blocks": [{"filters": 8, "kernel": 3, "normalise": True, "pool": 2}]},
}
SHAPE = (64, 5)


def read(blob: bytes):
    model = schema.ModelT.InitFromObj(schema.Model.GetRootAs(blob, 0))
    graph = model.subgraphs[0]
    codes = [model.operatorCodes[op.opcodeIndex].builtinCode for op in graph.operators]
    signature = model.signatureDefs[0]
    inputs = [entry.name.decode() for entry in signature.inputs]
    outputs = [entry.name.decode() for entry in signature.outputs]
    return codes, inputs, outputs


def calibration():
    generator = np.random.default_rng(0)
    return lambda: ([generator.normal(size=(1, *SHAPE)).astype(np.float32)] for _ in range(20))


@pytest.mark.parametrize("template", sorted(CASES))
def test_weights_are_unchanged_array_for_array(template: str) -> None:
    keras.utils.set_random_seed(7)
    built = load_builder(template)(CASES[template], SHAPE, ["a", "b", "c", "d"])
    before = [weight.copy() for weight in built.get_weights()]

    rewired = rewire(built, "frames", "attack")

    after = rewired.get_weights()
    assert len(before) == len(after)
    assert all(np.array_equal(a, b) for a, b in zip(before, after, strict=True))
    assert rewired.inputs[0].name.startswith("frames")


@pytest.mark.parametrize("template", sorted(CASES))
def test_operators_are_unchanged_and_the_signature_carries_the_names(template: str) -> None:
    keras.utils.set_random_seed(7)
    built = load_builder(template)(CASES[template], SHAPE, ["a", "b", "c", "d"])
    plain_codes, _, plain_outputs = read(convert(built, "int8", calibration()))

    codes, inputs, outputs = read(convert(rewire(built, "frames", "attack"), "int8", calibration()))

    assert codes == plain_codes
    assert inputs == ["frames"]
    assert outputs == ["attack"]
    # Without the rewiring the converter invents a name — the reason the rewiring exists.
    assert plain_outputs != ["attack"]
