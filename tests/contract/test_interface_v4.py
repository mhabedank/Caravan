"""Interface contract version 4 (feature 014, contracts/reports.md; FR-019).

The contract states how the training data was cut (``training_stride``) and what a window's
prediction means (``window_label``), and says beside the stride that a firmware may read with any
step: before version 4 the field was called ``stride`` and read as an instruction to the device.
"""

from __future__ import annotations

import json

from caravan.export.interface import CONTRACT_VERSION, TRAINING_STRIDE_NOTE, interface_document
from tests.unit.test_interface_emit import BINDINGS, FEATURES, MODEL, OUTPUT


def contract(**more) -> dict:
    return json.loads(interface_document(MODEL, BINDINGS, FEATURES, OUTPUT, 64, **more))


def test_the_version_is_four_and_stride_is_gone() -> None:
    parsed = contract()
    assert CONTRACT_VERSION == parsed["contract_version"] == 4
    assert "stride" not in parsed


def test_without_a_stated_stride_the_training_stride_is_the_window() -> None:
    assert contract()["training_stride"] == 64


def test_the_training_stride_and_its_note_travel_together() -> None:
    parsed = contract(training_stride=16, window_label="last")
    assert parsed["training_stride"] == 16
    assert parsed["training_stride_note"] == TRAINING_STRIDE_NOTE
    assert "any step" in TRAINING_STRIDE_NOTE
    assert parsed["window_label"] == "last"


def test_the_any_rule_is_carried_with_its_value() -> None:
    assert contract(window_label={"any": "dos"})["window_label"] == {"any": "dos"}
