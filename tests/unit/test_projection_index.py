"""A stage may read one field of a declaration, not the whole list (feature 006, FR-031).

Principle III: editing a field that only a later stage reads must not invalidate an earlier stage's
result. The budget lives inside ``outputs[0]``, so a stage that read ``outputs`` whole would rebuild
and retrain for a budget change. An index in a projection path is what lets it read less.
"""

from __future__ import annotations

import pytest

from caravan.stages.base import DeclarationError, StageSpec, project

RESOLVED = {
    "inputs": [{"name": "frames", "kind": "series", "columns": ["a", "b"], "window": 64}],
    "outputs": [
        {
            "name": "attack",
            "kind": "class",
            "column": "label",
            "labels": ["dos", "normal"],
            "accuracy_drop_max": 0.02,
        }
    ],
    "export": {"targets": ["esp32"]},
}


def spec(*reads: str) -> StageSpec:
    return StageSpec(name="probe", reads=reads, reads_dataset=False, upstream=None, artifacts=())


def test_an_indexed_path_resolves() -> None:
    inputs = project(RESOLVED, spec("outputs[0].labels", "inputs[0].window", "export.targets"))
    assert inputs == {
        "outputs[0].labels": ["dos", "normal"],
        "inputs[0].window": 64,
        "export.targets": ["esp32"],
    }


@pytest.mark.parametrize("path", ["outputs[1].labels", "outputs[0].colour", "inputs.window"])
def test_a_path_the_manifest_does_not_have_raises(path: str) -> None:
    with pytest.raises(DeclarationError):
        project(RESOLVED, spec(path))


def test_a_budget_change_leaves_a_field_by_field_projection_unchanged() -> None:
    changed = {
        **RESOLVED,
        "outputs": [{**RESOLVED["outputs"][0], "accuracy_drop_max": 0.10}],
    }
    reads = spec("inputs[0].columns", "outputs[0].name", "outputs[0].labels")
    assert project(RESOLVED, reads) == project(changed, reads)
    budget = spec("outputs[0].accuracy_drop_max")
    assert project(RESOLVED, budget) != project(changed, budget)
