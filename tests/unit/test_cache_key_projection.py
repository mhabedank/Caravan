"""The test this feature turns on.

A cache that reuses a result it should not have is a silent incorrect answer: not a crash, not a
warning, a model that claims to come from a manifest it does not come from. So this does not check
a list of cases. It walks **every leaf of the pilot manifest**, changes it, and asserts that the
stage key moves if and only if that leaf is covered by the stage's declared read set.

A field added to the schema later cannot escape it, which is the property a list of cases cannot
have. Between them, this and the projection in ``stages.base`` are why FR-014, FR-015 and SC-005
hold by construction rather than by review.
"""

from __future__ import annotations

import copy
import re
from typing import Any

import pytest

from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import merge_derived, resolve
from caravan.stages.base import StageSpec, project
from caravan.stages.build import SPEC as BUILD
from caravan.stages.cache import cache_key
from caravan.stages.data import SPEC as DATA
from caravan.stages.export import SPEC as EXPORT
from caravan.stages.quantize import SPEC as QUANTIZE
from caravan.stages.train import SPEC as TRAIN
from tests.support import VALID

#: The new-form pilot (feature 006), with what the data stage derives merged in — the form every
#: stage after ``data`` actually reads.
PILOT = VALID / "picket-mlp-fixture.yaml"
FIXTURE_COLUMNS = ["can_id", "dlc", "b0", "b1", "b2"]

# Feature 003 adds one entry, and the walk below then covers the new stage entirely: every leaf of
# the pilot manifest is changed in turn and the key must move if and only if that leaf is in the
# stage's declared read set. A schema field added later cannot quietly enter or leave what
# re-quantizes.
STAGES = (DATA, BUILD, TRAIN, QUANTIZE, EXPORT)
DATASET_VERSION = "sha256:aaaa"


def resolved_pilot() -> dict[str, Any]:
    outcome = load_manifest(PILOT)
    assert outcome.manifest is not None
    resolved = resolve(outcome.manifest)
    return merge_derived(
        resolved,
        input_columns=FIXTURE_COLUMNS,
        labels=resolved["outputs"][0]["labels"],
    )


def leaf_paths(value: Any, prefix: str = "") -> list[str]:
    """Every path to a leaf in the resolved manifest: ``export.targets``, ``outputs[0].labels``.

    A list of mappings — the declarations — is walked into, entry by entry; a list of scalars is
    one leaf.
    """
    if isinstance(value, dict):
        out: list[str] = []
        for key, child in value.items():
            out.extend(leaf_paths(child, f"{prefix}.{key}" if prefix else str(key)))
        return out
    if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        out = []
        for index, child in enumerate(value):
            out.extend(leaf_paths(child, f"{prefix}[{index}]"))
        return out
    return [prefix]


_PART = re.compile(r"^(?P<key>[^\[]+)(?:\[(?P<index>\d+)\])?$")


def _parent_and_key(document: dict[str, Any], path: str) -> tuple[Any, str]:
    parts = path.split(".")
    current: Any = document
    for part in parts[:-1]:
        match = _PART.match(part)
        assert match is not None
        current = current[match["key"]]
        if match["index"] is not None:
            current = current[int(match["index"])]
    return current, parts[-1]


def set_at(document: dict[str, Any], path: str, value: Any) -> None:
    parent, key = _parent_and_key(document, path)
    parent[key] = value


def get_at(document: dict[str, Any], path: str) -> Any:
    parent, key = _parent_and_key(document, path)
    return parent[key]


