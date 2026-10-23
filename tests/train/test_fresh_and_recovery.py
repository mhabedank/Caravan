"""`--fresh`, and what happens when the cache is damaged rather than absent."""

from __future__ import annotations

import json

from caravan.cli.main import EXIT_OK, main
from caravan.stages.cache import OUTCOME_PRODUCED, OUTCOME_REUSED
from tests.train.conftest import latest_run, pure_windows, write_manifest, write_records

HEADER = "label,a,b"


def train(manifest, tmp_path, *extra):
    code = main(
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
    assert code == EXIT_OK
    return json.loads((latest_run(tmp_path / "runs") / "report.json").read_text("utf-8"))


def prepare(tmp_path):
    write_records(tmp_path / "data", [HEADER, *pure_windows(["normal", "attack"], 4, 8)])
    return write_manifest(tmp_path)


def test_fresh_retrains_and_the_report_records_the_bypass(tmp_path) -> None:
    # FR-017. A cache bypass, not a gate being silenced — and the report says it happened, so a
    # result that cost a full training run is distinguishable from one that did not.
    manifest = prepare(tmp_path)
    train(manifest, tmp_path)
    report = train(manifest, tmp_path, "--fresh")

    assert [stage["outcome"] for stage in report["stages"]] == [OUTCOME_PRODUCED] * 4
    assert all(stage["fresh"] for stage in report["stages"])


def test_without_fresh_the_report_says_so_too(tmp_path) -> None:
    manifest = prepare(tmp_path)
    train(manifest, tmp_path)
    report = train(manifest, tmp_path)
    assert all(stage["fresh"] is False for stage in report["stages"])


def test_a_deleted_cached_artifact_causes_a_fresh_run_not_a_failure(tmp_path) -> None:
    # FR-018. A cache that failed the run because its own bookkeeping is damaged would be worse
    # than one that recomputes.
    manifest = prepare(tmp_path)
    train(manifest, tmp_path)
    for artifact in (tmp_path / "cache").rglob("trained.keras"):
        artifact.unlink()

    report = train(manifest, tmp_path)
    outcomes = {stage["name"]: stage["outcome"] for stage in report["stages"]}
    assert outcomes == {
        "data": OUTCOME_REUSED,
        "build": OUTCOME_REUSED,
        "fit": OUTCOME_REUSED,
        "train": OUTCOME_PRODUCED,
    }


def test_a_truncated_cache_record_is_a_miss_not_an_error(tmp_path) -> None:
    manifest = prepare(tmp_path)
    train(manifest, tmp_path)
    for record in (tmp_path / "cache" / "train").rglob("result.json"):
        record.write_text("{ not json", encoding="utf-8")

    report = train(manifest, tmp_path)
    outcomes = {stage["name"]: stage["outcome"] for stage in report["stages"]}
    assert outcomes["train"] == OUTCOME_PRODUCED


def test_fresh_leaves_the_cache_usable_for_the_next_run(tmp_path) -> None:
    manifest = prepare(tmp_path)
    train(manifest, tmp_path, "--fresh")
    report = train(manifest, tmp_path)
    assert [stage["outcome"] for stage in report["stages"]] == [OUTCOME_REUSED] * 4


def test_the_cache_directory_is_not_inside_the_run_directory(tmp_path) -> None:
    # A run directory is per invocation and complete on its own; the cache outlives it. Mixing
    # the two would make cleaning either one destroy the other.
    manifest = prepare(tmp_path)
    train(manifest, tmp_path)
    run_dir = latest_run(tmp_path / "runs")
    assert not (run_dir / "cache").exists()
    assert (tmp_path / "cache").is_dir()
