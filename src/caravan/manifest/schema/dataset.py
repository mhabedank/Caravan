"""The dataset section: where the data comes from and how it is split.

What the data *means* — which columns go in, which one holds the answer, what the classes are — is
declared by the input and the output (``schema/io.py``), and what follows from the data is derived
from it rather than asked for (constitution 3.0.0, Principle I). Rights to the data are the
author's; Caravan neither asks about them nor claims to check them (Principle VI).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caravan.manifest.errors import RULE_SPLIT_COLUMN_WITH_FRACTIONS, RULE_SPLIT_SUM, rule_error

#: The documented floor for int8 calibration. Calibration data determines the quantized
#: activation ranges; too few or unrepresentative samples are a known cause of accuracy collapse,
#: so this is a schema requirement rather than a convention. More is better.
MINIMUM_REPRESENTATIVE_SAMPLES = 100

#: The fields of the fractions form, none of which a fixed split accepts (CF-12).
FRACTION_FIELDS = ("train", "val", "test", "stratified")
#: What a record of a fixed split may name.
PART_NAMES = ("train", "val", "test")


class Split(BaseModel):
    """Named parts, never a positional list (FR-018) — or a column of the data that names them.

    Two forms (feature 007, research R9). With fractions, samples are drawn into the parts by
    seed. With ``column``, every record names its own part, ``train``, ``val`` or ``test``, so a
    dataset can keep subjects, vehicles or sessions on one side of the split. The fractions and
    ``stratified`` are absent from the second form rather than ignored in it (CF-12).
    """

    model_config = ConfigDict(extra="forbid")

    train: float | None = None
    val: float | None = None
    test: float | None = None
    stratified: bool | None = None
    column: str | None = Field(default=None, min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _one_form_only(cls, data: Any) -> Any:
        # CF-12, on the raw input: a fraction the author wrote beside the column would otherwise be
        # dropped without a word, and so would `stratified: true`.
        if isinstance(data, dict) and data.get("column") is not None:
            stated = sorted(key for key in FRACTION_FIELDS if key in data)
            if stated:
                rule_error(
                    RULE_SPLIT_COLUMN_WITH_FRACTIONS,
                    "dataset.split",
                    f"a fixed split takes its parts from the column {data['column']!r}; "
                    f"{', '.join(stated)} would be ignored, so they are not accepted beside it",
                    found=stated,
                )
        return data

    @model_validator(mode="after")
    def _parts_sum_to_one(self) -> Split:
        if self.column is not None:
            return self
        # The fractions form, with the documented defaults for what the author left out.
        self.train = 0.7 if self.train is None else self.train
        self.val = 0.15 if self.val is None else self.val
        self.test = 0.15 if self.test is None else self.test
        self.stratified = True if self.stratified is None else self.stratified
        # CF-1. A part of zero is rejected: a part with no data cannot be trained on, tuned on or
        # evaluated against, and the frozen test part is the reference for every later result.
        parts = {"train": self.train, "val": self.val, "test": self.test}
        empty = sorted(name for name, value in parts.items() if value <= 0)
        if empty:
            rule_error(
                RULE_SPLIT_SUM,
                "dataset.split",
                f"every part must be greater than zero; {', '.join(empty)} is not",
                found={name: value for name, value in parts.items()},
            )
        total = sum(parts.values())
        if abs(total - 1.0) > 1e-6:
            rule_error(
                RULE_SPLIT_SUM,
                "dataset.split",
                f"the parts train, val and test must sum to 1.0; they sum to {total:g}",
                found={name: value for name, value in parts.items()},
            )
        return self


class DatasetSpec(BaseModel):
    """Where the data comes from and how it is split."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    split: Split = Field(default_factory=Split)
    representative_samples: int | None = Field(default=None, gt=0)
