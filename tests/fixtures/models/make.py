"""Generate the small example models the runtime tests read.

They are committed because `tests/verify` runs on Pythons where no converter can be installed —
that is the whole point of the `verify` extra — so those tests need a model that already exists.

Three models:

* ``example-int8.tflite`` and ``example-float.tflite`` — one input, one output, converted with an
  int8 boundary (input and output int8 with a scale and a zero point), as other converters and
  Caravan before feature 008 produce. The runtime must still feed such a model correctly.
* ``example-typed.tflite`` — the form Caravan produces since feature 008: five inputs of mixed
  element types (three float32 numbers, an int32 category code, an int32 binary), preprocessing
  inside the model, a float32 output, full int8 in between.

The generator needs the conversion half and therefore Python 3.13. Its output is **not** promised
to be byte-identical between runs: a flatbuffer carries its converter's version and layout choices.
The regeneration test in `tests/train` asserts functional equivalence instead.

Run with ``python tests/fixtures/models/make.py``.
"""

from __future__ import annotations

from pathlib import Path

INPUT_SHAPE = (8, 3)
CLASSES = 3
SEED = 20261022
CALIBRATION_SAMPLES = 64

#: The names the single-input models carry: the interface contract binds by them, so the verify
#: tests that read these files need them.
INPUT_NAME = "frames"
OUTPUT_NAME = "attack"

#: The typed model's window and its five inputs, in manifest order.
TYPED_WINDOW = 8
TYPED_INPUTS = ("speed", "gear", "brake", "rpm", "load")
TYPED_OUTPUT = "state"
TYPED_CODES = (3, 5, 7)


def _model():
    import keras

    keras.utils.set_random_seed(SEED)
    tensor_in = keras.Input(shape=INPUT_SHAPE, name=INPUT_NAME)
    tensor = keras.layers.Flatten(name="flatten")(tensor_in)
    tensor = keras.layers.Dense(6, activation="relu", name="hidden")(tensor)
    tensor = keras.layers.Dense(CLASSES, activation="softmax", name="output")(tensor)
    return keras.Model(tensor_in, {OUTPUT_NAME: tensor}, name="example")


def _calibration():
    import numpy as np

    rng = np.random.default_rng(SEED)

    def generate():
        for _ in range(CALIBRATION_SAMPLES):
            yield {INPUT_NAME: rng.random((1, *INPUT_SHAPE), dtype=np.float32)}

    return generate


def _int8_boundary(model) -> bytes:
    """A full int8 conversion with an int8 input and output, as another converter produces."""
    import tensorflow as tf

    from caravan.convert.batch import fix_batch

    converter = tf.lite.TFLiteConverter.from_keras_model(fix_batch(model))
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = _calibration()
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    return converter.convert()


def typed_features() -> list[dict]:
    """The five input features, with fitted values, as the front-end takes them."""
    number = {"normalization": "zscore", "shift": 0.5, "scale": 0.25, "fill": 0.0}
    return [
        {"name": "speed", "type": "number", "preprocessing": {"fitted": dict(number)}},
        {
            "name": "gear",
            "type": "category",
            "preprocessing": {"fitted": {"codes": list(TYPED_CODES), "text_codes": None}},
            "encoder": {"type": "dense", "embedding_size": 2},
        },
        {"name": "brake", "type": "binary", "preprocessing": {"fitted": {"spellings": {}}}},
        {"name": "rpm", "type": "number", "preprocessing": {"fitted": dict(number)}},
        {"name": "load", "type": "number", "preprocessing": {"fitted": dict(number)}},
    ]


def typed_input(count: int, seed: int = SEED + 2) -> dict:
    """Raw values for the typed model, as a firmware would pass them."""
    import numpy as np

    rng = np.random.default_rng(seed)
    shape = (count, TYPED_WINDOW)
    return {
        "speed": rng.random(shape, dtype=np.float32),
        "gear": rng.choice([*TYPED_CODES, 9], size=shape).astype(np.int32),
        "brake": rng.integers(0, 2, size=shape).astype(np.int32),
        "rpm": rng.random(shape, dtype=np.float32),
        "load": rng.random(shape, dtype=np.float32),
    }


def _typed_model():
    import keras

    from caravan.templates.builders import load_builder
    from caravan.templates.builders.frontend import build_model

    keras.utils.set_random_seed(SEED)
    output = {
        "name": TYPED_OUTPUT,
        "type": "category",
        "preprocessing": {"fitted": {"labels": ["idle", "drive", "fault"]}},
    }
    return build_model(load_builder("mlp"), {"hidden": [6]}, typed_features(), output, TYPED_WINDOW)


def generate(destination: Path) -> tuple[Path, Path, Path]:
    """Write the three models and the example input into ``destination``."""
    import numpy as np

    from caravan.convert.tflite import convert

    destination.mkdir(parents=True, exist_ok=True)
    model = _model()

    int8_path = destination / "example-int8.tflite"
    int8_path.write_bytes(_int8_boundary(model))
    float_path = destination / "example-float.tflite"
    float_path.write_bytes(convert(model, "none"))

    calibration = typed_input(CALIBRATION_SAMPLES, seed=SEED + 3)

    def typed_calibration():
        for index in range(CALIBRATION_SAMPLES):
            yield {name: values[index : index + 1] for name, values in calibration.items()}

    typed_path = destination / "example-typed.tflite"
    typed_path.write_bytes(convert(_typed_model(), "int8", typed_calibration))

    rng = np.random.default_rng(SEED + 1)
    features = rng.random((12, *INPUT_SHAPE)).astype(np.float32)
    np.save(destination / "example-input.npy", features)
    return int8_path, float_path, typed_path


if __name__ == "__main__":
    for written in generate(Path(__file__).parent):
        print(f"{written}: {written.stat().st_size} bytes")
