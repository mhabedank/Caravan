"""The export section.

Format identifiers are deliberately not vendor product names: a rename of a product would
otherwise become a schema migration (constitution amendment 8, research R8). ``flatbuffer`` is the
serialised model, ``c_array`` the C source form of it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caravan.manifest.errors import RULE_DUPLICATE_TARGETS, field_error, rule_error

Quantization = Literal["int8", "float16", "none"]
Format = Literal["flatbuffer", "c_array", "onnx"]


#: The documented floor for int8 calibration. Calibration data determines the quantized
#: activation ranges; too few or unrepresentative samples are a known cause of accuracy collapse,
#: so this is a schema requirement rather than a convention. More is better.
MINIMUM_REPRESENTATIVE_SAMPLES = 100

#: The most test windows an export hands a board (feature 009, data-model §1). Not a board limit:
#: 64 windows of the example are about 82 KB of raw inputs (64 x 64 x (4 + 4 x 4) bytes) against
#: the 4 MB of flash a common ESP32 module has. The bound keeps the header readable and the board
#: run short.
MAXIMUM_TEST_WINDOWS = 64


class ExportSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantization: Quantization = "int8"
    formats: list[Format] = Field(default_factory=lambda: ["flatbuffer", "c_array"])
    targets: list[str] = Field(min_length=1)
    #: How many training samples calibrate an int8 conversion (rule CF-4). It belongs to the
    #: quantization, so it lives here since caravan/v0.2.
    representative_samples: int | None = Field(default=None, gt=0)
    #: How many windows of the test part the export writes into ``model/test_windows.h``, with the
    #: host's int8 answers, for a board to run and compare against (feature 009). Default 0: the
    #: author's data enters an export set only when the author asks for it (Principle VI).
    test_windows: int = Field(default=0, ge=0, le=MAXIMUM_TEST_WINDOWS)

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
        if self.test_windows > 0 and "c_array" not in self.formats:
            # The header binds each window by the named positions of the C array's header, so
            # without the array there is nothing for it to bind to.
            field_error(
                "export.test_windows",
                (
                    f"test windows need the c_array format, and export.formats is "
                    f"{list(self.formats)}: add c_array to export.formats or set test_windows to 0"
                ),
                found=self.test_windows,
            )
        return self
