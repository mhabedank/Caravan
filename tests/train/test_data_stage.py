"""The data stage: typed columns, windows, split, and preprocessing fitted on the training part.

Features 006 and 008. Lives under ``tests/train`` because the reader imports numpy, which only the
training extra brings.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from caravan.data.fingerprint import resolve_dataset
from caravan.data.reader import read_records
from caravan.manifest.errors import (
    RULE_CLASS_OUTSIDE_TRAIN,
    RULE_DATASET_LABELS,
    RULE_TOO_FEW_CLASSES,
    RULE_UNKNOWN_INPUT_COLUMN,
    RunRuleFailure,
)
from caravan.manifest.resolve import DERIVED
from caravan.stages import data as data_stage
from caravan.stages.base import StageContext, run_stage
from tests.support import FIXTURE_COLUMNS, FIXTURE_LABELS, FIXTURE_RECORDS, SYNTHETIC_DATASET
from tests.train.conftest import write_records

NUMBER = {"normalization": "zscore", "missing_value_strategy": "fill_with_const", "fill_value": 0.0}
CATEGORY = {
    "missing_value_strategy": "fill_with_const",
    "fill_value": "<UNK>",
    "most_common": 32,
    "vocab": DERIVED,
}
PILOT_FEATURES = [
    {"name": "can_id", "type": "category", "preprocessing": dict(CATEGORY)},
    *(
        {"name": name, "type": "number", "preprocessing": dict(NUMBER)}
        for name in FIXTURE_COLUMNS[1:]
    ),
]
STRATIFY = {"type": "stratify", "probabilities": [0.7, 0.15, 0.15], "column": "label"}


def inputs_for(features=None, *, output="label", labels=DERIVED, window=64, split=None) -> dict:
    return {
        "input_features": PILOT_FEATURES if features is None else features,
        "output_features[0].name": output,
        "output_features[0].type": "category",
        "output_features[0].preprocessing": {"vocab": labels},
        "preprocessing.window_size": window,
        "preprocessing.split": STRATIFY if split is None else split,
        "random_seed": 42,
    }


def run_on(directory, **kwargs) -> tuple[dict, dict]:
    inputs = inputs_for(**kwargs)
    dataset = resolve_dataset(str(directory), directory.parent)
    records = read_records(
        dataset,
        features=tuple((f["name"], f["type"]) for f in inputs["input_features"]),
        output=(inputs["output_features[0].name"], "category"),
    )
    return data_stage.run_data(records, inputs)


def test_labels_are_derived_by_frequency_and_every_feature_is_fitted() -> None:
    schema, fitted = run_on(SYNTHETIC_DATASET)
    # Every class has the same number of training windows, so the order falls to the text.
    assert fitted["output"]["labels"] == list(FIXTURE_LABELS)
    assert fitted["output"]["labels_source"] == "derived"
    assert list(fitted["input_features"]) == list(FIXTURE_COLUMNS)
    assert schema["ignored_columns"] == []
    assert schema["records"] == FIXTURE_RECORDS
    assert schema["fitted_on"] == "train"


def test_the_statistics_come_from_the_training_part_only() -> None:
    schema, fitted = run_on(SYNTHETIC_DATASET)
    train_mean = fitted["input_features"]["b0"]["shift"]
    dataset = resolve_dataset(str(SYNTHETIC_DATASET), SYNTHETIC_DATASET.parent)
    records = read_records(dataset, features=(("b0", "number"),))
    assert train_mean != pytest.approx(float(np.mean(records.columns["b0"])), abs=1e-9)
    assert schema["split"]["train"] > schema["split"]["test"]


def test_pinned_labels_keep_their_order() -> None:
    pinned = ["normal", "dos", "fuzzy", "replay"]
    _, fitted = run_on(SYNTHETIC_DATASET, labels=pinned)
    assert fitted["output"]["labels"] == pinned
    assert fitted["output"]["labels_source"] == "stated"


def test_a_pinned_list_missing_a_data_value_fails_naming_it() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        run_on(SYNTHETIC_DATASET, labels=["normal", "dos", "fuzzy"])
    finding = caught.value.finding
    assert finding.rule == RULE_DATASET_LABELS
    assert finding.path == "output_features[0].preprocessing.vocab"
    assert finding.found == ["replay"]


def test_a_pinned_list_naming_an_absent_value_fails_naming_it() -> None:
    with pytest.raises(RunRuleFailure) as caught:
        run_on(SYNTHETIC_DATASET, labels=["normal", "dos", "fuzzy", "replay", "spoof"])
    finding = caught.value.finding
    assert finding.rule == RULE_DATASET_LABELS
    assert "spoof" in finding.problem


def small(tmp_path, rows: list[str]):
    write_records(tmp_path / "data", rows)
    return tmp_path / "data"


def features_ab() -> list[dict]:
    return [{"name": "a", "type": "number", "preprocessing": dict(NUMBER)}]


def test_one_class_is_nothing_to_classify(tmp_path) -> None:
    data = small(tmp_path, ["label,a", *(f"normal,{i}" for i in range(8))])
    with pytest.raises(RunRuleFailure) as caught:
        run_on(data, features=features_ab(), window=1, split={**STRATIFY})
    assert caught.value.finding.rule == RULE_TOO_FEW_CLASSES


def test_a_class_only_outside_the_training_part_is_ds_14(tmp_path) -> None:
    # A fixed split can leave a class out of the training part; nothing could learn it.
    rows = ["label,split,a"]
    rows += [f"x,train,{i}" for i in range(4)] + [f"y,train,{i}" for i in range(4)]
    rows += ["x,validation,1", "y,validation,2", "z,test,3", "x,test,4"]
    data = small(tmp_path, rows)
    inputs = inputs_for(features_ab(), window=1, split={"type": "fixed", "column": "split"})
    dataset = resolve_dataset(str(data), data.parent)
    records = read_records(
        dataset, features=(("a", "number"),), output=("label", "category"), split_column="split"
    )
    with pytest.raises(RunRuleFailure) as caught:
        data_stage.run_data(records, inputs)
    assert caught.value.finding.rule == RULE_CLASS_OUTSIDE_TRAIN
    assert caught.value.finding.found == ["z"]


def test_an_unknown_column_fails_naming_the_columns_there_are() -> None:
    features = [{"name": "speed", "type": "number", "preprocessing": dict(NUMBER)}]
    with pytest.raises(RunRuleFailure) as caught:
        run_on(SYNTHETIC_DATASET, features=features)
    finding = caught.value.finding
    assert finding.rule == RULE_UNKNOWN_INPUT_COLUMN
    assert finding.path == "input_features[0].name"
    assert finding.found == "speed"
    assert set(finding.accepted) == set(FIXTURE_COLUMNS)


def test_a_column_no_feature_reads_is_visible_as_ignored() -> None:
    features = [{"name": "dlc", "type": "number", "preprocessing": dict(NUMBER)}]
    schema, _ = run_on(SYNTHETIC_DATASET, features=features)
    assert schema["ignored_columns"] == ["can_id", "b0", "b1", "b2"]


def test_a_text_category_gets_codes_and_an_empty_number_is_filled(tmp_path) -> None:
    rows = ["label,gear,speed"]
    for index in range(40):
        label = "a" if index % 2 else "b"
        gear = "park" if index % 3 else "drive"
        speed = "" if index == 5 else str(index)
        rows.append(f"{label},{gear},{speed}")
    data = small(tmp_path, rows)
    features = [
        {"name": "gear", "type": "category", "preprocessing": dict(CATEGORY)},
        {"name": "speed", "type": "number", "preprocessing": dict(NUMBER)},
    ]
    _, fitted = run_on(data, features=features, window=1)
    gear = fitted["input_features"]["gear"]
    assert set(gear["text_codes"]) == {"park", "drive"}
    assert fitted["input_features"]["speed"]["fill"] == 0.0


def test_a_reused_data_stage_reads_no_records(tmp_path) -> None:
    dataset = resolve_dataset(str(SYNTHETIC_DATASET), SYNTHETIC_DATASET.parent)
    resolved = {
        "input_features": PILOT_FEATURES,
        "output_features": [
            {"name": "label", "type": "category", "preprocessing": {"vocab": DERIVED}}
        ],
        "preprocessing": {"window_size": 64, "split": STRATIFY},
        "random_seed": 42,
    }
    cache = tmp_path / "cache"
    for attempt in ("first", "second"):
        run_dir = tmp_path / attempt
        run_dir.mkdir()
        context = StageContext(
            dataset=dataset,
            run_dir=run_dir,
            features=tuple((f["name"], f["type"]) for f in PILOT_FEATURES),
        )
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
        fitted = json.loads((run_dir / data_stage.PREPROCESSING).read_text(encoding="utf-8"))
        assert fitted["output"]["labels"] == list(FIXTURE_LABELS)
