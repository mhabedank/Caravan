"""The export section.

Format identifiers are deliberately not vendor product names: a rename of a product would
otherwise become a schema migration (constitution amendment 8, research R8). ``flatbuffer`` is the
serialised model, ``c_array`` the C source form of it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caravan.manifest.errors import RULE_DUPLICATE_TARGETS, rule_error

Quantization = Literal["int8", "float16", "none"]
Format = Literal["flatbuffer", "c_array", "onnx"]


class ExportSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantization: Quantization = "int8"
    formats: list[Format] = Field(default_factory=lambda: ["flatbuffer", "c_array"])
    targets: list[str] = Field(min_length=1)
    accuracy_drop_max: float = Field(default=0.02, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _targets_and_formats_are_distinct(self) -> ExportSpec:
        # CF-2: duplicates are rejected, never silently de-duplicated.
        duplicates = sorted({t for t in self.targets if self.targets.count(t) > 1})
        if duplicates:
            rule_error(
                RULE_DUPLICATE_TARGETS,
                "export.targets",
                f"a target board must not be named twice: {', '.join(duplicates)}",
                found=list(self.targets),
            )
        if len(set(self.formats)) != len(self.formats):
            raise ValueError("an export format must not be named twice")
        return self
