"""One case per run rule: the data and a valid manifest disagreeing, and what is said about it.

Each case asserts that the message names **both** sides of the disagreement (SC-008), because a
rejection that names only one leaves the author guessing which of the two to change.

The bad data is written into a temporary directory rather than committed. FR-013 allows exactly
one dataset in this repository, and a library of broken ones would be a second, a third and a
fourth.
"""

from __future__ import annotations

import pytest

from caravan.cli.main import EXIT_RULE, main
from caravan.data.fingerprint import resolve_dataset
from caravan.data.reader import read_records
from caravan.manifest.errors import (
    RULE_DATASET_CELL,
    RULE_DATASET_COLUMNS,
    RULE_DATASET_HEADERS_DIFFER,
    RULE_DATASET_LABELS,
    RunRuleFailure,
)
from caravan.stages import data as data_stage
from tests.train.conftest import pure_windows, write_manifest, write_records

HEADER = "label,a,b"


def read(directory, labels=("normal", "attack")):
    """Read the data, then check it against a pinned label list, as a run does.

    Since feature 006 the reader returns the labels as the data spells them and the ``data`` stage
    holds them against the manifest (DS-5), so the two steps are taken together here.
    """
    dataset = resolve_dataset("data", directory)
    records = read_records(dataset)
    data_stage.derive_labels(records.labels, list(labels))
    return records


def test_ds_2_when_no_column_is_called_label(tmp_path) -> None:
    write_records(tmp_path / "data", ["class,a,b", "normal,1,2"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_COLUMNS
    # Both sides: what the file has, and what is required.
    assert "class" in str(finding.found)
    assert "label" in finding.accepted


def test_ds_2_when_there_is_no_feature_column(tmp_path) -> None:
    write_records(tmp_path / "data", ["label", "normal"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    assert error.value.finding.rule == RULE_DATASET_COLUMNS
    assert "feature" in error.value.finding.problem


def test_ds_2_when_two_columns_are_called_label(tmp_path) -> None:
    write_records(tmp_path / "data", ["label,a,label", "normal,1,attack"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    assert error.value.finding.rule == RULE_DATASET_COLUMNS


def test_ds_3_when_two_files_disagree_about_their_header(tmp_path) -> None:
    data = tmp_path / "data"
    write_records(data, [HEADER, "normal,1,2"], name="a.csv")
    write_records(data, ["label,a,c", "normal,1,2"], name="b.csv")
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_HEADERS_DIFFER
    # Both files are named, because either one of them could be the one that is wrong.
    assert "a.csv" in finding.problem and "b.csv" in finding.problem


def test_ds_4_when_a_cell_is_not_a_number(tmp_path) -> None:
    write_records(tmp_path / "data", [HEADER, "normal,1,2", "normal,oops,3"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_CELL
    # The file, the record and the column — all three, so the author can go straight to it.
    assert "records.csv" in finding.problem
    assert "record 2" in finding.problem
    assert "'a'" in finding.problem  # 'oops' sits in the first feature column


def test_ds_4_when_a_cell_is_empty(tmp_path) -> None:
    write_records(tmp_path / "data", [HEADER, "normal,1,"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    assert error.value.finding.rule == RULE_DATASET_CELL
    assert "empty" in error.value.finding.problem


def test_ds_4_when_a_record_has_too_many_values(tmp_path) -> None:
    # The case the fast reader cannot see on its own: with ``usecols`` it simply ignores the extra
    # field. Caught by counting delimiters, so an appended column is refused instead of dropped.
    write_records(tmp_path / "data", [HEADER, "normal,1,2", "attack,1,2,3"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_CELL
    assert "record 2" in finding.problem


def test_ds_4_when_a_record_has_too_few_values(tmp_path) -> None:
    write_records(tmp_path / "data", [HEADER, "normal,1,2", "attack,1"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    assert error.value.finding.rule == RULE_DATASET_CELL


def test_ds_5_when_the_data_has_a_label_the_manifest_does_not_declare(tmp_path) -> None:
    write_records(tmp_path / "data", [HEADER, "normal,1,2", "fuzzy,1,2", "attack,1,2"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_LABELS
    assert "fuzzy" in finding.problem
    assert finding.accepted == ("normal", "attack")


def test_ds_5_when_the_manifest_declares_a_label_the_data_never_shows(tmp_path) -> None:
    # The other direction, and just as much a disagreement: a model asked to predict a class it
    # will never see an example of cannot be stratified or scored on it.
    write_records(tmp_path / "data", [HEADER, "normal,1,2"])
    with pytest.raises(RunRuleFailure) as error:
        read(tmp_path)
    finding = error.value.finding
    assert finding.rule == RULE_DATASET_LABELS
    assert "attack" in finding.problem


def test_ds_6_through_the_command_line_names_the_path_and_the_window(tmp_path) -> None:
    # End to end, so the exit code and the message form are covered too: a run rule is exit 1,
    # the same as an invalid manifest, because in both cases a rule said no.
    write_records(tmp_path / "data", [HEADER, *[f"normal,{i},{i}" for i in range(3)]])
    manifest = write_manifest(tmp_path, window=64, labels="normal")
    # One label is not a valid manifest, so use two and let the window be the problem.
    manifest = write_manifest(tmp_path, window=64)
    write_records(
        tmp_path / "data",
        [HEADER, *[f"{'normal' if i % 2 else 'attack'},{i},{i}" for i in range(10)]],
    )
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
    assert code == EXIT_RULE


def test_a_dataset_that_matches_its_manifest_reads_cleanly(tmp_path) -> None:
    # The control case. Without it, every assertion above could be passing for the wrong reason.
    write_records(tmp_path / "data", [HEADER, *pure_windows(["normal", "attack"], 4, 2)])
    records = read(tmp_path)
    assert records.schema.feature_names == ("a", "b")
    assert records.schema.record_count == 16
