"""The guide's example is the manifest the suite runs (feature 007, research R4).

``examples/picket-mlp.yaml`` exists so that someone with an installed package can try Caravan
without a checkout. It must not drift from the fixture the end-to-end tests run, or the guide would
promise something no test checks. They differ in one field only: where the data is, seen from each.
"""

from __future__ import annotations

from pathlib import Path

from caravan.manifest._yaml import read_mapping
from tests.support import PILOT_FIXTURE, SYNTHETIC_DATASET

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "picket-mlp.yaml"


def without_source(mapping: dict) -> dict:
    return {key: value for key, value in mapping.items() if key != "dataset"}


def test_the_example_is_the_fixture_apart_from_the_source() -> None:
    assert without_source(read_mapping(EXAMPLE)) == without_source(read_mapping(PILOT_FIXTURE))


def test_the_example_points_at_the_committed_dataset() -> None:
    source = read_mapping(EXAMPLE)["dataset"]
    assert (EXAMPLE.parent / source).resolve() == SYNTHETIC_DATASET.resolve()
