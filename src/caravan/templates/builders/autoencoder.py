"""The builder half of the ``autoencoder`` template (feature 010).

The parameter half is ``caravan/templates/autoencoder.py`` and lives in the core. This module
imports Keras, so it is reachable only with the ``train`` extra, and it is imported by name when a
stage asks for it.

It returns the *reconstruction*: a model whose output has the input's shape. The score is not the
template's business — the front-end's ``anomaly`` head compares the reconstruction with the input as
the model saw it after preprocessing (``frontend.py``), which is why the template answers the
``anomaly`` output and only that one.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import keras

from caravan.templates.autoencoder import AutoencoderParameters


def build(
    params: Mapping[str, Any] | AutoencoderParameters,
    input_shape: tuple[int, ...],
    labels: Sequence[str],
) -> Any:
    """A window in, the same window reconstructed out.

    Flatten, the encoder's dense layers with ReLU, the linear code, the decoder's dense layers with
    ReLU, one linear dense layer as wide as the window, and a reshape back to the window's shape.
    ``labels`` is accepted because every builder takes it; an autoencoder has none.
    """
    del labels
    settings = (
        params
        if isinstance(params, AutoencoderParameters)
        else AutoencoderParameters.model_validate(params)
    )
    width = math.prod(input_shape)

    layers: list[Any] = [keras.layers.Input(shape=input_shape, name="input")]
    if len(input_shape) > 1:
        layers.append(keras.layers.Flatten(name="flatten"))
    for position, units in enumerate(settings.encoder, start=1):
        layers.append(keras.layers.Dense(units, activation="relu", name=f"encoder_{position}"))
        if settings.dropout:
            layers.append(
                keras.layers.Dropout(settings.dropout, name=f"encoder_dropout_{position}")
            )
    layers.append(keras.layers.Dense(settings.code, name="code"))
    for position, units in enumerate(settings.decoder_widths(), start=1):
        layers.append(keras.layers.Dense(units, activation="relu", name=f"decoder_{position}"))
        if settings.dropout:
            layers.append(
                keras.layers.Dropout(settings.dropout, name=f"decoder_dropout_{position}")
            )
    layers.append(keras.layers.Dense(width, name="reconstruction"))
    if len(input_shape) > 1:
        layers.append(keras.layers.Reshape(input_shape, name="reconstruction_shape"))

    return keras.Sequential(layers, name="autoencoder")
