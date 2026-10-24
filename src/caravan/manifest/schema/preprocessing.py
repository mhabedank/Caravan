"""Global preprocessing: the window and the split, in Ludwig's names (feature 008).

What each feature does to its own column is the feature's preprocessing (``features.py``). What
applies to all rows lives here: how many consecutive records form one sample, and how samples are
divided into the training, validation and test parts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caravan.manifest.errors import RULE_SPLIT_COLUMN_WITH_FRACTIONS, RULE_SPLIT_SUM, rule_error

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


class Split(BaseModel):
    """``random`` draws by seed, ``stratify`` per class, ``fixed`` reads each record's part."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["random", "stratify", "fixed"] = "random"
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
        return data

    @model_validator(mode="after")
    def _probabilities(self) -> Split:
        if self.type == "fixed":
            return self
        if self.type == "random" and self.column is not None:
            raise ValueError(
                "a random split reads no column; use type stratify to split per class, or fixed "
                "to take the parts from the column"
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
    #: window (rule CF-6). Windows never overlap.
    window_size: int | None = Field(default=None, gt=0)
    split: Split = Field(default_factory=Split)
