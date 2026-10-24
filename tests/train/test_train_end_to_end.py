"""The acceptance criterion: the pilot manifest trains end to end on the committed fixture."""

from __future__ import annotations

import json
import time

from caravan.cli.main import EXIT_OK, main
from caravan.stages.build import BUILT_MODEL, BUILT_REPORT
from caravan.stages.train import (
    BEST_CHECKPOINT,
    FINAL_CHECKPOINT,
    HISTORY,
    METRICS,
    TRAINED_MODEL,
)
from tests.support import (
    FIXTURE_RECORDS,
    FIXTURE_WINDOWS_DISCARDED,
    FIXTURE_WINDOWS_KEPT,
)
from tests.train.conftest import latest_run

PROMISED = (
    BUILT_MODEL,
    BUILT_REPORT,
    TRAINED_MODEL,
    BEST_CHECKPOINT,
    FINAL_CHECKPOINT,
    METRICS,
    HISTORY,
    "report.json",
    "resolved-manifest.yaml",
)

#: SC-001's budget. Generous on purpose: it is a smoke test of the pipeline, and the figure that
#: matters is that it is seconds rather than minutes.
BUDGET_SECONDS = 60


def train(manifest, runs, cache, *extra):
    return main(
        ["train", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache), *extra]
    )


def test_the_pilot_manifest_trains_end_to_end_within_the_budget(
    fixture_manifest, workspace
) -> None:
    runs, cache = workspace
    started = time.perf_counter()
    assert train(fixture_manifest, runs, cache) == EXIT_OK
    elapsed = time.perf_counter() - started
    assert elapsed < BUDGET_SECONDS, f"{elapsed:.1f}s is over the {BUDGET_SECONDS}s budget"


def test_every_promised_artifact_is_there(fixture_manifest, workspace) -> None:
    # SC-002, as a list rather than a sample: an artifact nobody checks is an artifact that stops
    # being written one day without anyone noticing.
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    run_dir = latest_run(runs)
    missing = [name for name in PROMISED if not (run_dir / name).is_file()]
    assert not missing, f"missing artifacts: {missing}"


def test_the_report_states_what_the_windowing_kept_and_threw_away(
    fixture_manifest, workspace
) -> None:
    # The half of SC-010 the fixture test cannot cover: the counts have to reach the *report*,
    # because that is where a reader of the model's provenance looks.
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    dataset = report["dataset_resolved"]

    assert dataset["records"] == FIXTURE_RECORDS
    assert dataset["windows_kept"] == FIXTURE_WINDOWS_KEPT
    assert dataset["windows_discarded_mixed"] == FIXTURE_WINDOWS_DISCARDED
    assert dataset["records_dropped_remainder"] == 0
    assert sum(dataset["split"].values()) == FIXTURE_WINDOWS_KEPT


def test_the_report_records_every_effective_training_setting(fixture_manifest, workspace) -> None:
    # FR-008. The pilot manifest states five of the six; the record carries all six and says
    # which one it filled in itself.
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    training = report["training"]

    assert set(training["effective_settings"]) == {
        "epochs",
        "batch_size",
        "optimizer",
        "learning_rate",
        "early_stop",
        "random_seed",
    }
    assert training["settings_from_default"] == ["optimizer"]
    assert training["finished"] is True
    assert training["epochs_run"] >= 1


def test_the_history_covers_the_epochs_that_ran(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    train(fixture_manifest, runs, cache)
    run_dir = latest_run(runs)
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    history = json.loads((run_dir / HISTORY).read_text(encoding="utf-8"))
    assert len(history["loss"]) == report["training"]["epochs_run"]
    assert "val_loss" in history
