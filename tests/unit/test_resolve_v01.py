"""The resolved manifest of caravan/v0.1 (feature 006, contracts/manifest.md).

Every default expanded, nothing left implicit, key order from the schema — and the two values that
come from the data shown as ``derived`` until a run has read the data (FR-013).
"""

from __future__ import annotations

import copy

import pytest

from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import DERIVED, merge_derived, render, resolve
from tests.support import VALID

NEW_PILOT = VALID / "picket-mlp-v01.yaml"


@pytest.fixture
def pilot():
    outcome = load_manifest(NEW_PILOT)
    assert outcome.is_valid, outcome.findings
    return outcome.manifest


def test_key_order_follows_the_schema(pilot) -> None:
    assert list(resolve(pilot)) == [
        "apiVersion",
        "model",
        "inputs",
        "outputs",
        "dataset",
        "train",
        "export",
    ]
    assert list(resolve(pilot)["inputs"][0]) == ["name", "kind", "columns", "window"]
    assert list(resolve(pilot)["outputs"][0]) == [
        "name",
        "kind",
        "column",
        "labels",
        "accuracy_drop_max",
    ]


def test_what_the_data_will_say_is_marked_derived(pilot) -> None:
    resolved = resolve(pilot)
    assert resolved["inputs"][0]["columns"] == DERIVED == "derived"
    assert resolved["outputs"][0]["labels"] == DERIVED
    assert resolved["outputs"][0]["column"] == "label"


def test_stated_values_are_kept_as_written(pilot) -> None:
    pinned = pilot.model_copy(deep=True)
    pinned.outputs[0].labels = ["normal", "dos", "fuzzy", "replay"]
    pinned.inputs[0].columns = ["dlc", "can_id"]
    resolved = resolve(pinned)
    assert resolved["outputs"][0]["labels"] == ["normal", "dos", "fuzzy", "replay"]
    assert resolved["inputs"][0]["columns"] == ["dlc", "can_id"]


def test_no_removed_field_appears(pilot) -> None:
    text = render(pilot)
    for gone in ("compliance", "topic", "task", "permitted_use", "license", "verify:", "bench:"):
        assert gone not in text, gone
    assert "publish" not in text


def test_merge_replaces_exactly_the_two_derived_values(pilot) -> None:
    resolved = resolve(pilot)
    before = copy.deepcopy(resolved)
    merged = merge_derived(
        resolved, input_columns=["can_id", "dlc"], labels=["dos", "fuzzy", "normal", "replay"]
    )

    assert resolved == before  # the input is not mutated
    assert merged["inputs"][0]["columns"] == ["can_id", "dlc"]
    assert merged["outputs"][0]["labels"] == ["dos", "fuzzy", "normal", "replay"]
    merged["inputs"][0]["columns"] = DERIVED
    merged["outputs"][0]["labels"] = DERIVED
    assert merged == before


def test_rendering_is_byte_identical_across_calls(pilot) -> None:
    assert render(pilot) == render(pilot)
