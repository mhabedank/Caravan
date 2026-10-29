"""Every input feature in, preprocessed, concatenated, through the template's body, one head out.

Behind the ``train`` extra (feature 008, research R2-R5). The model has one input per input feature,
named after it, with the element type a device has for its type: float32 for ``number``, int32 for
``category`` and ``binary``. Each input passes through its type's layer (``preprocessing.py``); the
channels are concatenated to ``(window_size, channels)``, which is what a template's builder has
always been given as its input shape, so ``mlp`` and ``conv1d`` are unchanged.

The head depends on the output type:

* ``category`` — the builder's own last layer, a softmax over the labels;
* ``binary`` — the builder's body and one sigmoid unit;
* ``number`` — the builder's body, one linear unit, the inverse of the output's normalization when
  one is set, and its ``clip`` when one is stated;
* ``anomaly`` (feature 010) — the builder's body whole, since it reconstructs rather than decides,
  and a ``ReconstructionError`` comparing the reconstruction with the input as the model saw it
  after preprocessing: the model's output is the anomaly score (research R8).

An ``image`` input (feature 010) is the model's only input: pixel values 0-255 as float32 in the
Keras model, scaled by 1/255 inside it; the converter makes the boundary uint8 at scale 1, zero
point 0 (research R6). The body is given the image's shape (height, width, channels).

A builder's last layer is its head: that is the contract the registered templates keep, and it is
why a ``binary`` or ``number`` head replaces it. The model returns a dict keyed by the output's
name: the converter keeps that name in the signature, and the firmware binds by it (feature 006,
research R4).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import keras

from caravan.templates.builders.preprocessing import (
    AsChannel,
    Clip,
    ReconstructionError,
    Rescale,
    Standardize,
    VocabularyOneHot,
)

#: The element type of each input type's model input. An image is float32 in the Keras model and
#: uint8 in the converted one: the converter sets the boundary, not this table (research R6).
INPUT_DTYPES = {"number": "float32", "category": "int32", "binary": "int32", "image": "float32"}

#: What a builder receives as labels for a one-unit head it will not keep.
ONE_UNIT = ("value",)


def channels_of(feature: Mapping[str, Any]) -> int:
    """How many channels per step one input feature contributes."""
    if feature["type"] == "image":
        return int(feature["preprocessing"]["fitted"]["num_channels"])
    if feature["type"] != "category":
        return 1
    encoder = feature["encoder"]
    if encoder["type"] == "dense":
        return int(encoder["embedding_size"])
    return len(feature["preprocessing"]["fitted"]["codes"]) + 1


def feature_branch(feature: Mapping[str, Any], window: int | None) -> tuple[Any, Any]:
    """One feature's input and its preprocessed channels."""
    name = feature["name"]
    fitted = feature["preprocessing"]["fitted"]
    if feature["type"] == "image":
        shape = (int(fitted["height"]), int(fitted["width"]), int(fitted["num_channels"]))
        tensor_in = keras.Input(shape=shape, dtype=INPUT_DTYPES["image"], name=name)
        return tensor_in, keras.layers.Rescaling(1.0 / 255.0, name=f"{name}_scale")(tensor_in)
    tensor_in = keras.Input(shape=(window or 1,), dtype=INPUT_DTYPES[feature["type"]], name=name)
    if feature["type"] == "number":
        return tensor_in, Standardize(fitted["shift"], fitted["scale"], name=f"{name}_scale")(
            tensor_in
        )
    if feature["type"] == "binary":
        return tensor_in, AsChannel(name=f"{name}_channel")(tensor_in)
    channels = VocabularyOneHot(fitted["codes"], name=f"{name}_onehot")(tensor_in)
    encoder = feature["encoder"]
    if encoder["type"] == "dense":
        channels = keras.layers.Dense(
            int(encoder["embedding_size"]), use_bias=False, name=f"{name}_embedding"
        )(channels)
    return tensor_in, channels


def head_labels(output: Mapping[str, Any]) -> tuple[str, ...]:
    """The labels a builder is given: the classes of a ``category``, one unit otherwise."""
    if output["type"] == "category":
        return tuple(output["preprocessing"]["fitted"]["labels"])
    if output["type"] == "anomaly":
        return ()
    return ONE_UNIT


def build_model(
    builder: Callable[..., Any],
    params: Mapping[str, Any],
    features: Sequence[Mapping[str, Any]],
    output: Mapping[str, Any],
    window: int | None,
) -> Any:
    """The whole model: inputs, preprocessing, the template's body, the head of the output type."""
    branches = [feature_branch(feature, window) for feature in features]
    inputs = [tensor_in for tensor_in, _ in branches]
    parts = [channels for _, channels in branches]
    tensor = (
        keras.layers.Concatenate(axis=-1, name="features")(parts) if len(parts) > 1 else parts[0]
    )
    channels = sum(channels_of(feature) for feature in features)
    if features[0]["type"] == "image":
        shape: tuple[int, ...] = tuple(int(size) for size in tensor.shape[1:])
    elif window is None:
        tensor = keras.layers.Reshape((channels,), name="record")(tensor)
        shape = (channels,)
    else:
        shape = (window, channels)

    body = builder(params, shape, head_labels(output))
    layers = list(body.layers)
    if output["type"] not in ("category", "anomaly"):
        layers = layers[:-1]
    seen = tensor
    for layer in layers:
        tensor = layer(tensor)

    if output["type"] == "anomaly":
        tensor = ReconstructionError(name="score")([tensor, seen])

    if output["type"] == "binary":
        tensor = keras.layers.Dense(1, activation="sigmoid", name="output")(tensor)
    elif output["type"] == "number":
        tensor = keras.layers.Dense(1, name="output")(tensor)
        fitted = output["preprocessing"]["fitted"]
        if fitted["normalization"] is not None:
            tensor = Rescale(fitted["shift"], fitted["scale"], name="output_rescale")(tensor)
        if output.get("clip") is not None:
            low, high = output["clip"]
            tensor = Clip(low, high, name="output_clip")(tensor)
    # One input is passed bare, as ``caravan.convert.batch`` rebuilds it: a list of one is a
    # different input structure to Keras, and the batch fix's clone would refuse it. No model had
    # a single input before images, which are always alone (CF-19).
    return keras.Model(
        inputs if len(inputs) > 1 else inputs[0], {output["name"]: tensor}, name=body.name
    )
