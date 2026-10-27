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
from caravan.manifest.resolve import merge_fitted, resolve
from caravan.stages.base import StageSpec, project, read_path
from caravan.stages.build import SPEC as BUILD
from caravan.stages.cache import cache_key
from caravan.stages.data import SPEC as DATA
from caravan.stages.export import SPEC as EXPORT
from caravan.stages.quantize import SPEC as QUANTIZE
from caravan.stages.train import SPEC as TRAIN
from tests.support import VALID, pilot_fitted

#: The typed pilot (feature 008), with what the data stage fits merged in — the form every stage
#: after ``data`` actually reads.
PILOT = VALID / "picket-mlp-fixture.yaml"

# Feature 003 adds one entry, and the walk below then covers the new stage entirely: every leaf of
# the pilot manifest is changed in turn and the key must move if and only if that leaf is in the
# stage's declared read set. A schema field added later cannot quietly enter or leave what
# re-quantizes.
STAGES = (DATA, BUILD, TRAIN, QUANTIZE, EXPORT)
DATASET_VERSION = "sha256:aaaa"


def declared_pilot() -> dict[str, Any]:
    """The pilot as the ``data`` stage sees it: declared, nothing fitted yet."""
    outcome = load_manifest(PILOT)
    assert outcome.manifest is not None
    return resolve(outcome.manifest)


def resolved_pilot() -> dict[str, Any]:
    return merge_fitted(declared_pilot(), pilot_fitted())


def document_for(spec: StageSpec) -> dict[str, Any]:
    """What a stage's key is computed from in a run: the declared form for ``data``, which fits,
    and the merged form for every stage after it (``cli/pipeline.py``)."""
    return declared_pilot() if spec is DATA else resolved_pilot()


