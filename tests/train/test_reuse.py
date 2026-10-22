"""User story 3, end to end: what retrains and what does not.

The generic proof is ``tests/unit/test_cache_key_projection.py``, which walks every leaf of the
pilot manifest. This is the lived version: edit a manifest the way a person actually edits one,
run it again, and see what happened.
"""

from __future__ import annotations

import json

from caravan.cli.main import EXIT_OK, main
from caravan.stages.cache import OUTCOME_PRODUCED, OUTCOME_REUSED
from tests.train.conftest import latest_run, pure_windows, write_manifest, write_records

HEADER = "label,a,b"


def train(manifest, tmp_path):
    code = main(
        [
            "train",
            str(manifest),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == EXIT_OK
    report = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text(encoding="utf-8"))
    return {stage["name"]: stage["outcome"] for stage in report["stages"]}


def dataset_and_manifest(tmp_path, **overrides):
    write_records(tmp_path / "data", [HEADER, *pure_windows(["normal", "attack"], 4, 8)])
    return write_manifest(tmp_path, **overrides)


def edit(manifest, old: str, new: str) -> None:
    manifest.write_text(manifest.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def test_the_first_run_produces_and_the_second_reuses(tmp_path) -> None:
    manifest = dataset_and_manifest(tmp_path)
    assert train(manifest, tmp_path) == {"build": OUTCOME_PRODUCED, "train": OUTCOME_PRODUCED}
    assert train(manifest, tmp_path) == {"build": OUTCOME_REUSED, "train": OUTCOME_REUSED}


def test_editing_compliance_text_retrains_nothing(tmp_path) -> None:
    # SC-004, and the reason the cache exists at all: keeping compliance text current must never
    # cost a training run, or the honest habit becomes a reason to avoid touching the manifest.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    edit(manifest, "Exercises one run rule end to end", "Exercises one run rule, end to end")
    assert train(manifest, tmp_path) == {"build": OUTCOME_REUSED, "train": OUTCOME_REUSED}


def test_changing_a_template_parameter_rebuilds_and_retrains(tmp_path) -> None:
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    edit(manifest, "hidden: [4]", "hidden: [8]")
    assert train(manifest, tmp_path) == {"build": OUTCOME_PRODUCED, "train": OUTCOME_PRODUCED}


def test_changing_the_seed_rebuilds_and_retrains(tmp_path) -> None:
    # The seed is an input to *both* stages, which the plan had wrong: Keras draws the initial
    # weights when the model is constructed, so ``built.keras`` already contains them. Reusing a
    # built model across seeds would hand back weights the manifest did not ask for.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    edit(manifest, "epochs: 1", "epochs: 1\n  seed: 7")
    assert train(manifest, tmp_path) == {"build": OUTCOME_PRODUCED, "train": OUTCOME_PRODUCED}


def test_changing_a_training_setting_retrains_but_does_not_rebuild(tmp_path) -> None:
    # The interesting case: the learning rate is in the train stage's read set and not in the
    # build stage's, so exactly one of the two runs again.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    edit(manifest, "learning_rate: 0.001", "learning_rate: 0.002")
    assert train(manifest, tmp_path) == {"build": OUTCOME_REUSED, "train": OUTCOME_PRODUCED}


def test_changing_a_byte_of_the_dataset_rebuilds_and_retrains(tmp_path) -> None:
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    records = tmp_path / "data" / "records.csv"
    records.write_text(
        records.read_text(encoding="utf-8").replace("normal,0,0", "normal,1,0", 1),
        encoding="utf-8",
    )
    assert train(manifest, tmp_path) == {"build": OUTCOME_PRODUCED, "train": OUTCOME_PRODUCED}


def test_moving_the_dataset_without_changing_it_retrains_nothing(tmp_path) -> None:
    # ``dataset.source`` is in no stage's read set on purpose: the identity of a result depends on
    # the data, not on where the data sits.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)

    (tmp_path / "data").rename(tmp_path / "elsewhere")
    edit(manifest, "source: data", "source: elsewhere")
    assert train(manifest, tmp_path) == {"build": OUTCOME_REUSED, "train": OUTCOME_REUSED}


def test_a_reused_run_reports_the_same_numbers_as_the_run_that_produced_them(tmp_path) -> None:
    # The report is built from the stage's own artifact rather than from live objects, so reuse
    # cannot quietly drop the metrics or their provenance.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    first = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text(encoding="utf-8"))
    train(manifest, tmp_path)
    second = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text(encoding="utf-8"))

    assert first["metrics"] == second["metrics"]
    assert first["confusion_matrix"] == second["confusion_matrix"]
    assert first["dataset_resolved"] == second["dataset_resolved"]
    assert second["stages"][1]["outcome"] == OUTCOME_REUSED


def test_a_reused_result_names_the_run_that_produced_it(tmp_path) -> None:
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    first_run = latest_run(tmp_path / "runs").name
    train(manifest, tmp_path)
    report = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text(encoding="utf-8"))
    assert all(stage["produced_by_run"] == first_run for stage in report["stages"])
