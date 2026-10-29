"""The builder half of the ``conv2d`` template (feature 010).

The parameter half — the schema and the plane arithmetic — is ``caravan/templates/conv2d.py`` and
lives in the core. This module imports Keras, so it is reachable only with the ``train`` extra, and
is imported by name when a stage asks for it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import keras

from caravan.templates.conv2d import Conv2dParameters
from caravan.templates.plane import as_pair, walk_plane


def build(
    params: Mapping[str, Any] | Conv2dParameters,
    input_shape: tuple[int, ...],
    labels: Sequence[str],
) -> Any:
    """A plane in, one score per class out.

    ``input_shape`` is (rows, columns) for a window — reshaped here to one channel, which converts
    to a RESHAPE and nothing else (research R3) — or (height, width, channels) for an image.

    Within a block the order is the one ``conv1d`` uses and for the same reason:

        convolution → (normalisation) → ReLU → (pooling) → (dropout)

    with normalisation before the activation because that is the order it folds into the
    convolution in. A separable block is a depthwise convolution with the block's kernel and
    stride, its normalisation and ReLU, then a 1 x 1 convolution with the block's filters, its
    normalisation and ReLU — the DS-CNN and MobileNetV1 pattern. Convolutions keep their bias, as in
    ``conv1d`` and the MLPerf keyword-spotting code (research R4).
    """
    settings = (
        params if isinstance(params, Conv2dParameters) else Conv2dParameters.model_validate(params)
    )
    layers: list[Any] = [keras.layers.Input(shape=input_shape, name="input")]
    if len(input_shape) == 2:
        layers.append(keras.layers.Reshape((*input_shape, 1), name="plane"))

    def activation(position: int, suffix: str = "") -> None:
        if settings.blocks[position - 1].normalise:
            layers.append(keras.layers.BatchNormalization(name=f"norm_{position}{suffix}"))
        layers.append(keras.layers.ReLU(name=f"relu_{position}{suffix}"))

    for position, block in enumerate(settings.blocks, start=1):
        kernel = as_pair(block.kernel)
        stride = as_pair(block.stride)
        if block.kind == "standard":
            layers.append(
                keras.layers.Conv2D(
                    block.filters,
                    kernel,
                    strides=stride,
                    padding=block.padding,
                    name=f"conv_{position}",
                )
            )
            activation(position)
        else:
            layers.append(
                keras.layers.DepthwiseConv2D(
                    kernel, strides=stride, padding=block.padding, name=f"depthwise_{position}"
                )
            )
            activation(position, "_depthwise")
            layers.append(keras.layers.Conv2D(block.filters, 1, name=f"pointwise_{position}"))
            activation(position)
        pool = as_pair(block.pool)
        if pool is not None:
            layers.append(keras.layers.MaxPooling2D(pool_size=pool, name=f"pool_{position}"))
        if block.dropout:
            layers.append(keras.layers.Dropout(block.dropout, name=f"dropout_{position}"))

    if settings.head == "average":
        # Over the whole remaining plane, computed by the same walk the refusals use: a pooling
        # rather than a global mean, because only the pooling is accelerated (research R2).
        outcome = walk_plane(input_shape[0], input_shape[1], settings.as_blocks())
        if not outcome.fits:  # pragma: no cover - refused by CF-6 before a builder runs
            raise ValueError(f"the plane {input_shape[:2]} does not fit the blocks")
        rows, columns = outcome.final
        layers.append(keras.layers.AveragePooling2D(pool_size=(rows, columns), name="pool_head"))
    layers.append(keras.layers.Flatten(name="flatten_head"))
    layers.append(keras.layers.Dense(len(labels), activation="softmax", name="output"))

    return keras.Sequential(layers, name="conv2d")
