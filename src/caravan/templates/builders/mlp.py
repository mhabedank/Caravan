"""The builder half of the ``mlp`` template.

The other half — the parameter schema — is ``caravan/templates/mlp.py`` and lives in the core. This
module imports Keras, so it is only ever reachable with the ``train`` extra installed, and it is
imported by name when a stage asks for it rather than by any discovery walk.

It uses the parameter half to validate what it was given. A builder that trusted a raw mapping
would be the place where the two halves of a template drift apart.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import keras

from caravan.templates.mlp import MlpParameters


def build(
    params: Mapping[str, Any] | MlpParameters,
    input_shape: tuple[int, ...],
    labels: Sequence[str],
) -> Any:
    """A window in, one class out.

    ``Flatten`` first, so a window of records and a single record are the same model with a
    different input shape — which is what lets ``conv1d`` arrive later without changing what a
    template means. Dropout appears only where the author asked for it: a zero-rate dropout layer
    in the per-layer table is noise in a report.
    """
    settings = params if isinstance(params, MlpParameters) else MlpParameters.model_validate(params)

    layers: list[Any] = [keras.layers.Input(shape=input_shape, name="input")]
    if len(input_shape) > 1:
        layers.append(keras.layers.Flatten(name="flatten"))
    for position, width in enumerate(settings.hidden, start=1):
        layers.append(keras.layers.Dense(width, activation="relu", name=f"hidden_{position}"))
        if settings.dropout:
            layers.append(keras.layers.Dropout(settings.dropout, name=f"dropout_{position}"))
    layers.append(keras.layers.Dense(len(labels), activation="softmax", name="output"))

    return keras.Sequential(layers, name="mlp")
