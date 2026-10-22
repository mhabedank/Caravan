"""The template builds at both shapes — the named model's and the committed fixture's.

**Nothing here trains anything.** The point is that the template can *express* the shape the named
model needs: 128 samples across 9 channels, six classes. What a model built that way achieves is
measured where the real data is, and this project has none (Principle IX).
"""

from __future__ import annotations

from caravan.templates.builders.conv1d import build
from caravan.templates.conv1d import Conv1dParameters

#: pace-cnn's input contract, read from the zoo on 2026-10-22: 2.56 s at 50 Hz of the UCI-HAR
#: inertial signals, six activities out.
NAMED_MODEL = {"window": 128, "channels": 9, "labels": tuple(f"activity_{i}" for i in range(6))}

#: The committed fixture's shape: the same template, an eighth of the window, four labels.
FIXTURE = {"window": 64, "channels": 5, "labels": ("normal", "dos", "fuzzy", "replay")}

BLOCKS = {
    "blocks": [
        {"filters": 16, "kernel": 5, "stride": 2, "normalise": True, "pool": 2},
        {"filters": 32, "kernel": 3, "normalise": True, "pool": 2},
    ],
    "head": "average",
}


def built(shape, params=BLOCKS):
    return build(
        Conv1dParameters.model_validate(params),
        (shape["window"], shape["channels"]),
        shape["labels"],
    )


def test_it_builds_at_the_named_models_shape() -> None:
    model = built(NAMED_MODEL)
    assert tuple(model.inputs[0].shape)[1:] == (128, 9)
    assert tuple(model.outputs[0].shape)[1:] == (6,)
    assert model.count_params() > 0


def test_it_builds_at_the_committed_fixtures_shape() -> None:
    model = built(FIXTURE)
    assert tuple(model.inputs[0].shape)[1:] == (64, 5)
    assert tuple(model.outputs[0].shape)[1:] == (4,)


def test_the_same_parameters_mean_the_same_thing_at_both_shapes() -> None:
    # Not a different template for a different scale: the parameters' meaning does not depend on
    # the window, which is what lets the acceptance test use the fixture at all.
    small, large = built(FIXTURE), built(NAMED_MODEL)
    kinds = [type(layer).__name__ for layer in small.layers]
    assert kinds == [type(layer).__name__ for layer in large.layers]
    assert large.count_params() > small.count_params()


def test_the_layer_order_inside_a_block_is_the_one_that_folds() -> None:
    # Normalisation before the activation, because that is the order it folds into the convolution
    # in — and the fold is the only reason it is offered.
    kinds = [type(layer).__name__ for layer in built(FIXTURE).layers]
    conv = kinds.index("Conv1D")
    assert kinds[conv + 1] == "BatchNormalization"
    assert kinds[conv + 2] == "ReLU"


def test_the_two_heads_give_different_parameter_counts() -> None:
    reducing = built(NAMED_MODEL)
    flattening = built(NAMED_MODEL, {**BLOCKS, "head": "flatten"})
    assert flattening.count_params() > reducing.count_params()


def test_dropout_at_zero_adds_no_layer() -> None:
    with_dropout = built(FIXTURE, {"blocks": [{"filters": 8, "kernel": 3, "dropout": 0.2}]})
    without = built(FIXTURE, {"blocks": [{"filters": 8, "kernel": 3}]})
    assert "Dropout" in [type(layer).__name__ for layer in with_dropout.layers]
    assert "Dropout" not in [type(layer).__name__ for layer in without.layers]


def test_normalisation_left_out_adds_no_layer() -> None:
    kinds = [
        type(layer).__name__
        for layer in built(FIXTURE, {"blocks": [{"filters": 8, "kernel": 3}]}).layers
    ]
    assert "BatchNormalization" not in kinds


def test_the_builder_validates_what_it_is_given() -> None:
    # A raw mapping goes through the parameter half, so the two halves cannot drift.
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        build({"blocks": [{"filters": 0, "kernel": 3}]}, (64, 5), ("a", "b"))
