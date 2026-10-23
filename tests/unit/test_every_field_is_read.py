"""Principle I (constitution 3.0.0): every field of the manifest is read by a stage.

Walks every leaf of the resolved new-form pilot and asserts that some stage declares it reads that
leaf, or a field around it. Two fields are settled by the constitution itself rather than by a stage
function, each with its reason below. SC-001 rides along: the new form is the shorter one.
"""

from __future__ import annotations

from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import resolve
from caravan.stages.build import SPEC as BUILD
from caravan.stages.data import SPEC as DATA
from caravan.stages.export import SPEC as EXPORT
from caravan.stages.quantize import SPEC as QUANTIZE
from caravan.stages.train import SPEC as TRAIN
from tests.support import PILOT, PILOT_FIXTURE
from tests.unit.test_cache_key_projection import leaf_paths

STAGES = (DATA, BUILD, TRAIN, QUANTIZE, EXPORT)

#: Read, but not by a stage function — each with the reason the constitution gives.
SETTLED_BY_THE_CONSTITUTION = {
    # Principle IX: every manifest declares its schema version; the loader reads it.
    "apiVersion",
    # Names the data every stage with ``reads_dataset`` reads; the path is resolved by the pipeline,
    # because a result depends on the data and not on where the data sits.
    "dataset.source",
}


def non_blank_lines(path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    return sum(1 for line in lines if line.strip() and not line.lstrip().startswith("#"))


def test_every_leaf_is_read_by_a_stage() -> None:
    outcome = load_manifest(PILOT_FIXTURE)
    assert outcome.manifest is not None
    reads = {read for spec in STAGES for read in spec.reads}
    unread = [
        leaf
        for leaf in leaf_paths(resolve(outcome.manifest))
        if leaf not in SETTLED_BY_THE_CONSTITUTION
        and not any(leaf == read or leaf.startswith(f"{read}.") for read in reads)
    ]
    assert not unread, f"fields no stage reads (Principle I): {unread}"


#: Non-blank, non-comment lines of the pilot in the form before feature 006 (``caravan/v0``),
#: counted on that file at commit 64c5603. The form no longer loads, so the count is a constant.
PREVIOUS_FORM_LINES = 43


def test_the_new_pilot_is_a_fifth_shorter_than_the_old() -> None:
    # SC-001: at most 34 non-blank, non-comment lines against the previous form's 43.
    for pilot in (PILOT, PILOT_FIXTURE):
        assert non_blank_lines(pilot) <= 34 <= PREVIOUS_FORM_LINES * 0.8
