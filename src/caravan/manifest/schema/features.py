"""Input and output features, in Ludwig's names (feature 008, contracts/manifest.md).

A manifest lists the columns the model reads, one feature per column, each with a ``type``; the
type brings its preprocessing, which is fitted on the training part and built into the model, so
the firmware passes raw values (research R1-R3). The output feature says what the model answers
and the int8 budget its quantization is held to (Principle V).

Every key here is optional but ``name`` and ``type``. What a key left out means is decided in this
order: the feature's own value, then ``defaults`` for its type, then the type's default
(``resolve.py``). A key that does not apply to the feature's type is refused rather than ignored
(Principle I): it would be read by nobody.

The form of a name, the set of implemented types and the budget's match with the output type are
checked by the manifest, not here: only the manifest knows a feature's position, and a rule's
finding carries its full path, ``input_features[2].type`` rather than ``type``.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: What a feature name must look like. The intersection of a C identifier, which the exported
#: header uses, and a name a converted model's signature keeps intact (feature 006, research R2,
#: R4). In ``caravan/v0.2`` the name is also the data column the feature reads.
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
NAME_FORM = (
    "a lower-case letter followed by up to 31 lower-case letters, digits or underscores, "
    "for example can_id or body_acc_x"
)

#: The input and output types this build implements (feature 008, Principle X). Each has a path to
#: the device: an operator TFLite Micro has, and an element type the firmware can pass.
INPUT_TYPES: tuple[str, ...] = ("number", "binary", "category")
OUTPUT_TYPES: tuple[str, ...] = ("category", "binary", "number")

Normalization = Literal["zscore", "minmax", "iq"]
MissingValueStrategy = Literal["fill_with_const", "fill_with_mean"]
EncoderType = Literal["dense", "onehot"]
NumberLoss = Literal["mean_squared_error", "mean_absolute_error", "huber"]

#: Which preprocessing key applies to which input type. A key outside its types is refused.
INPUT_PREPROCESSING_KEYS: dict[str, tuple[str, ...]] = {
    "normalization": ("number",),
    "missing_value_strategy": ("number", "binary", "category"),
    "fill_value": ("number", "binary", "category"),
    "most_common": ("category",),
    "vocab": ("category",),
    "fallback_true_label": ("binary",),
}

#: The strategies each input type accepts. ``fill_with_mean`` needs a mean, so a number.
STRATEGIES: dict[str, tuple[str, ...]] = {
    "number": ("fill_with_const", "fill_with_mean"),
    "binary": ("fill_with_const",),
    "category": ("fill_with_const",),
}

#: Which output key applies to which output type.
OUTPUT_KEYS: dict[str, tuple[str, ...]] = {
    "preprocessing.vocab": ("category",),
    "preprocessing.fallback_true_label": ("binary",),
    "preprocessing.normalization": ("number",),
    "loss.class_weights": ("category",),
    "loss.positive_class_weight": ("binary",),
    "loss.type": ("number",),
    "threshold": ("binary",),
    "clip": ("number",),
    "accuracy_drop_max": ("category", "binary"),
    "mae_increase_max": ("number",),
}


def name_problem(name: str) -> str | None:
    """Why a feature name is not acceptable, or ``None`` when it is."""
    if NAME_PATTERN.match(name):
        return None
    return f"a feature name must be {NAME_FORM}"


def _distinct(values: list[Any], what: str) -> list[Any]:
    if any(isinstance(value, str) and not value.strip() for value in values):
        raise ValueError(f"every {what} must be non-empty")
    if len({str(value) for value in values}) != len(values):
        raise ValueError(f"the {what}s must be distinct")
    return values


class InputPreprocessing(BaseModel):
    """Every preprocessing key an input feature may state. Which ones apply depends on the type."""

    model_config = ConfigDict(extra="forbid")

    #: ``null`` is a value (no normalization), so "left out" is told apart by ``model_fields_set``.
    normalization: Normalization | None = None
    missing_value_strategy: MissingValueStrategy | None = None
    fill_value: str | float | int | bool | None = None
    most_common: int | None = Field(default=None, gt=0)
    #: Pins the vocabulary and its order. Codes as the data spells them: integers or text.
    vocab: list[str | int] | None = Field(default=None, min_length=1)
    fallback_true_label: str | None = Field(default=None, min_length=1)

    @field_validator("vocab")
    @classmethod
    def _vocab_is_distinct(cls, value: list[Any] | None) -> list[Any] | None:
        return None if value is None else _distinct(value, "vocabulary entry")


class Encoder(BaseModel):
    """How a ``category`` input becomes channels: an embedding (``dense``) or the one-hot."""

    model_config = ConfigDict(extra="forbid")

    type: EncoderType | None = None
    embedding_size: int | None = Field(default=None, gt=0)


class InputFeature(BaseModel):
    """One column the model reads."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    preprocessing: InputPreprocessing = Field(default_factory=InputPreprocessing)
    encoder: Encoder | None = None


