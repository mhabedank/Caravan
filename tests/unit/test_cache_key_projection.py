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

from typing import Any

import pytest

from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import resolve
from caravan.stages.base import StageSpec, project
from caravan.stages.build import SPEC as BUILD
from caravan.stages.cache import cache_key
from caravan.stages.train import SPEC as TRAIN
from tests.support import PILOT

STAGES = (BUILD, TRAIN)
DATASET_VERSION = "sha256:aaaa"


def resolved_pilot() -> dict[str, Any]:
    outcome = load_manifest(PILOT)
    assert outcome.manifest is not None
    return resolve(outcome.manifest)


def leaf_paths(value: Any, prefix: str = "") -> list[str]:
    """Every dotted path to a non-mapping value in the resolved manifest."""
    if isinstance(value, dict):
        out: list[str] = []
        for key, child in value.items():
            out.extend(leaf_paths(child, f"{prefix}.{key}" if prefix else str(key)))
        return out
    return [prefix]


def set_at(document: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current: Any = document
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = value


def get_at(document: dict[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.split("."):
        current = current[part]
    return current


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
    assert "compliance.intended_use" in leaves
    assert "model.params.hidden" in leaves


@pytest.mark.parametrize("spec", STAGES, ids=lambda spec: spec.name)
def test_every_declared_read_exists_in_the_resolved_manifest(spec: StageSpec) -> None:
    # A declared field that does not exist would make the stage unrunnable, and the projection
    # raises for it — this says so at the first test rather than at the first run.
    project(resolved_pilot(), spec)


def test_editing_compliance_text_changes_no_stage_key() -> None:
    # FR-015 stated as the thing a person actually does: fixing a typo in the intended-use text
    # must never retrain. The walk above covers it; this names it, so the reason the test exists
    # survives a refactor.
    base = resolved_pilot()
    edited = resolved_pilot()
    set_at(edited, "compliance.intended_use", "a clearer sentence about the same thing")
    set_at(edited, "publish.hf_repo", "someone-else/picket-mlp")
    for spec in STAGES:
        assert key_for(spec, base) == key_for(spec, edited)


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
