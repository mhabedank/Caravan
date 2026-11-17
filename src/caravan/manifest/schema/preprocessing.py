"""Global preprocessing: the window and the split, in Ludwig's names (feature 008).

What each feature does to its own column is the feature's preprocessing (``features.py``). What
applies to all rows lives here: how many consecutive records form one sample, how often a new one
starts, what label it carries, where one recording ends and the next begins, and how samples are
divided into the training, validation and test parts.

Feature 014 (``caravan/v0.3``) added the recording-aware fields: ``window_stride``,
``window_label``, ``recording_column``, and the split types ``recording``, ``group`` and
``blocked``. Ludwig has no names for these, so they carry Caravan's own plain words.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caravan.manifest.errors import (
    RULE_RECORDING_COLUMN,
    RULE_SPLIT_COLUMN_WITH_FRACTIONS,
    RULE_SPLIT_SUM,
    rule_error,
)

#: Ludwig's default split, train / validation / test.
DEFAULT_PROBABILITIES = (0.7, 0.15, 0.15)

#: The values a record of a fixed split may hold: Ludwig's numbers and the words (research R8).
FIXED_SPLIT_VALUES: dict[str, str] = {
    "0": "train",
    "1": "val",
    "2": "test",
    "train": "train",
    "validation": "val",
    "test": "test",
}


#: Every split type. ``recording``, ``group`` and ``blocked`` assign whole groups of windows, so
#: neighbouring windows of one recording never sit on both sides of a part boundary (feature 014).
SplitType = Literal["random", "stratify", "fixed", "recording", "group", "blocked"]

#: The split types that assign groups rather than single windows; overlapping training windows are
#: allowed only with these (rule CF-21) and with the derived default.
GROUPED_SPLITS: tuple[str, ...] = ("fixed", "recording", "group", "blocked")

#: The window label rules that are a plain word. ``{any: <value>}`` is the one with a value.
WindowLabelName = Literal["all_equal", "last", "majority", "mean"]


class AnyLabel(BaseModel):
    """``{any: <value>}``: a window holding this value in any row takes it (feature 014)."""

    model_config = ConfigDict(extra="forbid")

    any: str | int | bool

    @property
    def value(self) -> str:
        """The value as the reader writes labels: text."""
        if isinstance(self.any, bool):
            return "true" if self.any else "false"
        return str(self.any)


class Split(BaseModel):
    """How windows become the training, validation and test parts.

    ``random`` draws by seed, ``stratify`` per class, ``fixed`` reads each record's part from a
    column. ``recording`` keeps every recording in one part, ``group`` every value of a column, and
    ``blocked`` assigns contiguous blocks of one recording (feature 014). Left out with a window,
    the type is derived from the data at run time: ``recording`` with three or more recordings,
    ``blocked`` otherwise.
    """

    model_config = ConfigDict(extra="forbid")

    type: SplitType | None = None
    probabilities: list[float] | None = Field(default=None, min_length=3, max_length=3)
    column: str | None = Field(default=None, min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _one_form_only(cls, data: Any) -> Any:
        # CF-12 on the raw input, so a stated fraction is never dropped without a word.
        if isinstance(data, dict) and data.get("type") == "fixed":
            if "probabilities" in data:
                rule_error(
                    RULE_SPLIT_COLUMN_WITH_FRACTIONS,
                    "preprocessing.split.probabilities",
                    "a fixed split takes its parts from a column of the data; probabilities would "
                    "be ignored, so they are not accepted beside it",
                    found=data["probabilities"],
                )
            if not data.get("column"):
                rule_error(
                    RULE_SPLIT_COLUMN_WITH_FRACTIONS,
                    "preprocessing.split.column",
                    "a fixed split takes its parts from a column of the data, so the column must "
                    "be named",
                )
        if isinstance(data, dict) and data.get("type") == "group" and not data.get("column"):
            rule_error(
                RULE_RECORDING_COLUMN,
                "preprocessing.split.column",
                "a group split keeps all rows with the same value of a column in one part, so the "
                "column must be named",
            )
        return data

    @model_validator(mode="after")
    def _probabilities(self) -> Split:
        if self.type == "fixed":
            return self
        if self.type in (None, "random", "recording", "blocked") and self.column is not None:
            kind = self.type or "derived"
            raise ValueError(
                f"a {kind} split reads no column; use type group to keep each value of the column "
                "in one part, stratify to split per class, or fixed to take the parts from the "
                "column"
            )
        if self.probabilities is None:
            self.probabilities = list(DEFAULT_PROBABILITIES)
        # CF-1. A part of zero is rejected: a part with no data cannot be trained on, tuned on or
        # evaluated against.
        names = ("train", "validation", "test")
        empty = [name for name, value in zip(names, self.probabilities, strict=True) if value <= 0]
        if empty:
            rule_error(
                RULE_SPLIT_SUM,
                "preprocessing.split.probabilities",
                f"every part must be greater than zero; {', '.join(empty)} is not",
                found=list(self.probabilities),
            )
        total = sum(self.probabilities)
        if abs(total - 1.0) > 1e-6:
            rule_error(
                RULE_SPLIT_SUM,
                "preprocessing.split.probabilities",
                f"the parts train, validation and test must sum to 1.0; they sum to {total:g}",
                found=list(self.probabilities),
            )
        return self


class GlobalPreprocessing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: How many consecutive records form one sample. Required exactly when the template consumes a
    #: window (rule CF-6).
    window_size: int | None = Field(default=None, gt=0)
    #: How many records apart two windows start, within one recording. Left out, the window size:
    #: windows do not overlap. Smaller only with a split that assigns groups (rule CF-21).
    window_stride: int | None = None
    #: How a window's rows' labels become the window's label. Left out: ``last`` for a ``number``
    #: output, ``all_equal`` otherwise (feature 014, research R3).
    window_label: WindowLabelName | AnyLabel | None = None
    #: A column whose change of value starts a new recording. Left out, each file is one recording.
    recording_column: str | None = Field(default=None, min_length=1)
    split: Split = Field(default_factory=Split)

    def label_rule(self) -> str | dict[str, str] | None:
        """The rule as stated, in the form the resolved manifest and the contract carry it."""
        rule = self.window_label
        if isinstance(rule, AnyLabel):
            return {"any": rule.value}
        return rule
