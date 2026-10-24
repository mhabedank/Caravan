"""A run whose data decides the split (feature 007, FR-017 to FR-019)."""

from __future__ import annotations

import json
import shutil

from caravan.cli.main import EXIT_OK, EXIT_RULE, main
from caravan.manifest.errors import RULE_SPLIT_VALUE
from tests.support import SPLIT_COUNTS, SPLIT_DISCARDED, VALID, write_split_dataset
from tests.train.conftest import latest_run

MANIFEST = VALID / "picket-mlp-fixed-split.yaml"


def run(tmp_path, verb: str = "train") -> int:
    return main(
        [
            verb,
            str(tmp_path / MANIFEST.name),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )


def prepare(tmp_path):
    shutil.copy(MANIFEST, tmp_path / MANIFEST.name)
    return write_split_dataset(tmp_path / "data")


def test_the_parts_come_from_the_column(tmp_path) -> None:
    prepare(tmp_path)
    assert run(tmp_path) == EXIT_OK
    report = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text())
    resolved = report["dataset_resolved"]
    assert resolved["split_source"] == "column:split"
    assert resolved["windows_discarded_mixed_split"] == SPLIT_DISCARDED
    assert resolved["split"] == SPLIT_COUNTS


def test_the_split_column_is_not_an_input(tmp_path) -> None:
    prepare(tmp_path)
    assert run(tmp_path, "build") == EXIT_OK
    schema = json.loads((latest_run(tmp_path / "runs") / "data" / "schema.json").read_text())
    assert "split" not in schema["input_columns"]
    assert "split" not in schema["ignored_columns"]
    assert schema["split_column"] == "split"


def test_an_unknown_part_stops_the_run_naming_where(tmp_path, capsys) -> None:
    data = prepare(tmp_path)
    records = data / "records.csv"
    lines = records.read_text().splitlines()
    lines[10] = lines[10].replace(",train,", ",holdout,", 1)
    records.write_text("\n".join(lines) + "\n")
    assert run(tmp_path, "build") == EXIT_RULE
    err = capsys.readouterr().err
    assert "records.csv" in err and "line 11" in err and "holdout" in err
    report = json.loads((latest_run(tmp_path / "runs") / "report.json").read_text())
    assert [finding["rule"] for finding in report["findings"]] == [RULE_SPLIT_VALUE]
