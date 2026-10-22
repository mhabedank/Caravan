"""One run directory per invocation, never overwritten."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.run.paths import (
    MAX_RUNS_PER_SECOND,
    RUN_DIR_PATTERN,
    RunDirectoryError,
    create_run_directory,
    file_digest,
)
from tests.support import PILOT

FIXED = datetime(2026, 10, 22, 12, 0, 0, tzinfo=UTC)


def test_the_name_carries_the_time_and_the_manifest_digest(tmp_path) -> None:
    digest = file_digest(PILOT)
    run_dir = create_run_directory(tmp_path, digest, now=FIXED)
    assert run_dir.name == f"20261022T120000Z-{digest[:8]}"


def test_a_second_run_in_the_same_second_gets_its_own_directory(tmp_path) -> None:
    # Changed by feature 002 from "fails rather than overwriting". The invariant was always that a
    # run never overwrites another's artifacts, and that still holds — what changed is that the
    # second run no longer *fails*. It had to: a fully reused run takes under a third of a second,
    # so running the same manifest twice in a row lands in one second routinely, and that is an
    # ordinary thing to do rather than an error. Caught by the `train` job on the first push.
    digest = file_digest(PILOT)
    first = create_run_directory(tmp_path, digest, now=FIXED)
    (first / "report.json").write_text("the first run's artifact", encoding="utf-8")

    second = create_run_directory(tmp_path, digest, now=FIXED)
    third = create_run_directory(tmp_path, digest, now=FIXED)

    assert second != first and third not in {first, second}
    assert second.name == f"{first.name}-2"
    assert third.name == f"{first.name}-3"
    # The point of the rule: nothing of the first run was touched.
    assert (first / "report.json").read_text(encoding="utf-8") == "the first run's artifact"
    assert not any(second.iterdir())


def test_a_same_second_directory_is_still_recognised_as_a_run_directory(tmp_path) -> None:
    # ``--runs-dir`` may not point inside a run directory, and the pattern that decides this has
    # to know the disambiguated form too, or the guard would have a gap exactly where runs are
    # most likely to pile up.
    digest = file_digest(PILOT)
    create_run_directory(tmp_path, digest, now=FIXED)
    second = create_run_directory(tmp_path, digest, now=FIXED)
    assert RUN_DIR_PATTERN.match(second.name)
    with pytest.raises(RunDirectoryError, match="inside an existing run directory"):
        create_run_directory(second / "nested", "0" * 64, now=FIXED)


def test_a_runaway_loop_is_refused_rather_than_renamed_forever(tmp_path) -> None:
    digest = file_digest(PILOT)
    for _ in range(MAX_RUNS_PER_SECOND):
        create_run_directory(tmp_path, digest, now=FIXED)
    with pytest.raises(RunDirectoryError, match="looks like a loop"):
        create_run_directory(tmp_path, digest, now=FIXED)


def test_a_runs_dir_inside_an_existing_run_directory_is_refused(tmp_path) -> None:
    run_dir = create_run_directory(tmp_path, file_digest(PILOT), now=FIXED)
    with pytest.raises(RunDirectoryError, match="inside an existing run directory"):
        create_run_directory(run_dir / "nested", "0" * 64, now=FIXED)


def test_nothing_outside_the_run_directory_is_created(tmp_path, capsys) -> None:
    runs = tmp_path / "runs"
    assert main(["render", str(PILOT), "--runs-dir", str(runs)]) == EXIT_OK
    assert [p.name for p in tmp_path.iterdir()] == ["runs"]
    run_dirs = list(runs.iterdir())
    assert len(run_dirs) == 1
    assert sorted(p.name for p in run_dirs[0].iterdir()) == [
        "report.json",
        "resolved-manifest.yaml",
    ]
