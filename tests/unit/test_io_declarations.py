"""The input and output declarations, field by field (feature 006, data model).

The form of a name and the implemented kinds are manifest rules (CF-9, CF-10), because only the
manifest knows where a declaration sits; they are tested in ``test_manifest_v01.py``. Here: what a
declaration accepts on its own.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from caravan.manifest.schema.io import (
    DEFAULT_OUTPUT_COLUMN,
    InputDeclaration,
    OutputDeclaration,
    name_problem,
)


def test_a_minimal_input() -> None:
    declared = InputDeclaration(name="frames", kind="series")
    assert declared.columns is None
    assert declared.window is None


@pytest.mark.parametrize("columns", [[], ["a", "a"], ["a", " "]])
def test_input_columns_are_a_non_empty_list_of_distinct_names(columns: list[str]) -> None:
    with pytest.raises(ValidationError):
        InputDeclaration(name="frames", kind="series", columns=columns)


@pytest.mark.parametrize("window", [0, -3])
def test_a_window_is_positive(window: int) -> None:
    with pytest.raises(ValidationError):
        InputDeclaration(name="frames", kind="series", window=window)


def test_an_output_defaults_its_column_to_label() -> None:
    declared = OutputDeclaration(name="attack", kind="class", accuracy_drop_max=0.02)
    assert declared.column == DEFAULT_OUTPUT_COLUMN == "label"
    assert declared.labels is None


def test_an_output_must_state_its_budget() -> None:
    # Principle V: every manifest states its budgets. There is no default to fall back on (FR-029).
    with pytest.raises(ValidationError) as caught:
        OutputDeclaration(name="attack", kind="class")
    assert any(error["loc"] == ("accuracy_drop_max",) for error in caught.value.errors())


@pytest.mark.parametrize("budget", [-0.01, 1.01])
def test_the_budget_is_a_fraction(budget: float) -> None:
    with pytest.raises(ValidationError):
        OutputDeclaration(name="attack", kind="class", accuracy_drop_max=budget)


@pytest.mark.parametrize("labels", [["only"], ["a", "a"], ["a", ""]])
def test_pinned_labels_are_at_least_two_distinct_names(labels: list[str]) -> None:
    with pytest.raises(ValidationError):
        OutputDeclaration(name="attack", kind="class", labels=labels, accuracy_drop_max=0.02)


def test_pinned_labels_keep_their_order() -> None:
    declared = OutputDeclaration(
        name="attack", kind="class", labels=["normal", "dos"], accuracy_drop_max=0.02
    )
    assert declared.labels == ["normal", "dos"]


@pytest.mark.parametrize("model", [InputDeclaration, OutputDeclaration])
def test_unknown_fields_are_refused(model: type) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(
            {"name": "x", "kind": "series", "accuracy_drop_max": 0.1, "colour": "red"}
        )


@pytest.mark.parametrize("name", ["frames", "attack_type", "x", "a" * 32])
def test_acceptable_names(name: str) -> None:
    assert name_problem(name) is None


@pytest.mark.parametrize("name", ["Frames", "can-id", "1x", "_x", "a" * 33, ""])
def test_unacceptable_names(name: str) -> None:
    assert name_problem(name) is not None
