"""The training section. Every field has a documented default (Principle I)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TrainSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    epochs: int = Field(default=50, gt=0)
    batch: int = Field(default=256, gt=0)
    optimizer: Literal["adam", "sgd", "adamw"] = "adam"
    learning_rate: float = Field(default=1e-3, gt=0)
    early_stopping: bool = True
    patience: int = Field(default=5, ge=0)
    #: Recorded in every run report, because reproducibility is from configuration (Principle III).
    seed: int = 42
