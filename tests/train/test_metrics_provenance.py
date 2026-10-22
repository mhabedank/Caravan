"""A number that does not say what it was measured against is not a result (FR-007, SC-003).

The enforcement is structural: ``QualityMetric`` cannot be constructed without its split, its
dataset version and its sample count, so there is no path from a computation to a report that
could drop them even by accident. These tests check both the structure and the output.
"""

from __future__ import annotations

import json

import pytest

from caravan.cli.main import main
from caravan.run.report import IncompleteMetric, QualityMetric
from caravan.stages.train import METRICS
from tests.train.conftest import latest_run

EXPECTED_NAMES = {
    "accuracy",
    "precision_macro",
    "recall_macro",
    "f1_macro",
    "recall_per_class",
}


def train(manifest, runs, cache):
    return main(["train", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])


def test_every_metric_in_the_report_names_what_it_was_measured_against(
    fixture_manifest, workspace
) -> None:
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))

    assert report["metrics"], "a finished training run with no metrics is not a result"
    for metric in report["metrics"]:
        assert metric["split"] in {"val", "test"}
        assert metric["dataset_version"].startswith("sha256:")
        assert metric["samples"] > 0
    assert report["dataset_resolved"]["version"] == report["metrics"][0]["dataset_version"]


def test_the_documented_set_is_measured_on_both_splits(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    measured = json.loads((latest_run(runs) / METRICS).read_text(encoding="utf-8"))
    for split in ("val", "test"):
        names = {m["name"] for m in measured["metrics"] if m["split"] == split}
        assert names == EXPECTED_NAMES


def test_no_metric_is_measured_on_the_training_split(fixture_manifest, workspace) -> None:
    # FR-006a. A number from data the model fitted is not evidence, and reporting it beside the
    # others invites exactly the comparison it cannot support.
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    assert "train" not in {metric["split"] for metric in report["metrics"]}


def test_the_confusion_matrix_carries_its_split_and_dataset_version(
    fixture_manifest, workspace
) -> None:
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    matrix = report["confusion_matrix"]
    assert matrix["split"] == "test"
    assert matrix["dataset_version"].startswith("sha256:")
    assert len(matrix["rows"]) == len(matrix["labels"])
    # The matrix is over the test split, so its cells must sum to the test sample count.
    assert sum(sum(row) for row in matrix["rows"]) == report["dataset_resolved"]["split"]["test"]


def test_the_per_class_recall_names_every_declared_label(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    per_class = next(
        m for m in report["metrics"] if m["name"] == "recall_per_class" and m["split"] == "test"
    )
    assert set(per_class["value"]) == set(report["confusion_matrix"]["labels"])


@pytest.mark.parametrize(
    "missing",
    [
        {"split": "train"},
        {"split": ""},
        {"dataset_version": ""},
        {"samples": 0},
        {"name": ""},
    ],
)
def test_an_incomplete_metric_cannot_be_constructed(missing) -> None:
    # The mechanism behind SC-003, asserted directly: not a convention the writer follows, but a
    # value that cannot exist without its provenance.
    fields = {
        "name": "accuracy",
        "value": 0.5,
        "split": "test",
        "dataset_version": "sha256:abc",
        "samples": 10,
    }
    fields.update(missing)
    with pytest.raises(IncompleteMetric):
        QualityMetric(**fields)