def perturb(value: Any) -> Any:
    """A different value of a plausible shape. Only its difference matters here."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 0.125
    if isinstance(value, str):
        return value + "-changed"
    if isinstance(value, list):
        return [*value, "changed"] if value else ["changed"]
    if value is None:
        return 1
    raise AssertionError(f"no perturbation defined for {type(value)!r}")  # pragma: no cover


def key_for(spec: StageSpec, document: dict[str, Any], upstream: str | None = None) -> str:
    return cache_key(
        spec.name,
        project(document, spec),
        dataset_version=DATASET_VERSION if spec.reads_dataset else None,
        upstream_key=upstream,
    )


def covers(spec: StageSpec, leaf: str) -> bool:
    """Whether a declared read covers this leaf — the field itself, or a field inside it."""
    return any(leaf == read or leaf.startswith(f"{read}.") for read in spec.reads)


@pytest.mark.parametrize("spec", STAGES, ids=lambda spec: spec.name)
def test_the_key_moves_exactly_for_the_fields_the_stage_declares(spec: StageSpec) -> None:
    base = resolved_pilot()
    before = key_for(spec, base)

    for leaf in leaf_paths(base):
        document = resolved_pilot()
        original = get_at(document, leaf)
        set_at(document, leaf, perturb(original))
        after = key_for(spec, document)

        if covers(spec, leaf):
            assert after != before, (
                f"{spec.name}: changing {leaf} must change the key — it is in the declared "
                "read set, so the stage's result depends on it"
            )
        else:
            assert after == before, (
                f"{spec.name}: changing {leaf} must NOT change the key — the stage does not "
                "read it, so a change there cannot change its result (FR-015)"
            )


def test_the_walk_actually_covers_the_manifest() -> None:
    # A guard against the test above passing because it examined nothing.
    leaves = leaf_paths(resolved_pilot())
    assert len(leaves) > 25, leaves
    assert "outputs[0].accuracy_drop_max" in leaves
    assert "inputs[0].columns" in leaves
    assert "model.params.hidden" in leaves


@pytest.mark.parametrize("spec", STAGES, ids=lambda spec: spec.name)
def test_every_declared_read_exists_in_the_resolved_manifest(spec: StageSpec) -> None:
    # A declared field that does not exist would make the stage unrunnable, and the projection
    # raises for it — this says so at the first test rather than at the first run.
    project(resolved_pilot(), spec)


#: Whose *own* projection a change moves (feature 006, FR-031; data model, *Stages*). A stage
#: downstream of one of these re-runs as well, through its upstream key — the budget re-runs
#: ``export`` that way — but no stage *upstream* of the reader does. The walk above proves the
#: general property; this names the cases a person actually meets, so the reason survives a
#: refactor. Principle III: a change only a later stage reads must not invalidate an earlier one.
RERUNS = {
    "outputs[0].accuracy_drop_max": {"quantize"},
    "export.targets": {"export"},
    "model.name": {"export"},
    "model.version": {"export"},
    "outputs[0].labels": {"data", "build", "train", "quantize", "export"},
}


@pytest.mark.parametrize("leaf", sorted(RERUNS))
def test_a_change_reruns_exactly_the_stages_that_read_it(leaf: str) -> None:
    base = resolved_pilot()
    edited = resolved_pilot()
    set_at(edited, leaf, perturb(get_at(edited, leaf)))
    moved = {spec.name for spec in STAGES if key_for(spec, base) != key_for(spec, edited)}
    assert moved == RERUNS[leaf]


def test_a_budget_change_never_retrains() -> None:
    # The case analysis C1 of 2026-10-23 found: the budget sits inside outputs[0], and a stage
    # that read the declaration whole would rebuild and retrain when it changed.
    base = resolved_pilot()
    edited = resolved_pilot()
    set_at(edited, "outputs[0].accuracy_drop_max", 0.05)
    for spec in (DATA, BUILD, TRAIN):
        assert key_for(spec, base) == key_for(spec, edited), spec.name


def test_the_dataset_version_and_the_upstream_key_are_part_of_the_identity() -> None:
    base = resolved_pilot()
    inputs = project(base, TRAIN)
    first = cache_key("train", inputs, dataset_version="sha256:aaaa", upstream_key="sha256:1")
    other_data = cache_key("train", inputs, dataset_version="sha256:bbbb", upstream_key="sha256:1")
    other_build = cache_key("train", inputs, dataset_version="sha256:aaaa", upstream_key="sha256:2")
    assert first != other_data
    assert first != other_build


def test_the_tool_version_is_part_of_the_identity(monkeypatch) -> None:
    # On purpose (research R7): a different version of Caravan may build a different model from
    # the same manifest, and Principle III makes provenance part of the result.
    from caravan.stages import cache as cache_module

    inputs = project(resolved_pilot(), BUILD)
    before = cache_module.cache_key("build", inputs, dataset_version=DATASET_VERSION)
    monkeypatch.setattr(cache_module, "__version__", "99.0.0")
    after = cache_module.cache_key("build", inputs, dataset_version=DATASET_VERSION)
    assert before != after


def test_the_two_stages_never_share_a_key() -> None:
    base = resolved_pilot()
    assert key_for(BUILD, base) != key_for(TRAIN, base)


def test_the_split_column_reruns_the_data_stage_and_a_fraction_does_not() -> None:
    # Analysis finding A1 of feature 007: the data stage leaves the split column out of the
    # derived inputs, so the column is part of its key; it does not split, so a fraction is not.
    base = resolved_pilot()
    fixed = copy.deepcopy(base)
    fixed["dataset"]["split"] = {"column": "split"}
    assert key_for(DATA, fixed) != key_for(DATA, base)
    tighter = copy.deepcopy(base)
    tighter["dataset"]["split"]["train"] = 0.6
    tighter["dataset"]["split"]["val"] = 0.25
    assert key_for(DATA, tighter) == key_for(DATA, base)
    assert key_for(TRAIN, tighter) != key_for(TRAIN, base)
