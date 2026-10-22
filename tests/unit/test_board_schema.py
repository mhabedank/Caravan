"""Board-file rules E-1 and S-1.

They govern board descriptions, not manifests, so they cannot appear in the manifest fixture
library and would otherwise go untested (FR-024, FR-025).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from caravan.manifest._yaml import read_mapping
from caravan.targets.registry import default_registry
from caravan.targets.schema import BoardDescription
from tests.support import BOARDS


def _rule_of(exc: ValidationError) -> str:
    return exc.errors()[0]["type"]


def test_emulator_must_be_stated_not_omitted() -> None:
    data = read_mapping(BOARDS / "e-1-emulator-omitted.yaml")
    with pytest.raises(ValidationError) as caught:
        BoardDescription.model_validate(data)
    # The field is required, so omitting it is a missing field rather than a silent default.
    assert caught.value.errors()[0]["type"] == "missing"
    assert caught.value.errors()[0]["loc"] == ("emulator",)


def test_emulator_platform_must_exist() -> None:
    data = read_mapping(BOARDS / "e-1-platform-that-does-not-exist.yaml")
    with pytest.raises(ValidationError) as caught:
        BoardDescription.model_validate(data)
    assert _rule_of(caught.value) == "E-1"


def test_every_value_needs_a_citation() -> None:
    data = read_mapping(BOARDS / "s-1-source-missing.yaml")
    with pytest.raises(ValidationError) as caught:
        BoardDescription.model_validate(data)
    assert _rule_of(caught.value) == "S-1"
    assert "toolchain" in caught.value.errors()[0]["ctx"]["problem"]


def test_shipped_boards_all_validate() -> None:
    registry = default_registry()
    assert registry.identifiers == ("esp32", "s32k144", "stm32h743")


def test_shipped_boards_state_emulator_support_honestly() -> None:
    registry = default_registry()
    # The two boards Renode has no platform for say so, with the evidence in their sources.
    for name in ("s32k144", "esp32"):
        board = registry.get(name)
        assert board is not None
        assert board.emulator is None
        assert "2026-10-22" in board.sources["emulator"]
    stm32 = registry.get("stm32h743")
    assert stm32 is not None and stm32.emulator is not None
    assert stm32.emulator.platform == "stm32h743"
