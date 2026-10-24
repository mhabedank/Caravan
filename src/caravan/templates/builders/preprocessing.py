"""The preprocessing layers each feature type brings into the model (feature 008, research R3).

Behind the ``train`` extra: it imports Keras. The layers are registered, take their fitted values
as constructor arguments and nothing else, so they survive saving, loading and the batch fix
(``caravan.convert.batch``) unchanged — no ``Lambda``, no adapt-state.

Each lowers only to operators TFLite Micro has at ``f7ed40d`` (research note, sections 1-2):

* ``Standardize`` — ``(x - shift) * (1 / scale)``: SUB, MUL, after the converter's QUANTIZE;
* ``VocabularyOneHot`` — EQUAL of the int32 code against the constant vocabulary, CAST, RELU, and
  an "unknown" slot ``1 - SUM`` at index 0: exact for every code, an unseen one lands in slot 0.
  The RELU is the identity on 0 and 1; it is there because it is where the converter quantizes.
  Without it the converter keeps the SUM, the SUB and the CONCATENATION in float32 and, worse,
  dequantizes the other features to concatenate them in float (measured 2026-10-24, TF 2.21.0);
  with it the only float32 tensor of the branch is the CAST's output, consumed by a QUANTIZE;
* ``AsChannel`` — CAST of a 0/1 int32 to a channel, and the same RELU;
* ``Rescale`` — the inverse of ``Standardize`` for a ``number`` output, and ``Clip`` for its
  bounds (MAXIMUM, MINIMUM).

The dense encoder of a ``category`` is a plain ``Dense`` without bias on the one-hot: an embedding
computed as a matrix product, which lowers to FULLY_CONNECTED rather than to the GATHER and SELECT
v1 a Keras ``Embedding`` produces (research R3, R4).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import keras
import numpy as np

PACKAGE = "caravan"


@keras.saving.register_keras_serializable(package=PACKAGE)
class Standardize(keras.layers.Layer):
    """A ``number`` input: ``(x - shift) / scale``, one channel per step."""

    def __init__(self, shift: float, scale: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.shift = float(shift)
        self.scale = float(scale)

    def call(self, inputs: Any) -> Any:
        centred = keras.ops.subtract(inputs, self.shift)
        return keras.ops.expand_dims(keras.ops.multiply(centred, 1.0 / self.scale), -1)

    def compute_output_shape(self, input_shape: Sequence[int | None]) -> tuple[int | None, ...]:
        return (*input_shape, 1)

    def get_config(self) -> dict[str, Any]:
        return {**super().get_config(), "shift": self.shift, "scale": self.scale}


@keras.saving.register_keras_serializable(package=PACKAGE)
class VocabularyOneHot(keras.layers.Layer):
    """A ``category`` input: int32 codes to V+1 channels, "unknown" at index 0."""

    def __init__(self, codes: Sequence[int], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.codes = [int(code) for code in codes]

    def call(self, inputs: Any) -> Any:
        table = keras.ops.convert_to_tensor(np.array(self.codes, dtype=np.int32))
        hits = keras.ops.cast(keras.ops.equal(keras.ops.expand_dims(inputs, -1), table), "float32")
        # The identity on 0 and 1, and the point where the conversion quantizes (see above).
        hits = keras.ops.relu(hits)
        unknown = keras.ops.subtract(1.0, keras.ops.sum(hits, axis=-1, keepdims=True))
        return keras.ops.concatenate([unknown, hits], axis=-1)

    def compute_output_shape(self, input_shape: Sequence[int | None]) -> tuple[int | None, ...]:
        return (*input_shape, len(self.codes) + 1)

    def get_config(self) -> dict[str, Any]:
        return {**super().get_config(), "codes": list(self.codes)}


@keras.saving.register_keras_serializable(package=PACKAGE)
class AsChannel(keras.layers.Layer):
    """A ``binary`` input: the int32 0/1 as one float channel per step."""

    def call(self, inputs: Any) -> Any:
        # The RELU is the identity on 0 and 1 and the point where the conversion quantizes, as in
        # ``VocabularyOneHot``: a CAST straight into the concatenation would keep it in float.
        return keras.ops.expand_dims(keras.ops.relu(keras.ops.cast(inputs, "float32")), -1)

    def compute_output_shape(self, input_shape: Sequence[int | None]) -> tuple[int | None, ...]:
        return (*input_shape, 1)


@keras.saving.register_keras_serializable(package=PACKAGE)
class Rescale(keras.layers.Layer):
    """A ``number`` output: ``x * scale + shift``, back in the column's unit."""

    def __init__(self, shift: float, scale: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.shift = float(shift)
        self.scale = float(scale)

    def call(self, inputs: Any) -> Any:
        return keras.ops.add(keras.ops.multiply(inputs, self.scale), self.shift)

    def get_config(self) -> dict[str, Any]:
        return {**super().get_config(), "shift": self.shift, "scale": self.scale}


@keras.saving.register_keras_serializable(package=PACKAGE)
class Clip(keras.layers.Layer):
    """A ``number`` output's ``clip: [low, high]``."""

    def __init__(self, low: float, high: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.low = float(low)
        self.high = float(high)

    def call(self, inputs: Any) -> Any:
        return keras.ops.minimum(keras.ops.maximum(inputs, self.low), self.high)

    def get_config(self) -> dict[str, Any]:
        return {**super().get_config(), "low": self.low, "high": self.high}


#: The layers this module registers, for a check that a model carries nothing else of its own.
REGISTERED = (Standardize, VocabularyOneHot, AsChannel, Rescale, Clip)
