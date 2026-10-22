"""Verification, benchmarking and publication.

``verify.emulator`` defaults to ``none`` rather than ``renode``: no emulator stage exists yet, and
two of the three boards shipped with this feature have no Renode platform at all. A default that
cannot be honoured for most targets is a false promise.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Emulator = Literal["renode", "none"]
Metric = Literal["latency_p50", "latency_p99", "ram_peak", "flash"]
License = Literal["apache-2.0", "mit", "cc-by-4.0"]


class VerifySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emulator: Emulator = "none"


class BenchSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[Metric] = Field(
        default_factory=lambda: ["latency_p50", "ram_peak", "flash"], min_length=1
    )

    @model_validator(mode="after")
    def _metrics_are_distinct(self) -> BenchSpec:
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("a benchmark metric must not be named twice")
        return self


class PublishSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hf_repo: str = Field(min_length=3, pattern=r"^[^/\s]+/[^/\s]+$")
    license: License = "apache-2.0"
