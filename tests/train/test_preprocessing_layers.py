"""Each type's preprocessing layer: exact, TFLite Micro's operators only, and serialisable (T013).

Feature 008, research R3. Every layer is converted on its own under Caravan's settings (full int8,
input and output types left as the model has them) and read back from the file: the operators it
lowers to must all be in the set the research found in TFLM at ``f7ed40d``, and the integer check
must hold. Then the arithmetic is checked against what the fitted values say.
"""

from __future__ import annotations

import keras
import numpy as np
import pytest
from ai_edge_litert.interpreter import Interpreter

from caravan.convert.batch import fix_batch
from caravan.convert.tflite import convert
from caravan.runtime.flatbuffer import inspect_graph
from caravan.runtime.inspect import inspect_model
from caravan.templates.builders.preprocessing import AsChannel, Standardize, VocabularyOneHot

WINDOW = 8
#: What the three layers may lower to (research R3, plus what any converted model carries).
ALLOWED = {
    "QUANTIZE",
    "DEQUANTIZE",
    "SUB",
    "MUL",
    "ADD",
    "EQUAL",
    "CAST",
    "RELU",
    "SUM",
    "CONCATENATION",
    "RESHAPE",
    "FULLY_CONNECTED",
    "STRIDED_SLICE",
}
CODES = [291, 608, 790, 1072]


def single(layer, dtype: str):
    """One layer between a named input and a small dense head, as it sits in a real model."""
    tensor_in = keras.Input(shape=(WINDOW,), dtype=dtype, name="x")
    tensor = layer(tensor_in)
    head = keras.layers.Dense(2, name="head")(keras.layers.Flatten()(tensor))
    return keras.Model(tensor_in, {"y": head}), keras.Model(tensor_in, {"y": tensor})


def calibration(dtype: str):
    rng = np.random.default_rng(0)

    def generate():
        for _ in range(32):
            if dtype == "int32":
                yield {"x": rng.choice([*CODES, 0, 1, 7], size=(1, WINDOW)).astype(np.int32)}
            else:
                yield {"x": rng.normal(100.0, 20.0, size=(1, WINDOW)).astype(np.float32)}

    return generate


CASES = {
    "standardize": (lambda: Standardize(100.0, 20.0, name="s"), "float32"),
    "onehot": (lambda: VocabularyOneHot(CODES, name="v"), "int32"),
    "channel": (lambda: AsChannel(name="c"), "int32"),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_each_layer_lowers_to_tflm_operators_only_and_stays_integer(case, tmp_path) -> None:
    make, dtype = CASES[case]
    model, _ = single(make(), dtype)
    path = tmp_path / f"{case}.tflite"
    path.write_bytes(convert(model, "int8", calibration(dtype)))
    operators = {operator.name for operator in inspect_graph(path).operators}
    assert operators <= ALLOWED, operators - ALLOWED
    inspection = inspect_model(path)
    assert inspection.fully_integer, inspection.floating_tensors()


def run_converted(model, values: np.ndarray, tmp_path, dtype: str) -> np.ndarray:
    path = tmp_path / "layer.tflite"
    path.write_bytes(convert(model, "int8", calibration(dtype)))
    runner = Interpreter(model_path=str(path)).get_signature_runner()
    return np.concatenate([runner(x=values[i : i + 1])["y"] for i in range(len(values))])


def test_the_one_hot_is_exact_for_every_code_and_an_unseen_one_is_unknown(tmp_path) -> None:
    _, probe = single(VocabularyOneHot(CODES, name="v"), "int32")
    codes = np.array([[*CODES, 0, 5, -1, 2**20]], dtype=np.int32)
    expected = np.zeros((1, WINDOW, len(CODES) + 1), dtype=np.float32)
    for position, code in enumerate(codes[0]):
        slot = CODES.index(code) + 1 if code in CODES else 0
        expected[0, position, slot] = 1.0
    np.testing.assert_array_equal(probe(codes)["y"].numpy(), expected)
    converted = run_converted(probe, codes, tmp_path, "int32")
    np.testing.assert_array_equal(converted, expected)


def test_standardize_matches_shift_and_scale_within_the_int8_step(tmp_path) -> None:
    _, probe = single(Standardize(100.0, 20.0, name="s"), "float32")
    values = np.random.default_rng(1).normal(100.0, 20.0, size=(4, WINDOW)).astype(np.float32)
    expected = ((values - 100.0) / 20.0)[..., None]
    np.testing.assert_allclose(probe(values)["y"].numpy(), expected, rtol=1e-6)
    converted = run_converted(probe, values, tmp_path, "float32")
    step = (expected.max() - expected.min()) / 255
    assert np.abs(converted - expected).max() <= 2 * step


def test_as_channel_is_the_bit(tmp_path) -> None:
    _, probe = single(AsChannel(name="c"), "int32")
    bits = np.array([[0, 1, 1, 0, 1, 0, 0, 1]], dtype=np.int32)
    np.testing.assert_array_equal(probe(bits)["y"].numpy(), bits[..., None].astype(np.float32))


@pytest.mark.parametrize("case", sorted(CASES))
def test_each_layer_survives_saving_loading_and_the_batch_fix(case, tmp_path) -> None:
    make, dtype = CASES[case]
    model, _ = single(make(), dtype)
    model.save(tmp_path / "m.keras")
    loaded = keras.saving.load_model(tmp_path / "m.keras")
    fixed = fix_batch(loaded)
    values = next(iter(calibration(dtype)()))
    np.testing.assert_allclose(
        model.predict(values, verbose=0)["y"], fixed.predict(values, verbose=0)["y"], atol=1e-5
    )
    assert type(loaded.get_layer({"standardize": "s", "onehot": "v", "channel": "c"}[case])) is (
        type(make())
    )
