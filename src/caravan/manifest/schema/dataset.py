"""The dataset section.

Two fields here are statements by the author, never verified by this tool: ``license`` and
``permitted_use``. Caravan holds the author to what they state (rule CF-8) and reports what they
did not state as unverified (FR-032). Responsibility for the rights to the data stays with
whoever brings the data — Principle VI, as amended in constitution v2.1.0.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caravan.manifest.errors import RULE_SPLIT_SUM, rule_error

PermittedUse = Literal["training", "benchmark-only", "unknown"]

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
    """Where the data comes from, how it is split, and what the author says it permits."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    split: Split = Field(default_factory=Split)
    window: int | None = Field(default=None, gt=0)
    labels: list[str] = Field(min_length=2)
    representative_samples: int | None = Field(default=None, gt=0)
    license: str | None = None
    permitted_use: PermittedUse = "unknown"

    @model_validator(mode="after")
    def _labels_are_distinct_and_named(self) -> DatasetSpec:
        if any(not label.strip() for label in self.labels):
            raise ValueError("every label must be a non-empty name")
        if len(set(self.labels)) != len(self.labels):
            raise ValueError("labels must be distinct")
        return self
