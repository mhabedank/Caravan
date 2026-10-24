"""The dataset version: what it is computed from, and what it refuses.

The cache decides whether to retrain by comparing these strings, so the two properties that matter
are that it moves when the bytes move and that it stands still when nothing but the metadata does.
A version derived from a modification time would get the second one wrong, which is why it is not.
"""

from __future__ import annotations

import os
import time

import pytest

from caravan.data.fingerprint import resolve_dataset
from caravan.manifest.errors import RULE_DATASET_UNREADABLE, RunRuleFailure
from tests.support import SYNTHETIC_DATASET


def test_the_committed_fixture_resolves_and_reports_its_size() -> None:
    files = resolve_dataset("synthetic", SYNTHETIC_DATASET.parent)
    assert files.relative_names == ("records.csv",)
    assert files.version.startswith("sha256:")
    assert files.total_bytes == (SYNTHETIC_DATASET / "records.csv").stat().st_size


def test_two_reads_of_the_same_data_give_the_same_version() -> None:
    first = resolve_dataset("synthetic", SYNTHETIC_DATASET.parent)
    second = resolve_dataset("synthetic", SYNTHETIC_DATASET.parent)
    assert first.version == second.version


def test_the_version_moves_when_a_byte_moves(tmp_path) -> None:
    data = tmp_path / "set"
    data.mkdir()
    (data / "a.csv").write_text("label,x\nnormal,1\n", encoding="utf-8")
    before = resolve_dataset("set", tmp_path).version

    (data / "a.csv").write_text("label,x\nnormal,2\n", encoding="utf-8")
    assert resolve_dataset("set", tmp_path).version != before


def test_the_version_stands_still_when_only_the_timestamp_moves(tmp_path) -> None:
    # The whole reason the version is a content hash. A modification time changes when a file is
    # touched, copied or checked out, none of which change the data.
    data = tmp_path / "set"
    data.mkdir()
    (data / "a.csv").write_text("label,x\nnormal,1\n", encoding="utf-8")
    before = resolve_dataset("set", tmp_path).version

    future = time.time() + 86_400
    os.utime(data / "a.csv", (future, future))
    assert resolve_dataset("set", tmp_path).version == before


def test_a_file_name_is_part_of_the_version(tmp_path) -> None:
    # Two datasets with the same bytes under different names are different datasets: the reader
    # reads a directory in sorted name order, so the names decide the sequence.
    first = tmp_path / "one"
    first.mkdir()
    (first / "a.csv").write_text("label,x\nnormal,1\n", encoding="utf-8")
    second = tmp_path / "two"
    second.mkdir()
    (second / "b.csv").write_text("label,x\nnormal,1\n", encoding="utf-8")

    assert resolve_dataset("one", tmp_path).version != resolve_dataset("two", tmp_path).version


def test_a_single_file_reference_resolves_to_that_file(tmp_path) -> None:
    (tmp_path / "only.csv").write_text("label,x\nnormal,1\n", encoding="utf-8")
    files = resolve_dataset("only.csv", tmp_path)
    assert files.relative_names == ("only.csv",)


def test_ds_1_when_the_path_does_not_exist(tmp_path) -> None:
    with pytest.raises(RunRuleFailure) as error:
        resolve_dataset("nowhere", tmp_path)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_UNREADABLE
    assert finding.path == "dataset"
    assert "nowhere" in finding.problem


def test_ds_1_when_the_directory_holds_no_data_file(tmp_path) -> None:
    (tmp_path / "set").mkdir()
    (tmp_path / "set" / "notes.md").write_text("not data", encoding="utf-8")
    with pytest.raises(RunRuleFailure) as error:
        resolve_dataset("set", tmp_path)
    assert error.value.finding.rule == RULE_DATASET_UNREADABLE
    assert ".csv" in error.value.finding.problem


def test_ds_1_when_the_directory_is_nested(tmp_path) -> None:
    # Refused rather than searched: a partially read dataset is a silently different dataset.
    data = tmp_path / "set"
    (data / "deeper").mkdir(parents=True)
    (data / "deeper" / "a.csv").write_text("label,x\nnormal,1\n", encoding="utf-8")
    with pytest.raises(RunRuleFailure) as error:
        resolve_dataset("set", tmp_path)
    assert error.value.finding.rule == RULE_DATASET_UNREADABLE
    assert "deeper" in str(error.value.finding.found)


def test_ds_1_when_a_file_cannot_be_read(tmp_path) -> None:
    data = tmp_path / "set"
    data.mkdir()
    unreadable = data / "a.csv"
    unreadable.write_text("label,x\nnormal,1\n", encoding="utf-8")
    unreadable.chmod(0o000)
    try:
        if os.access(unreadable, os.R_OK):  # pragma: no cover - running as root
            pytest.skip("this process can read a mode 000 file, so there is nothing to assert")
        with pytest.raises(RunRuleFailure) as error:
            resolve_dataset("set", tmp_path)
        assert error.value.finding.rule == RULE_DATASET_UNREADABLE
    finally:
        unreadable.chmod(0o644)
