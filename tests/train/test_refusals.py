"""What a training run refuses, and what it leaves behind when it does: nothing.

Two refusals, from two different places: a dataset reference that does not resolve (DS-1), and a
run whose loss stops being a number (DS-10). Both are exit 1 — a rule said no — and neither leaves
a model behind. A third, DS-9, refused data the author had marked as not for training; it was
retired with the compliance layer in feature 006 (Principle VI).
"""

from __future__ import annotations

import json

from caravan.cli.main import EXIT_RULE, main
from caravan.manifest.errors import RULE_DATASET_UNREADABLE, RULE_TRAINING_DIVERGED
from caravan.stages.build import BUILT_MODEL
from caravan.stages.train import BEST_CHECKPOINT, TRAINED_MODEL
from tests.train.conftest import latest_run, pure_windows, write_manifest, write_records

HEADER = "label,a,b"


def train(manifest, tmp_path, *extra):
    return main(
        [
            "train",
            str(manifest),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
            *extra,
        ]
    )


def report_of(tmp_path) -> dict:
    run_dir = latest_run(tmp_path / "runs")
    return json.loads((run_dir / "report.json").read_text(encoding="utf-8"))


def rules_in(report: dict) -> set[str]:
    return {finding.get("rule") for finding in report["findings"]}


def test_ds_1_names_the_path_and_says_the_reference_did_not_resolve(tmp_path) -> None:
    manifest = write_manifest(tmp_path, source="data-that-is-not-there")

    assert train(manifest, tmp_path) == EXIT_RULE
    report = report_of(tmp_path)
    assert RULE_DATASET_UNREADABLE in rules_in(report)
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_DATASET_UNREADABLE)
    assert "data-that-is-not-there" in finding["problem"]
    # Not an internal error: the report says the run did not finish, and the exit code says a
    # rule said no.
    assert report["training"] == {"finished": False}


def test_ds_10_a_diverged_run_fails_and_leaves_no_model(tmp_path) -> None:
    # FR-012. A learning rate this size makes the loss leave the numbers within an epoch; what
    # matters is what is left behind afterwards, which is nothing.
    write_records(tmp_path / "data", [HEADER, *pure_windows(["normal", "attack"], 4, 8)])
    manifest = write_manifest(tmp_path, learning_rate=1e30, epochs=3)

    assert train(manifest, tmp_path) == EXIT_RULE
    report = report_of(tmp_path)
    assert RULE_TRAINING_DIVERGED in rules_in(report)
    assert report["training"] == {"finished": False}

    run_dir = latest_run(tmp_path / "runs")
    assert not (run_dir / TRAINED_MODEL).exists()
    assert not (run_dir / BEST_CHECKPOINT).exists()


def test_a_refused_run_still_writes_its_report_and_resolved_manifest(tmp_path) -> None:
    # A failed run is still a run: what it did and why it stopped is the record (FR-012). What it
    # must not leave is a model.
    write_records(tmp_path / "data", [HEADER, *pure_windows(["normal", "attack"], 4, 8)])
    manifest = write_manifest(tmp_path, learning_rate=1e30, epochs=2)
    train(manifest, tmp_path)

    run_dir = latest_run(tmp_path / "runs")
    assert (run_dir / "report.json").is_file()
    assert (run_dir / "resolved-manifest.yaml").is_file()

    # The *built* model is there, and belongs there: the build stage finished, its result is
    # valid, and the report says which stage produced what. FR-012 is about the trained model —
    # the artifact that would otherwise claim a training run happened.
    assert (run_dir / BUILT_MODEL).is_file()
    assert not (run_dir / TRAINED_MODEL).exists()
    assert not (run_dir / BEST_CHECKPOINT).exists()
    report = report_of(tmp_path)
    assert [stage["name"] for stage in report["stages"]] == ["data", "build"]


def test_nothing_is_cached_for_a_refused_run(tmp_path) -> None:
    # The stage writes into a private directory that is only published once it finishes, so a
    # refusal cannot leave an entry for a later run to find and trust.
    write_records(tmp_path / "data", [HEADER, *pure_windows(["normal", "attack"], 4, 8)])
    manifest = write_manifest(tmp_path, learning_rate=1e30, epochs=2)
    train(manifest, tmp_path)

    cache = tmp_path / "cache"
    entries = [path for path in cache.rglob("result.json") if "train" in str(path)]
    assert not entries, f"a diverged run left a cache entry: {entries}"
