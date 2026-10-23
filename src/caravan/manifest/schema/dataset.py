"""The dataset section: where the data comes from and how it is split.

What the data *means* — which columns go in, which one holds the answer, what the classes are — is
declared by the input and the output (``schema/io.py``), and what follows from the data is derived
from it rather than asked for (constitution 3.0.0, Principle I). Rights to the data are the
author's; Caravan neither asks about them nor claims to check them (Principle VI).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caravan.manifest.errors import RULE_SPLIT_SUM, rule_error

#: The documented floor for int8 calibration. Calibration data determines the quantized
#: activation ranges; too few or unrepresentative samples are a known cause of accuracy collapse,
#: so this is a schema requirement rather than a convention. More is better.
MINIMUM_REPRESENTATIVE_SAMPLES = 100


class Split(BaseModel):
    """Named parts, never a positional list (FR-018)."""

    model_config = ConfigDict(extra="forbid")

    train: float = 0.7
    val: float = 0.15
    test: float = 0.15
    stratified: bool = True

    @model_validator(mode="after")
    def _parts_sum_to_one(self) -> Split:
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
