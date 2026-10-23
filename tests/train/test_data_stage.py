"""The data stage derives what the data says, once (feature 006, FR-009 to FR-013).

Lives under ``tests/train`` because the reader imports numpy, which only the training extra brings.
"""

from __future__ import annotations

import json

import pytest

from caravan.data.fingerprint import resolve_dataset
from caravan.data.reader import read_records
from caravan.manifest.errors import (
    RULE_DATASET_LABELS,
    RULE_TOO_FEW_CLASSES,
    RULE_UNKNOWN_INPUT_COLUMN,
    RunRuleFailure,
)
from caravan.manifest.resolve import DERIVED
from caravan.stages import data as data_stage
from caravan.stages.base import StageContext, run_stage
from tests.support import FIXTURE_LABELS, FIXTURE_RECORDS, SYNTHETIC_DATASET
from tests.train.conftest import write_records

FIXTURE_COLUMNS = ["can_id", "dlc", "b0", "b1", "b2"]


def declared(columns=DERIVED, column="label", labels=DERIVED) -> dict:
    return {
        "inputs[0].kind": "series",
        "inputs[0].columns": columns,
        "outputs[0].kind": "class",
        "outputs[0].column": column,
        "outputs[0].labels": labels,
    }


def schema_of(directory, *, columns=None, column="label", labels=DERIVED) -> dict:
    dataset = resolve_dataset(str(directory), directory.parent)
    records = read_records(
        dataset, input_columns=None if columns is None else tuple(columns), output_column=column
    )
    return data_stage.describe(
        records, declared(DERIVED if columns is None else columns, column, labels)
    )


def test_labels_are_derived_and_sorted() -> None:
    schema = schema_of(SYNTHETIC_DATASET)
    assert schema["labels"] == list(FIXTURE_LABELS) == ["dos", "fuzzy", "normal", "replay"]
    assert schema["labels_source"] == "derived"
    assert schema["input_columns"] == FIXTURE_COLUMNS
    assert schema["columns_source"] == "derived"
    assert schema["ignored_columns"] == []
    assert schema["records"] == FIXTURE_RECORDS


def test_pinned_labels_keep_their_order() -> None:
    pinned = ["normal", "dos", "fuzzy", "replay"]
    schema = schema_of(SYNTHETIC_DATASET, labels=pinned)
    assert schema["labels"] == pinned
    assert schema["labels_source"] == "stated"


def test_a_pinned_list_missing_a_data_value_fails_naming_it() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        schema_of(SYNTHETIC_DATASET, labels=["normal", "dos", "fuzzy"])
    finding = caught.value.finding
    assert finding.rule == RULE_DATASET_LABELS
    assert finding.path == "outputs[0].labels"
    assert finding.found == ["replay"]


def test_a_pinned_list_naming_an_absent_value_fails_naming_it() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        schema_of(SYNTHETIC_DATASET, labels=["normal", "dos", "fuzzy", "replay", "spoof"])
    finding = caught.value.finding
    assert finding.rule == RULE_DATASET_LABELS
    assert "spoof" in finding.problem
    assert "spoof" in finding.accepted


def test_one_class_is_nothing_to_classify(tmp_path) -> None:
    write_records(tmp_path / "data", ["label,a", "normal,1", "normal,2"])
    with pytest.raises(RunRuleFailure) as caught:
        schema_of(tmp_path / "data")
    assert caught.value.finding.rule == RULE_TOO_FEW_CLASSES


def test_numeric_labels_sort_as_text(tmp_path) -> None:
    write_records(tmp_path / "data", ["label,a", "2,1", "10,2"])
    assert schema_of(tmp_path / "data")["labels"] == ["10", "2"]


def test_an_unknown_stated_column_fails_naming_the_columns_there_are() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        schema_of(SYNTHETIC_DATASET, columns=["can_id", "speed"])
    finding = caught.value.finding
    assert finding.rule == RULE_UNKNOWN_INPUT_COLUMN
    assert finding.found == ["speed"]
    assert set(finding.accepted) == set(FIXTURE_COLUMNS)


def test_stated_columns_keep_their_order_and_the_rest_is_visible() -> None:
    schema = schema_of(SYNTHETIC_DATASET, columns=["dlc", "can_id"])
    assert schema["input_columns"] == ["dlc", "can_id"]
    assert schema["columns_source"] == "stated"
    assert schema["ignored_columns"] == ["b0", "b1", "b2"]


def test_stated_columns_go_into_the_tensor_in_stated_order() -> None:
    dataset = resolve_dataset(str(SYNTHETIC_DATASET), SYNTHETIC_DATASET.parent)
    every = read_records(dataset)
    swapped = read_records(dataset, input_columns=("dlc", "can_id"))
    assert (swapped.features[:, 0] == every.features[:, 1]).all()
    assert (swapped.features[:, 1] == every.features[:, 0]).all()


def test_another_output_column_is_read(tmp_path) -> None:
    write_records(tmp_path / "data", ["kind,a,b", "x,1,2", "y,3,4"])
    schema = schema_of(tmp_path / "data", column="kind")
    assert schema["labels"] == ["x", "y"]
    assert schema["input_columns"] == ["a", "b"]


def test_a_reused_data_stage_reads_no_records(tmp_path) -> None:
    dataset = resolve_dataset(str(SYNTHETIC_DATASET), SYNTHETIC_DATASET.parent)
    resolved = {
        "inputs": [{"kind": "series", "columns": DERIVED}],
        "outputs": [{"kind": "class", "column": "label", "labels": DERIVED}],
    }
    cache = tmp_path / "cache"
    for attempt in ("first", "second"):
        run_dir = tmp_path / attempt
        run_dir.mkdir()
        context = StageContext(dataset=dataset, run_dir=run_dir)
        outcome = run_stage(
            data_stage.SPEC,
            data_stage.stage(context),
            resolved=resolved,
            run_dir=run_dir,
            cache_dir=cache,
            dataset_version=dataset.version,
        )
        if attempt == "second":
            assert outcome.outcome == "reused"
            assert context.records_if_read is None
        schema = json.loads((run_dir / data_stage.SCHEMA).read_text(encoding="utf-8"))
        assert schema["labels"] == list(FIXTURE_LABELS)
