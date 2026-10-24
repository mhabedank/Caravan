"""Every key caravan/v0.2 moved is refused at its path with the key that replaces it (T003).

Feature 008, contracts/manifest.md, *Removed from caravan/v0.1*. A moved key gets its own message
rather than "unknown field" (feature 006, FR-001), so an author learns where it went. A manifest of
the previous form as a whole is refused with V-1 and the change note (constitution 4.0.0).
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from caravan.manifest._yaml import dump_mapping
from caravan.manifest.load import load_manifest
from caravan.manifest.version import CHANGE_NOTE
from tests.support import INVALID
from tests.unit.test_features_schema import BASE

#: Each v0.1 key, written into a v0.2 manifest, with the path it is refused at and the key named.
MOVED: list[tuple[str, Any, str, str]] = [
    (
        "inputs",
        {"inputs": [{"name": "frames", "kind": "series", "window": 16}]},
        "inputs",
        "input_features",
    ),
    (
        "outputs",
        {"outputs": [{"name": "attack", "kind": "class", "labels": ["a", "b"]}]},
        "outputs",
        "output_features",
    ),
    ("train", {"train": {"batch": 32, "seed": 1}}, "train", "trainer"),
    ("dataset.source", {"dataset": {"source": "data/"}}, "dataset.source", "dataset"),
    (
        "dataset.split",
        {"dataset": {"source": "data/", "split": {"train": 0.7}}},
        "dataset.split",
        "preprocessing.split",
    ),
    (
        "dataset.representative_samples",
        {"dataset": {"source": "data/", "representative_samples": 100}},
        "dataset.representative_samples",
        "export.representative_samples",
    ),
]


@pytest.mark.parametrize(("case", "addition", "path", "new_key"), MOVED, ids=[m[0] for m in MOVED])
def test_a_moved_key_is_refused_at_its_path_naming_the_new_one(
    tmp_path, case, addition, path, new_key
) -> None:
    document = copy.deepcopy(BASE)
    document.update(addition)
    target = tmp_path / "moved.yaml"
    target.write_text(dump_mapping(document), encoding="utf-8")
    outcome = load_manifest(target)
    assert not outcome.is_valid
    by_path = {finding.path: finding for finding in outcome.findings}
    assert path in by_path, [finding.as_dict() for finding in outcome.findings]
    problem = by_path[path].problem
    assert "caravan/v0.2" in problem
    assert new_key in problem
    assert "unknown field" not in problem


def test_a_moved_section_does_not_also_report_its_replacement_missing(tmp_path) -> None:
    document = copy.deepcopy(BASE)
    document["inputs"] = document.pop("input_features")
    target = tmp_path / "moved.yaml"
    target.write_text(dump_mapping(document), encoding="utf-8")
    paths = [finding.path for finding in load_manifest(target).findings]
    assert "inputs" in paths
    assert "input_features" not in paths


def test_the_previous_form_as_a_whole_is_refused_with_v_1_and_the_change_note() -> None:
    outcome = load_manifest(INVALID / "v-1-previous-version.yaml")
    (finding,) = outcome.findings
    assert finding.rule == "V-1"
    assert finding.found == "caravan/v0.1"
    assert CHANGE_NOTE in finding.problem
    assert "caravan/v0.2" in finding.problem
