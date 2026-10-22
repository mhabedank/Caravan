"""The board description: declarative data, with a stated source for every value.

Principle VII names what a board description must carry — core, clock, memory, flash, accelerated
kernels, interfaces, toolchain and emulator support. ``toolchain`` is carried here even though no
stage in this feature reads it: the board files written now are the ones later stages will read,
and adding the field afterwards would mean migrating every file already shipped.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caravan.manifest.errors import RULE_EMULATOR_STATED, RULE_SOURCES_COVERAGE, rule_error

Accelerator = Literal["cmsis-nn", "esp-nn", "none"]
EmulatorBackend = Literal["renode"]
EmulatorStatus = Literal["supported", "experimental"]

#: Every one of these needs a citation in ``sources`` (rule S-1).
SOURCED_VALUES = ("clock_mhz", "ram_kb", "flash_kb", "accel", "toolchain", "emulator")

#: Platforms that exist in the named backend. A board description may not claim one that does
#: not (rule E-1); the list is data about Renode, checked on 2026-10-22.
KNOWN_RENODE_PLATFORMS = frozenset(
    {
        "stm32h743",
        "stm32h753",
        "stm32h747",
        "nucleo_h753zi",
        "nucleo_f767zi",
        "arduino_nano_33_ble",
        "nrf52840",
        "nxp-s32k388",
        "nxp-s32k388evb",
        "s32k118",
    }
)


class Toolchain(BaseModel):
    """How firmware for this board is built. A project decision, not a datasheet fact."""

    model_config = ConfigDict(extra="forbid")

    compiler: str = Field(min_length=1)
    optimization: str = Field(min_length=1)
    runtime: Literal["tflm"] = "tflm"


class EmulatorPlatform(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: EmulatorBackend
    platform: str = Field(min_length=1)
    status: EmulatorStatus = "supported"


class BoardDescription(BaseModel):
    """One target board, as data."""

    model_config = ConfigDict(extra="forbid")

    board: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    family: str = Field(min_length=1)
    core: str = Field(min_length=1)
    clock_mhz: float = Field(gt=0)
    ram_kb: float = Field(gt=0)
    flash_kb: float = Field(gt=0)
    accel: Accelerator
    interfaces: list[str] = Field(min_length=1)
    #: Required and nullable, so that "no emulator" is stated rather than omitted (rule E-1).
    toolchain: Toolchain
    emulator: EmulatorPlatform | None
    sources: dict[str, str]
    notes: str | None = None

    @model_validator(mode="after")
    def _emulator_platform_exists(self) -> BoardDescription:
        if self.emulator is None:
            return self
        if self.emulator.platform not in KNOWN_RENODE_PLATFORMS:
            rule_error(
                RULE_EMULATOR_STATED,
                f"{self.board}.emulator.platform",
                "a board description must not name an emulator platform that does not exist; "
                "state null instead",
                found=self.emulator.platform,
                accepted=tuple(sorted(KNOWN_RENODE_PLATFORMS)),
            )
        return self

    @model_validator(mode="after")
    def _every_value_has_a_source(self) -> BoardDescription:
        missing = [name for name in SOURCED_VALUES if not self.sources.get(name, "").strip()]
        if missing:
            rule_error(
                RULE_SOURCES_COVERAGE,
                f"{self.board}.sources",
                "every value must carry a citation a reader can check; missing: "
                + ", ".join(missing),
                accepted=SOURCED_VALUES,
            )
        return self
