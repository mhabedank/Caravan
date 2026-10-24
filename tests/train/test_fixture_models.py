"""The committed example models, and the property the suite actually depends on.

``tests/verify`` runs on Pythons where no converter can be installed, so the models it reads must
already exist in the repository. What has to hold is that they are what their generator produces —
not byte for byte, which nothing promises for a flatbuffer, but in every way the tests use them.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

MODELS = Path(__file__).resolve().parent.parent / "fixtures" / "models"


def load_generator():
    spec = importlib.util.spec_from_file_location("fixture_models_make", MODELS / "make.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def describe(path: Path) -> dict:
    """Everything the suite relies on about a model, read with the runtime."""
    from ai_edge_litert.interpreter import Interpreter

    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    return {
        "dtypes": sorted(d["dtype"].__name__ for d in interpreter.get_tensor_details()),
        "input": (
            interpreter.get_input_details()[0]["dtype"].__name__,
            tuple(interpreter.get_input_details()[0]["shape"]),
            interpreter.get_input_details()[0]["quantization"],
        ),
        "output": (
            interpreter.get_output_details()[0]["dtype"].__name__,
            tuple(interpreter.get_output_details()[0]["shape"]),
        ),
    }


def predictions(path: Path) -> list[int]:
    from caravan.runtime.measure import predict

    return list(predict(path, np.load(MODELS / "example-input.npy")))


def test_the_committed_models_match_what_their_generator_produces(tmp_path) -> None:
    # Functional equivalence, not byte-identity: a flatbuffer carries its converter's version and
    # layout choices, and nothing promises two runs produce the same bytes. Promising it would buy
    # an intermittent failure in exchange for nothing the suite needs.
    make = load_generator()
    int8_again, float_again, typed_again = make.generate(tmp_path / "again")

    assert describe(int8_again) == describe(MODELS / "example-int8.tflite")
    assert describe(float_again) == describe(MODELS / "example-float.tflite")
    assert predictions(int8_again) == predictions(MODELS / "example-int8.tflite")
    assert describe(typed_again)["dtypes"] == describe(MODELS / "example-typed.tflite")["dtypes"]
    assert typed_predictions(make, typed_again) == typed_predictions(
        make, MODELS / "example-typed.tflite"
    )


def typed_predictions(make, path: Path) -> list[int]:
    from caravan.runtime.measure import predict

    return list(predict(path, make.typed_input(12), make.TYPED_OUTPUT))


def test_the_committed_int8_models_are_fully_integer() -> None:
    from caravan.runtime.inspect import inspect_model

    assert inspect_model(MODELS / "example-int8.tflite").fully_integer
    assert inspect_model(MODELS / "example-typed.tflite").fully_integer


def test_the_models_stay_small() -> None:
    # They exist so another suite can read something, not to be representative of anything.
    total = sum(path.stat().st_size for path in MODELS.glob("example-*"))
    assert total < 64 * 1024, f"{total} bytes of committed example models is more than needed"