def input_key_problem(
    feature_type: str, preprocessing: InputPreprocessing, encoder: Encoder | None
) -> tuple[str, str] | None:
    """A key that does not apply to the type, as (relative path, problem); nothing would read it.

    Principle I: a key is either read or refused, never ignored.
    """
    for key in sorted(preprocessing.model_fields_set):
        applies = INPUT_PREPROCESSING_KEYS[key]
        if feature_type not in applies:
            return (
                f"preprocessing.{key}",
                f"does not apply to a {feature_type} feature; it applies to "
                f"{' and '.join(applies)}",
            )
    fill = preprocessing.fill_value
    if (
        feature_type == "number"
        and "fill_value" in preprocessing.model_fields_set
        and (isinstance(fill, bool) or not isinstance(fill, int | float))
    ):
        return ("preprocessing.fill_value", "a number feature is filled with a number")
    strategy = preprocessing.missing_value_strategy
    if strategy is not None and strategy not in STRATEGIES[feature_type]:
        return (
            "preprocessing.missing_value_strategy",
            f"{strategy} does not apply to a {feature_type} feature; it accepts "
            f"{', '.join(STRATEGIES[feature_type])}",
        )
    if encoder is not None and feature_type != "category":
        return ("encoder", f"does not apply to a {feature_type} feature; it applies to category")
    if encoder is not None and encoder.type == "onehot" and encoder.embedding_size is not None:
        return (
            "encoder.embedding_size",
            "does not apply to the onehot encoder, which gives one channel per vocabulary entry; "
            "it applies to dense",
        )
    return None


class OutputPreprocessing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: Pins the label order of a ``category`` output, as ``outputs[0].labels`` did.
    vocab: list[str] | None = Field(default=None, min_length=2)
    fallback_true_label: str | None = Field(default=None, min_length=1)
    normalization: Normalization | None = None

    @field_validator("vocab")
    @classmethod
    def _vocab_is_distinct(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _distinct(value, "label")


class Loss(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: NumberLoss | None = None
    #: In label order, or a map label -> weight.
    class_weights: list[float] | dict[str, float] | None = None
    positive_class_weight: float | None = Field(default=None, gt=0)


class OutputFeature(BaseModel):
    """What comes out of the model, and the budget its quantization is held to."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    preprocessing: OutputPreprocessing = Field(default_factory=OutputPreprocessing)
    loss: Loss = Field(default_factory=Loss)
    #: The device decision of a ``binary`` output: true when the score is at least this.
    threshold: float | None = Field(default=None, gt=0.0, lt=1.0)
    #: Bounds a ``number`` output, in the column's unit.
    clip: list[float] | None = Field(default=None, min_length=2, max_length=2)
    #: The int8 budget of a ``category`` or ``binary`` output: accuracy lost to quantization.
    accuracy_drop_max: float | None = Field(default=None, ge=0.0, le=1.0)
    #: The int8 budget of a ``number`` output: the increase of the mean absolute error, in the
    #: column's unit.
    mae_increase_max: float | None = Field(default=None, ge=0.0)

    @field_validator("clip")
    @classmethod
    def _clip_is_ordered(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and not value[0] < value[1]:
            raise ValueError("clip must be [low, high] with low below high")
        return value

    def stated_keys(self) -> list[str]:
        """The type-specific keys the author wrote, as dotted paths."""
        stated = [
            key
            for key in ("threshold", "clip", "accuracy_drop_max", "mae_increase_max")
            if key in self.model_fields_set
        ]
        stated += [f"preprocessing.{key}" for key in self.preprocessing.model_fields_set]
        stated += [f"loss.{key}" for key in self.loss.model_fields_set]
        return sorted(stated)
