"""Fixing the input batch to one is a reshaping of the graph, not a change to the function.

That sentence is the whole licence for doing it at all. The exported model is the model the
accuracy gate measured, so anything the conversion does to the graph has to leave the function
alone — and "leaves it alone" is checkable to the bit, so it is checked to the bit rather than
argued for.

Why it is worth doing: on a board the batch is always one, and the converter otherwise emits four
operators of shape plumbing to compute a flatten shape from a dimension that never varies. Half the
resolver, for arithmetic whose answer is known.
"""

from __future__ import annotations

import numpy as np
import pytest

from caravan.convert.batch import fix_batch

WINDOW, CHANNELS, CLASSES = 16, 3, 4
SEED = 20261022


def _trained(architecture: str):
    import keras

    keras.utils.set_random_seed(SEED)
    inner = (
        [keras.layers.Flatten(name="flatten"), keras.layers.Dense(8, activation="relu", name="h")]
        if architecture == "mlp"
        else [
            keras.layers.Conv1D(4, 3, activation="relu", name="conv"),
            keras.layers.GlobalAveragePooling1D(name="pool"),
        ]
    )
    model = keras.Sequential(
        [
            keras.layers.Input(shape=(WINDOW, CHANNELS), name="input"),
            *inner,
            keras.layers.Dense(CLASSES, activation="softmax", name="output"),
        ],
        name=architecture,
    )
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy")
    rng = np.random.default_rng(SEED)
    model.fit(
        rng.standard_normal((32, WINDOW, CHANNELS)).astype("float32"),
        rng.integers(0, CLASSES, 32),
        epochs=1,
        verbose=0,
    )
    return model


@pytest.mark.parametrize("architecture", ["mlp", "conv1d"])
def test_the_fixed_model_computes_the_same_function(architecture: str) -> None:
    # Both architectures, because a trick that works on one layer stack and not the next would be
    # worse than no trick: conv1d is the next template this project adds.
    trained = _trained(architecture)
    fixed = fix_batch(trained)

    probe = np.random.default_rng(SEED + 1).standard_normal((5, WINDOW, CHANNELS)).astype("float32")
    before = trained.predict(probe, verbose=0)
    after = np.concatenate([fixed.predict(probe[i : i + 1], verbose=0) for i in range(len(probe))])
    assert np.array_equal(before, after), f"max difference {np.abs(before - after).max()}"


def test_the_fixed_model_has_a_batch_of_one() -> None:
    fixed = fix_batch(_trained("mlp"))
    assert tuple(fixed.inputs[0].shape) == (1, WINDOW, CHANNELS)


def test_the_weights_are_the_trained_weights() -> None:
    trained = _trained("mlp")
    fixed = fix_batch(trained)
    for original, copied in zip(trained.get_weights(), fixed.get_weights(), strict=True):
        assert np.array_equal(original, copied)


def test_a_model_already_fixed_to_one_is_returned_as_it_is() -> None:
    # Idempotent, so a second conversion of the same model is not a second clone.
    once = fix_batch(_trained("mlp"))
    twice = fix_batch(once)
    assert tuple(twice.inputs[0].shape) == (1, WINDOW, CHANNELS)


def test_a_model_fixed_to_another_batch_is_refused() -> None:
    # Not a case the templates produce, but silently reshaping somebody's batch of 32 down to 1
    # would change what their model is. Refusing says so.
    import keras

    model = keras.Sequential(
        [
            keras.layers.Input(shape=(WINDOW, CHANNELS), batch_size=32, name="input"),
            keras.layers.Flatten(name="flatten"),
            keras.layers.Dense(CLASSES, activation="softmax", name="output"),
        ],
        name="batched",
    )
    with pytest.raises(ValueError, match="batch"):
        fix_batch(model)
