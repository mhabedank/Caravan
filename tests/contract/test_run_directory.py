"""One run directory per invocation, never overwritten."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.run.paths import RunDirectoryError, create_run_directory, file_digest
from tests.support import PILOT

FIXED = datetime(2026, 10, 22, 12, 0, 0, tzinfo=UTC)


def test_the_name_carries_the_time_and_the_manifest_digest(tmp_path) -> None:
    digest = file_digest(PILOT)
    run_dir = create_run_directory(tmp_path, digest, now=FIXED)
    assert run_dir.name == f"20261022T120000Z-{digest[:8]}"


def test_a_second_run_in_the_same_second_fails_rather_than_overwriting(tmp_path) -> None:
    digest = file_digest(PILOT)
    create_run_directory(tmp_path, digest, now=FIXED)
    with pytest.raises(RunDirectoryError, match="never overwrites"):
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
