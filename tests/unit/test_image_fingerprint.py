"""The dataset's identity covers the images a table names (feature 010, research R11).

Core: the fingerprint reads the tables with the standard library and hashes the files as bytes, so
the stage cache works without a framework. No image is decoded here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from caravan.data.fingerprint import resolve_dataset
from caravan.manifest.errors import RULE_DATASET_UNREADABLE, RunRuleFailure


def dataset(root: Path, names: list[str] | None = None) -> Path:
    data = root / "set"
    (data / "img").mkdir(parents=True)
    names = names if names is not None else ["img/a.png", "img/b.png"]
    for index, name in enumerate(names):
        target = data / name
        if "missing" not in name and target.parent == data / "img" and not target.exists():
            target.write_bytes(bytes([index]) * 16)
    rows = ["image,label", *(f"{name},x" for name in names)]
    (data / "labels.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return data


def test_the_named_images_are_part_of_the_dataset(tmp_path) -> None:
    dataset(tmp_path)
    files = resolve_dataset("set", tmp_path, image_columns=["image"])
    assert [path.name for path in files.images] == ["a.png", "b.png"]
    assert [path.name for path in files.files] == ["labels.csv"]


def test_changing_an_image_changes_the_version(tmp_path) -> None:
    # SC-015: the cache must not reuse a model trained on other pixels.
    data = dataset(tmp_path)
    before = resolve_dataset("set", tmp_path, image_columns=["image"]).version
    (data / "img" / "b.png").write_bytes(b"other pixels")
    assert resolve_dataset("set", tmp_path, image_columns=["image"]).version != before


def test_an_unchanged_dataset_keeps_its_version(tmp_path) -> None:
    dataset(tmp_path)
    first = resolve_dataset("set", tmp_path, image_columns=["image"]).version
    assert resolve_dataset("set", tmp_path, image_columns=["image"]).version == first


def test_without_an_image_input_the_images_are_not_read(tmp_path) -> None:
    data = dataset(tmp_path)
    before = resolve_dataset("set", tmp_path).version
    (data / "img" / "b.png").write_bytes(b"other pixels")
    assert resolve_dataset("set", tmp_path).version == before


def refusal(tmp_path, names: list[str]) -> RunRuleFailure:
    dataset(tmp_path, names)
    with pytest.raises(RunRuleFailure) as caught:
        resolve_dataset("set", tmp_path, image_columns=["image"])
    return caught.value


def test_a_missing_image_names_its_record_and_file(tmp_path) -> None:
    # SC-014: none dropped silently.
    finding = refusal(tmp_path, ["img/a.png", "img/missing.png"]).finding
    assert finding.rule == RULE_DATASET_UNREADABLE
    assert "labels.csv, record 2, column image" in finding.problem
    assert "img/missing.png does not exist" in finding.problem


def test_a_path_outside_the_dataset_is_refused(tmp_path) -> None:
    (tmp_path / "secret.png").write_bytes(b"x")
    finding = refusal(tmp_path, ["img/a.png", "../secret.png"]).finding
    assert finding.rule == RULE_DATASET_UNREADABLE
    assert "record 2" in finding.problem and "inside the dataset directory" in finding.problem
