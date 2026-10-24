"""Typed features end to end: the training part decides, and pinning only fixes an order (T018).

A run that leaves the label order and the vocabulary to the training part must form exactly the
samples and the split a run that pins them forms — pinning changes what the author writes, not
what the model is trained on — and its resolved manifest must carry what was fitted in place of the
``derived`` markers (features 006 FR-013, 008 FR-012).
"""

from __future__ import annotations

import json

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.manifest._yaml import read_mapping
from tests.support import (
    CONV1D_FIXTURE,
    FIXTURE_COLUMNS,
    FIXTURE_LABELS,
    PILOT_FIXTURE,
    PILOT_FIXTURE_PINNED,
)
from tests.train.conftest import latest_run


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
        "fitted": json.loads((run / "data" / "preprocessing.json").read_text(encoding="utf-8")),
    }


@pytest.fixture(scope="module")
def mlp_pair(tmp_path_factory):
    return (
        train(PILOT_FIXTURE, tmp_path_factory.mktemp("derived")),
        train(PILOT_FIXTURE_PINNED, tmp_path_factory.mktemp("pinned")),
    )


def test_the_run_fits_every_feature_on_the_training_part(mlp_pair) -> None:
    derived, _ = mlp_pair
    schema = derived["schema"]
    assert [feature["name"] for feature in schema["features"]] == list(FIXTURE_COLUMNS)
    assert schema["fitted_on"] == "train"
    assert schema["ignored_columns"] == []
    output = schema["output"]["fitted"]
    # Every class is equally frequent in the training part, so the order is by text (R7).
    assert output["labels"] == list(FIXTURE_LABELS)
    assert output["labels_source"] == "derived"
    can_id = derived["fitted"]["input_features"]["can_id"]
    assert can_id["text_codes"] is None and can_id["vocab"] == can_id["codes"]
    assert len(can_id["vocab"]) == 32  # most_common
    dlc = derived["fitted"]["input_features"]["dlc"]
    assert dlc["normalization"] == "zscore" and dlc["scale"] > 0


def test_the_resolved_manifest_of_the_run_carries_what_was_fitted(mlp_pair) -> None:
    derived, _ = mlp_pair
    resolved = derived["resolved"]
    assert resolved["output_features"][0]["preprocessing"]["vocab"] == list(FIXTURE_LABELS)
    can_id = resolved["input_features"][0]
    assert can_id["encoder"]["embedding_size"] == 4
    assert can_id["preprocessing"]["fitted"] == derived["fitted"]["input_features"]["can_id"]
    assert derived["report"]["data"]["features"][1]["fitted"]["shift"] == pytest.approx(
        derived["fitted"]["input_features"]["dlc"]["shift"]
    )


def test_the_samples_and_the_split_do_not_depend_on_what_is_pinned(mlp_pair) -> None:
    derived, pinned = mlp_pair
    keys = ("windows_kept", "windows_discarded_mixed", "records_dropped_remainder", "split")
    for key in keys:
        assert (
            derived["report"]["dataset_resolved"][key] == pinned["report"]["dataset_resolved"][key]
        ), key
    assert pinned["schema"]["output"]["fitted"]["labels"] == ["normal", "dos", "fuzzy", "replay"]
    assert pinned["fitted"]["input_features"]["can_id"]["vocab"] == [291, 608, 790, 1072]


def test_the_conv1d_template_forms_the_same_samples(mlp_pair, tmp_path) -> None:
    conv = train(CONV1D_FIXTURE, tmp_path / "conv1d")
    derived, _ = mlp_pair
    for key in ("windows_kept", "split"):
        assert conv["report"]["dataset_resolved"][key] == derived["report"]["dataset_resolved"][key]
