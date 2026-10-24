"""A run writes into its run directory and the cache, and nowhere else.

The manifest and the dataset are inputs and stay inputs — including their modification times, so
that a dataset's own fingerprint cannot be disturbed by the tool that read it.
"""

from __future__ import annotations

import hashlib
import shutil

from caravan.cli.main import EXIT_OK, main
from tests.support import SYNTHETIC_DATASET


def digest(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root) -> dict[str, tuple[str, int]]:
    return {
        str(path.relative_to(root)): (digest(path), path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_the_manifest_and_the_dataset_are_left_exactly_as_they_were(tmp_path) -> None:
    inputs = tmp_path / "inputs"
    data = inputs / "data"
    data.mkdir(parents=True)
    shutil.copy(SYNTHETIC_DATASET / "records.csv", data / "records.csv")
    manifest = inputs / "manifest.yaml"
    manifest.write_text(
        (SYNTHETIC_DATASET.parent.parent / "manifests" / "valid" / "picket-mlp-fixture.yaml")
        .read_text(encoding="utf-8")
        .replace("dataset: ../../datasets/synthetic", "dataset: data"),
        encoding="utf-8",
    )

    before = snapshot(inputs)
    assert (
        main(
            [
                "train",
                str(manifest),
                "--runs-dir",
                str(tmp_path / "runs"),
                "--cache-dir",
                str(tmp_path / "cache"),
            ]
        )
        == EXIT_OK
    )
    assert snapshot(inputs) == before


def test_only_the_runs_and_cache_directories_appear(tmp_path, monkeypatch) -> None:
    # Run from a directory of its own, so a default path that pointed somewhere unexpected would
    # show up here as a stray directory rather than inside somebody's repository.
    monkeypatch.chdir(tmp_path)
    inputs = tmp_path / "inputs"
    data = inputs / "data"
    data.mkdir(parents=True)
    shutil.copy(SYNTHETIC_DATASET / "records.csv", data / "records.csv")
    manifest = inputs / "manifest.yaml"
    manifest.write_text(
        (SYNTHETIC_DATASET.parent.parent / "manifests" / "valid" / "picket-mlp-fixture.yaml")
        .read_text(encoding="utf-8")
        .replace("dataset: ../../datasets/synthetic", "dataset: data"),
        encoding="utf-8",
    )

    main(["train", str(manifest)])

    created = sorted(path.name for path in tmp_path.iterdir())
    assert created == [".caravan", "inputs", "runs"]
