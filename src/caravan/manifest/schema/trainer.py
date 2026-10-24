"""The trainer section, in Ludwig's names. Every field has a documented default (Principle I)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Optimizer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["adam", "sgd", "adamw"] = "adam"


class TrainerSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    epochs: int = Field(default=50, gt=0)
    batch_size: int = Field(default=256, gt=0)
    learning_rate: float = Field(default=1e-3, gt=0)
    optimizer: Optimizer = Field(default_factory=Optimizer)
    #: Epochs without improvement of the validation loss before training stops; -1 never stops.
    early_stop: int = Field(default=5, ge=-1)
