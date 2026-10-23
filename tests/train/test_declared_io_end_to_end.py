"""User story 2 of feature 006, end to end: declare the input and the output, let the data talk.

A run that leaves the labels and the columns to the data must form exactly the samples and the
split a run that states them forms — the declarations change what the author writes, not what the
model is trained on (FR-016) — and its resolved manifest must carry what the data said in place of
the ``derived`` markers (FR-013).
"""

from __future__ import annotations

import json

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.manifest._yaml import read_mapping
from tests.support import CONV1D_FIXTURE, FIXTURE_LABELS, PILOT_FIXTURE, PILOT_FIXTURE_DERIVED
from tests.train.conftest import latest_run

FIXTURE_COLUMNS = ["can_id", "dlc", "b0", "b1", "b2"]


def train(manifest, root) -> dict:
    code = main(
        ["train", str(manifest), "--runs-dir", str(root / "runs"), "--cache-dir", str(root / "c")]
    )
    assert code == EXIT_OK
    run = latest_run(root / "runs")
    return {
        "run": run,
        "report": json.loads((run / "report.json").read_text(encoding="utf-8")),
        "resolved": read_mapping(run / "resolved-manifest.yaml"),
        "schema": json.loads((run / "data" / "schema.json").read_text(encoding="utf-8")),
    }


@pytest.fixture(scope="module")
def mlp_pair(tmp_path_factory):
    return (
        train(PILOT_FIXTURE_DERIVED, tmp_path_factory.mktemp("derived")),
        train(PILOT_FIXTURE, tmp_path_factory.mktemp("stated")),
    )


def test_the_run_derives_the_labels_and_the_columns(mlp_pair) -> None:
    new, _ = mlp_pair
    assert new["schema"]["labels"] == list(FIXTURE_LABELS)
    assert new["schema"]["labels_source"] == "derived"
    assert new["schema"]["input_columns"] == FIXTURE_COLUMNS
    assert new["schema"]["columns_source"] == "derived"


def test_the_resolved_manifest_of_the_run_carries_what_the_data_said(mlp_pair) -> None:
    new, _ = mlp_pair
    assert new["resolved"]["outputs"][0]["labels"] == list(FIXTURE_LABELS)
    assert new["resolved"]["inputs"][0]["columns"] == FIXTURE_COLUMNS
    assert new["report"]["data"]["labels"] == list(FIXTURE_LABELS)


def test_the_samples_and_the_split_do_not_depend_on_what_is_derived(mlp_pair) -> None:
    new, old = mlp_pair
    keys = ("windows_kept", "windows_discarded_mixed", "records_dropped_remainder", "split")
    for key in keys:
        assert new["report"]["dataset_resolved"][key] == old["report"]["dataset_resolved"][key], key


def test_the_conv1d_template_forms_the_same_samples(mlp_pair, tmp_path) -> None:
    new = train(CONV1D_FIXTURE, tmp_path / "conv1d")
    _, old = mlp_pair
    for key in ("windows_kept", "split"):
        assert new["report"]["dataset_resolved"][key] == old["report"]["dataset_resolved"][key]
