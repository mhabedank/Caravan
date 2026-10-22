"""Running an exported model, and why the input quantization is load-bearing."""

from __future__ import annotations

import numpy as np
import pytest

from caravan.runtime.inspect import TensorRecord, inspect_model
from caravan.runtime.measure import measure, predict, quantize_input

EXAMPLE_SHAPE = (8, 3)


def features(count: int = 12) -> np.ndarray:
    return np.random.default_rng(7).random((count, *EXAMPLE_SHAPE)).astype(np.float32)


def test_measuring_gives_an_accuracy_and_a_confusion_matrix(int8_model) -> None:
    x = features()
    truth = [0] * 12
    result = measure(int8_model, x, truth, 3, split="test", dataset_version="sha256:example")

    assert 0.0 <= result.accuracy <= 1.0
    assert result.samples == 12
    assert sum(sum(row) for row in result.confusion) == 12
    # The figure cannot exist without saying what it is about.
    assert result.split == "test"
    assert result.dataset_version == "sha256:example"


def test_feeding_float_data_to_an_integer_model_gives_a_different_answer(int8_model) -> None:
    """The reason ``quantize_input`` exists, demonstrated rather than asserted in a comment.

    Handing float bytes to an int8 tensor is not an error — the runtime reinterprets them and
    returns predictions — so the only way this stays visible is a test that shows the answers
    differ. If they ever stop differing, the quantization step has stopped mattering, and this is
    the place that would say so.
    """
    from ai_edge_litert.interpreter import Interpreter

    x = features()
    proper = list(predict(int8_model, x))

    interpreter = Interpreter(model_path=str(int8_model))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]

    naive = []
    for sample in x:
        # The cast an unwary implementation would write: the same numbers, the wrong meaning. The
        # example features are in [0, 1), so this truncates nearly all of them to zero.
        interpreter.set_tensor(input_detail["index"], sample[np.newaxis, ...].astype(np.int8))
        interpreter.invoke()
        naive.append(int(np.argmax(interpreter.get_tensor(output_detail["index"])[0])))

    assert proper != naive, (
        "quantising the input made no difference to the predictions, which means either the "
        "example model ignores its input or this test has stopped testing anything"
    )


def test_quantizing_the_input_uses_the_models_own_scale(int8_model) -> None:
    inspection = inspect_model(int8_model)
    x = features(4)
    q = quantize_input(x, inspection.input)

    assert q.dtype == np.int8
    expected = np.clip(
        np.round(x / inspection.input.scale) + inspection.input.zero_point, -128, 127
    ).astype(np.int8)
    np.testing.assert_array_equal(q, expected)


def test_a_float_input_passes_through_unchanged(float_model) -> None:
    inspection = inspect_model(float_model)
    x = features(3)
    np.testing.assert_array_equal(quantize_input(x, inspection.input), x)


def test_an_integer_tensor_without_a_scale_is_refused() -> None:
    # There is no defined way to feed it, and guessing a scale would be inventing data.
    tensor = TensorRecord(name="x", dtype="int8", shape=(1, 8, 3))
    with pytest.raises(ValueError, match="no defined way to feed it"):
        quantize_input(features(1), tensor)


def test_an_empty_split_cannot_be_measured(int8_model) -> None:
    with pytest.raises(ValueError, match="no samples"):
        measure(
            int8_model,
            features(0),
            [],
            3,
            split="test",
            dataset_version="sha256:example",
        )


def test_measuring_needs_no_training_framework(int8_model) -> None:
    import sys

    measure(int8_model, features(2), [0, 0], 3, split="test", dataset_version="sha256:x")
    loaded = {name.split(".")[0] for name in sys.modules}
    assert not loaded & {"tensorflow", "keras"}
