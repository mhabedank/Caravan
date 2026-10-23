"""The model section: what is being built, and from which template."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

NAME_FORM = (
    "lower-case letters, digits and hyphens, starting with a letter or digit, at least 3 characters"
)
VERSION_FORM = "three dot-separated non-negative integers, for example 0.1.0"


class ModelSpec(BaseModel):
    """Identity, template and template parameters of one model version."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    name: str
    version: str
    template: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name_form(cls, value: str) -> str:
        # FR-019: when a value is rejected, the message states the form it must take.
        if len(value) < 3 or not NAME_PATTERN.match(value):
            raise ValueError(f"a model name must be {NAME_FORM}")
        return value

    @field_validator("version")
    @classmethod
    def _version_form(cls, value: str) -> str:
        if not VERSION_PATTERN.match(value):
            raise ValueError(f"a model version must be {VERSION_FORM}")
        return value