def leaf_paths(value: Any, prefix: str = "") -> list[str]:
    """Every path to a leaf of the resolved manifest: ``export.targets``, ``model.params.hidden``.

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
    return any(covered_by(leaf, read_path(read)) for read in spec.reads)


def covered_by(leaf: str, read: str) -> bool:
    """The read is the leaf, or a field or a list the leaf sits inside."""
    return leaf == read or leaf.startswith(f"{read}.") or leaf.startswith(f"{read}[")


@pytest.mark.parametrize("spec", STAGES, ids=lambda spec: spec.name)
def test_the_key_moves_exactly_for_the_fields_the_stage_declares(spec: StageSpec) -> None:
    base = document_for(spec)
    before = key_for(spec, base)

    for leaf in leaf_paths(base):
        document = document_for(spec)
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
    assert len(leaves) > 40, leaves
    assert "output_features[0].accuracy_drop_max" in leaves
    assert "input_features[0].preprocessing.fitted.vocab" in leaves
    assert "input_features[1].preprocessing.fitted.shift" in leaves
    assert "model.params.hidden" in leaves


@pytest.mark.parametrize("spec", STAGES, ids=lambda spec: spec.name)
def test_every_declared_read_exists_in_the_resolved_manifest(spec: StageSpec) -> None:
    # A declared field that does not exist would make the stage unrunnable, and the projection
    # raises for it — this says so at the first test rather than at the first run.
    project(document_for(spec), spec)


#: Whose *own* projection a change moves (feature 006, FR-031; data model, *Stages*). A stage
#: downstream of one of these re-runs as well, through its upstream key — the budget re-runs
#: ``export`` that way — but no stage *upstream* of the reader does. The walk above proves the
#: general property; this names the cases a person actually meets, so the reason survives a
#: refactor. Principle III: a change only a later stage reads must not invalidate an earlier one.
RERUNS = {
    "output_features[0].accuracy_drop_max": {"quantize"},
    "export.targets": {"export"},
    "model.name": {"export"},
    "model.version": {"export"},
    "output_features[0].preprocessing.vocab": {"data", "build", "train", "quantize", "export"},
    # The seed draws the split, so the training part moves and with it every fitted value (T014).
    # The export reads it too since feature 009: its test windows are drawn from the same split.
    "random_seed": {"data", "build", "train", "quantize", "export"},
    # Read by the export alone, so changing how many windows a board gets re-runs nothing else.
    "export.test_windows": {"export"},
    "trainer.epochs": {"train"},
}


def moved_by(leaf: str, value: Any = None) -> set[str]:
    """The stages whose own key a change of this leaf moves, each on the document it reads."""
    moved = set()
    for spec in STAGES:
        base = document_for(spec)
        edited = document_for(spec)
        set_at(edited, leaf, perturb(get_at(edited, leaf)) if value is None else value)
        if key_for(spec, base) != key_for(spec, edited):
            moved.add(spec.name)
    return moved


@pytest.mark.parametrize("leaf", sorted(RERUNS))
def test_a_change_reruns_exactly_the_stages_that_read_it(leaf: str) -> None:
    assert moved_by(leaf) == RERUNS[leaf]


def test_a_budget_change_never_retrains() -> None:
    # The case analysis C1 of 2026-10-23 found: the budget sits inside the output, and a stage that
    # read the feature whole would rebuild and retrain when it changed.
    assert not moved_by("output_features[0].accuracy_drop_max", 0.05) & {"data", "build", "train"}


@pytest.mark.parametrize(
    "leaf",
    [
        "input_features[0].preprocessing.fitted.vocab",
        "input_features[1].preprocessing.fitted.shift",
        "output_features[0].preprocessing.fitted.labels",
    ],
)
def test_a_fitted_value_rebuilds_retrains_and_requantizes_but_never_refits(leaf: str) -> None:
    # FR-019, Principle III (feature 008, T014): the fitted values are constants of the model, so a
    # change of one — a vocabulary entry, a shift — changes what build, train and quantize produce.
    # The data stage's key is computed from the declared form, before anything is fitted, so it
    # never includes its own output.
    base = resolved_pilot()
    edited = resolved_pilot()
    set_at(edited, leaf, perturb(get_at(edited, leaf)))
    moved = {
        spec.name
        for spec in STAGES
        if spec is not DATA and key_for(spec, base) != key_for(spec, edited)
    }
    assert {"build", "train", "quantize"} <= moved
    assert "fitted" not in str(DATA.reads) and "fitted" not in str(project(declared_pilot(), DATA))


def test_a_number_budget_moves_only_quantize() -> None:
    # The budget of a number output is mae_increase_max; the same rule holds for it (T014).
    base = resolved_pilot()
    output = {
        "name": "label",
        "type": "number",
        "preprocessing": {"normalization": None, "fitted": {"normalization": None}},
        "loss": {"type": "mean_squared_error"},
        "clip": None,
        "mae_increase_max": 0.5,
    }
    base["output_features"][0] = output
    edited = copy.deepcopy(base)
    edited["output_features"][0]["mae_increase_max"] = 0.75
    moved = {spec.name for spec in STAGES if key_for(spec, base) != key_for(spec, edited)}
    assert moved == {"quantize"}


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


def test_the_split_reruns_the_data_stage() -> None:
    # Feature 008: the data stage splits and fits on the training part, so the split — its type,
    # its column, its probabilities — is part of its key, as it is of every stage that splits.
    base = resolved_pilot()
    fixed = copy.deepcopy(base)
    fixed["preprocessing"]["split"] = {"type": "fixed", "column": "split"}
    assert key_for(DATA, fixed) != key_for(DATA, base)
    tighter = copy.deepcopy(base)
    tighter["preprocessing"]["split"]["probabilities"] = [0.6, 0.25, 0.15]
    assert key_for(DATA, tighter) != key_for(DATA, base)
    assert key_for(TRAIN, tighter) != key_for(TRAIN, base)
    # The export reads the split too since feature 009, for its test windows.
    assert key_for(EXPORT, tighter) != key_for(EXPORT, base)
