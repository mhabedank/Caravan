"""Memory before building, through the floors ``build`` uses (feature 013, research R13)."""

from __future__ import annotations

import pytest

from caravan.init import drawing, memory
from caravan.targets.registry import default_registry as boards
from caravan.templates.registry import default_registry as templates

FEATURES = [
    memory.Feature("can_id", "category", 32),
    memory.Feature("dlc", "category", 8),
    memory.Feature("b0", "number"),
]


@pytest.mark.parametrize("identifier", templates().identifiers)
def test_every_starter_has_an_estimate_and_a_drawing(identifier) -> None:
    spec = templates().get(identifier)
    assert spec.starter is not None and spec.layers is not None
    kind = spec.output_types[0]
    window = spec.starter.window
    result = memory.estimate(
        FEATURES, window, spec, spec.starter.params, kind, 4, "int8", [boards().get("s32k144")]
    )
    assert result.flash.floor_bytes > 0 and result.ram.floor_bytes > 0
    assert not result.exceeds("s32k144")
    lines = drawing.draw(FEATURES, window, spec, spec.starter.params, kind, 4)
    assert lines[0].startswith("inputs") and lines[-1].startswith("answer")


def test_float32_costs_four_times_the_weights() -> None:
    spec = templates().get("mlp")
    board = [boards().get("s32k144")]
    small = memory.estimate(FEATURES, 16, spec, {"hidden": [32]}, "category", 4, "int8", board)
    large = memory.estimate(FEATURES, 16, spec, {"hidden": [32]}, "category", 4, "none", board)
    assert large.flash.floor_bytes > 3 * small.flash.floor_bytes


def test_a_model_too_large_for_a_board_is_marked() -> None:
    spec = templates().get("mlp")
    board = [boards().get("s32k144")]
    huge = memory.estimate(
        FEATURES, 128, spec, {"hidden": [4096, 4096]}, "category", 4, "int8", board
    )
    assert huge.exceeds("s32k144")
    assert any(line.endswith("✗") for line in memory.panel(huge, board))
    assert memory.LABEL in memory.panel(huge, board)[-1]


def test_a_wider_layer_shows_in_the_drawing_and_the_memory() -> None:
    spec = templates().get("mlp")
    board = [boards().get("esp32")]
    narrow = memory.estimate(FEATURES, 16, spec, {"hidden": [16]}, "category", 4, "int8", board)
    wide = memory.estimate(FEATURES, 16, spec, {"hidden": [64]}, "category", 4, "int8", board)
    assert wide.flash.floor_bytes > narrow.flash.floor_bytes
    assert any(
        "→ 64" in line for line in drawing.draw(FEATURES, 16, spec, {"hidden": [64]}, "category", 4)
    )
