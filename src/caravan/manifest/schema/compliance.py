"""The compliance section — required for every manifest, by the schema (Principle VI).

A required schema field is checked on every run by every contributor; a review checklist is
checked when someone remembers.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RiskClass = Literal["minimal-risk", "limited-risk", "high-risk"]
Privacy = Literal["no-personal-data", "anonymized", "personal-data"]


class ComplianceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eu_ai_act_class: RiskClass
    privacy: Privacy
    intended_use: str = Field(min_length=20)
    known_limits: list[str] = Field(min_length=1)

    @field_validator("intended_use")
    @classmethod
    def _intended_use_is_substantive(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("intended use must say something, not only whitespace")
        return value

    @field_validator("known_limits")
    @classmethod
    def _limits_are_named(cls, value: list[str]) -> list[str]:
        if any(not limit.strip() for limit in value):
            raise ValueError("every known limit must be a non-empty statement")
        return value
