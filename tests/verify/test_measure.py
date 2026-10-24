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


CHILD = """
import sys
import numpy as np
from caravan.runtime.measure import measure

result = measure(
    {path!r}, np.zeros((2, 8, 3), dtype=np.float32), [0, 0], 3,
    split="test", dataset_version="sha256:x",
)
loaded = sorted({{name.split(".")[0] for name in sys.modules}} & {{"tensorflow", "keras"}})
print(result.samples, loaded)
"""


def test_measuring_needs_no_training_framework(int8_model) -> None:
    """In a **fresh interpreter**, for the reason feature 002 learned the hard way.

    Reading ``sys.modules`` in this process proves nothing once the suite also contains tests that
    legitimately import a training framework — on Python 3.13 with both extras installed, a
    sibling in ``tests/train`` has already put Keras there. A subprocess is also the honest shape
    of the claim: what matters is what a user's process loads when it measures a model, not what
    this one happens to have lying around.
    """
    import subprocess
    import sys
    from pathlib import Path as _Path

    result = subprocess.run(
        [sys.executable, "-c", CHILD.format(path=str(int8_model))],
        capture_output=True,
        text=True,
        check=False,
        cwd=_Path(__file__).resolve().parents[2],
    )
    assert result.returncode == 0, result.stderr
    samples, loaded = result.stdout.strip().split(" ", 1)
    assert samples == "2"
    assert loaded == "[]", f"measuring loaded a training framework: {loaded}"


# --- feature 008: several inputs, fed by name ----------------------------------------------------


def typed_values(count: int) -> dict:
    from tests.verify.conftest import TYPED_INPUTS, TYPED_WINDOW

    rng = np.random.default_rng(11)
    out = {}
    for name, dtype in TYPED_INPUTS.items():
        if dtype == "int32":
            out[name] = rng.integers(0, 8, size=(count, TYPED_WINDOW)).astype(np.int32)
        else:
            out[name] = rng.random((count, TYPED_WINDOW), dtype=np.float32)
    return out


def test_a_typed_model_is_run_by_input_name(typed_model) -> None:
    from caravan.runtime.measure import run_model

    raw = run_model(typed_model, typed_values(5), "state")
    assert raw.shape == (5, 3)
    assert raw.dtype == np.float32
    np.testing.assert_allclose(raw.sum(axis=1), 1.0, atol=0.02)  # a softmax, dequantized


def test_the_order_of_the_mapping_does_not_matter(typed_model) -> None:
    from caravan.runtime.measure import run_model

    values = typed_values(4)
    reordered = dict(reversed(list(values.items())))
    np.testing.assert_array_equal(
        run_model(typed_model, values, "state"), run_model(typed_model, reordered, "state")
    )


def test_a_missing_input_is_refused_by_name(typed_model) -> None:
    from caravan.runtime.measure import run_model

    values = typed_values(2)
    del values["gear"]
    with pytest.raises(ValueError, match="gear"):
        run_model(typed_model, values, "state")
