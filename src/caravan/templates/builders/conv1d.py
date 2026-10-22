"""The builder half of the ``conv1d`` template.

The other half — the parameter schema — is ``caravan/templates/conv1d.py`` and lives in the core.
This module imports Keras, so it is only ever reachable with the ``train`` extra installed, and it
is imported by name when a stage asks for it rather than by any discovery walk.

It validates what it was given through the parameter half, so the two halves cannot drift.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import keras

from caravan.templates.conv1d import Conv1dParameters


def build(
    params: Mapping[str, Any] | Conv1dParameters,
    input_shape: tuple[int, ...],
    labels: Sequence[str],
) -> Any:
    """A window of samples in, one score per class out.

    The order inside a block is the one decision this builder makes:

        convolution → (normalisation) → activation → (pooling) → (dropout)

    Normalisation goes *before* the activation because that is the order it folds into the
    convolution in, and the fold is the only reason it is offered: measured 2026-10-22, it adds no
    operator to the converted model and 648 bytes of folded weights. Put after the activation it
    would be a separate operator on the target for no gain.

    The activation is the rectifier the dense template uses. It stays unparameterised until a named
    model asks for another one (Principle X).
    """
    settings = (
        params if isinstance(params, Conv1dParameters) else Conv1dParameters.model_validate(params)
    )

    layers: list[Any] = [keras.layers.Input(shape=input_shape, name="input")]
    for position, block in enumerate(settings.blocks, start=1):
        layers.append(
            keras.layers.Conv1D(
                filters=block.filters,
                kernel_size=block.kernel,
                strides=block.stride,
                padding=block.padding,
                # No activation here: it comes after the normalisation, for the reason above.
                name=f"conv_{position}",
            )
        )
        if block.normalise:
            layers.append(keras.layers.BatchNormalization(name=f"norm_{position}"))
        layers.append(keras.layers.ReLU(name=f"relu_{position}"))
        if block.pool:
            layers.append(keras.layers.MaxPooling1D(pool_size=block.pool, name=f"pool_{position}"))
        if block.dropout:
            # Only where the author asked for it: a zero-rate dropout layer is noise in a
            # per-layer table, which is the same rule the dense template follows.
            layers.append(keras.layers.Dropout(block.dropout, name=f"dropout_{position}"))

    if settings.head == "average":
        layers.append(keras.layers.GlobalAveragePooling1D(name="pool_head"))
    else:
        layers.append(keras.layers.Flatten(name="flatten_head"))
    layers.append(keras.layers.Dense(len(labels), activation="softmax", name="output"))

    return keras.Sequential(layers, name="conv1d")
