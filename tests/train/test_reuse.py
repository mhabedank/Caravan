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
    assert train(manifest, tmp_path) == {
        "data": OUTCOME_PRODUCED,
        "build": OUTCOME_PRODUCED,
        "fit": OUTCOME_PRODUCED,
        "train": OUTCOME_PRODUCED,
    }
    assert train(manifest, tmp_path) == {
        "data": OUTCOME_REUSED,
        "build": OUTCOME_REUSED,
        "fit": OUTCOME_REUSED,
        "train": OUTCOME_REUSED,
    }


def test_changing_the_budget_retrains_nothing(tmp_path) -> None:
    # Principle III and feature 006 FR-031, the case analysis C1 found: the budget sits inside the
    # output's declaration, and only quantize reads it — so tightening it must never cost a
    # training run, or the honest habit becomes a reason to avoid touching the manifest.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    edit(manifest, "accuracy_drop_max: 0.02", "accuracy_drop_max: 0.05")
    assert train(manifest, tmp_path) == {
        "data": OUTCOME_REUSED,
        "build": OUTCOME_REUSED,
        "fit": OUTCOME_REUSED,
        "train": OUTCOME_REUSED,
    }


def test_changing_a_template_parameter_rebuilds_and_retrains(tmp_path) -> None:
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    edit(manifest, "hidden: [4]", "hidden: [8]")
    assert train(manifest, tmp_path) == {
        "data": OUTCOME_REUSED,
        "build": OUTCOME_PRODUCED,
        "fit": OUTCOME_PRODUCED,
        "train": OUTCOME_PRODUCED,
    }


def test_changing_the_seed_refits_rebuilds_and_retrains(tmp_path) -> None:
    # The seed is an input to every stage: Keras draws the initial weights when the model is
    # constructed, so ``built.keras`` already contains them; and since feature 008 the data stage
    # splits and fits on the training part, which the seed draws.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    edit(manifest, "export:", "random_seed: 7\nexport:")
    assert train(manifest, tmp_path) == {
        "data": OUTCOME_PRODUCED,
        "build": OUTCOME_PRODUCED,
        "fit": OUTCOME_PRODUCED,
        "train": OUTCOME_PRODUCED,
    }


def test_changing_a_training_setting_retrains_but_does_not_rebuild(tmp_path) -> None:
    # The interesting case: the learning rate is in the train stage's read set and not in the
    # build stage's, so exactly one of the two runs again.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    edit(manifest, "learning_rate: 0.001", "learning_rate: 0.002")
    assert train(manifest, tmp_path) == {
        "data": OUTCOME_REUSED,
        "build": OUTCOME_REUSED,
        "fit": OUTCOME_REUSED,
        "train": OUTCOME_PRODUCED,
    }


def test_changing_a_byte_of_the_dataset_rebuilds_and_retrains(tmp_path) -> None:
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)
    records = tmp_path / "data" / "records.csv"
    records.write_text(
        records.read_text(encoding="utf-8").replace("normal,0,0", "normal,1,0", 1),
        encoding="utf-8",
    )
    assert train(manifest, tmp_path) == {
        "data": OUTCOME_PRODUCED,
        "build": OUTCOME_PRODUCED,
        "fit": OUTCOME_PRODUCED,
        "train": OUTCOME_PRODUCED,
    }


def test_moving_the_dataset_without_changing_it_retrains_nothing(tmp_path) -> None:
    # ``dataset`` is in no stage's read set on purpose: the identity of a result depends on
    # the data, not on where the data sits.
    manifest = dataset_and_manifest(tmp_path)
    train(manifest, tmp_path)

    (tmp_path / "data").rename(tmp_path / "elsewhere")
    edit(manifest, "dataset: data", "dataset: elsewhere")
    assert train(manifest, tmp_path) == {
        "data": OUTCOME_REUSED,
        "build": OUTCOME_REUSED,
        "fit": OUTCOME_REUSED,
        "train": OUTCOME_REUSED,
    }


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


def test_three_runs_in_a_row_get_three_run_directories(tmp_path) -> None:
    """The regression the `train` job caught on its first push.

    A fully reused run takes under a third of a second, so consecutive runs of one manifest land
    in the same second — and the run directory name is only accurate to the second. The first two
    runs here are fast enough on most machines to collide, which used to fail with exit 3, "a
    defect in caravan itself". The deterministic version of this is in
    ``tests/contract/test_run_directory.py``, with a frozen clock; this one is the end-to-end
    shape of what a person actually does.
    """
    manifest = dataset_and_manifest(tmp_path)
    for _ in range(3):
        train(manifest, tmp_path)

    runs = sorted(path.name for path in (tmp_path / "runs").iterdir())
    assert len(runs) == 3, runs
    assert len(set(runs)) == 3
    # Each one is complete on its own, reused or not.
    for name in runs:
        assert ((tmp_path / "runs" / name) / "report.json").is_file()
        assert ((tmp_path / "runs" / name) / "model" / "trained.keras").is_file()
