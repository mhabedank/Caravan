"""Generate the two small example models the runtime tests read.

They are committed because `tests/verify` runs on Pythons where no converter can be installed —
that is the whole point of the `verify` extra — so those tests need a model that already exists.

The generator needs the conversion half and therefore Python 3.13. Its output is **not** promised
to be byte-identical between runs: a flatbuffer carries its converter's version and layout choices,
and nothing says two runs produce the same bytes. The regeneration test in `tests/train` asserts
functional equivalence instead — the same tensor types, shapes, quantisation parameters and
predictions — which is the property the suite actually depends on.

Run with ``python tests/fixtures/models/make.py``.
"""

from __future__ import annotations

from pathlib import Path

INPUT_SHAPE = (8, 3)
CLASSES = 3
SEED = 20261022
CALIBRATION_SAMPLES = 64


#: The declared names the models carry, as a model built by caravan does since feature 006: the
#: interface contract binds by them, so the verify tests that read these files need them.
INPUT_NAME = "frames"
OUTPUT_NAME = "attack"


def _model():
    import keras

    from caravan.stages.build import rewire

    keras.utils.set_random_seed(SEED)
    sequential = keras.Sequential(
        [
            keras.layers.Input(shape=INPUT_SHAPE, name="input"),
            keras.layers.Flatten(name="flatten"),
            keras.layers.Dense(6, activation="relu", name="hidden"),
            keras.layers.Dense(CLASSES, activation="softmax", name="output"),
        ],
        name="example",
    )
    return rewire(sequential, INPUT_NAME, OUTPUT_NAME)


def _calibration():
    import numpy as np

    rng = np.random.default_rng(SEED)

    def generate():
        for _ in range(CALIBRATION_SAMPLES):
            yield [rng.random((1, *INPUT_SHAPE), dtype=np.float32)]

    return generate


def generate(destination: Path) -> tuple[Path, Path]:
    """Write both models and the example input into ``destination``."""
    import numpy as np

    from caravan.convert.tflite import convert

    destination.mkdir(parents=True, exist_ok=True)
    model = _model()

    int8_path = destination / "example-int8.tflite"
    int8_path.write_bytes(convert(model, "int8", _calibration()))
    float_path = destination / "example-float.tflite"
    float_path.write_bytes(convert(model, "none"))

    rng = np.random.default_rng(SEED + 1)
    features = rng.random((12, *INPUT_SHAPE)).astype(np.float32)
    np.save(destination / "example-input.npy", features)
    return int8_path, float_path


if __name__ == "__main__":
    for written in generate(Path(__file__).parent):
        print(f"{written}: {written.stat().st_size} bytes")
