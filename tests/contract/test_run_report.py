"""The run report's shape, and what determinism means for it (research R9)."""

from __future__ import annotations

import json
from pathlib import Path

from caravan.cli.main import main
from tests.support import INVALID, PILOT, PILOT_FIXTURE

EXPECTED_FIELDS = [
    "caravan_version",
    "command",
    "started_at",
    "manifest_path",
    "manifest_sha256",
    "dataset",
    "template",
    "schema_version",
    "outcome",
    "gates",
    "findings",
    "unresolved",
    "artifacts",
    "seed",
]


def report_of(runs_dir: Path) -> dict:
    return json.loads(next(runs_dir.glob("*/report.json")).read_text(encoding="utf-8"))


def test_the_report_carries_exactly_the_contract_fields_in_order(tmp_path, capsys) -> None:
    main(["render", str(PILOT), "--runs-dir", str(tmp_path)])
    report = report_of(tmp_path)
    assert list(report) == EXPECTED_FIELDS


def test_the_report_carries_the_declared_schema_version(tmp_path, capsys) -> None:
    main(["validate", str(PILOT_FIXTURE), "--runs-dir", str(tmp_path)])
    assert report_of(tmp_path)["schema_version"] == "caravan/v0.2"


def test_a_refused_version_is_recorded_as_written(tmp_path, capsys) -> None:
    main(["validate", str(INVALID / "v-1-previous-version.yaml"), "--runs-dir", str(tmp_path)])
    report = report_of(tmp_path)
    assert report["outcome"] == "invalid"
    assert report["schema_version"] == "caravan/v0.1"
    assert [finding["rule"] for finding in report["findings"]] == ["V-1"]


def test_artifact_paths_are_relative_to_the_run_directory(tmp_path, capsys) -> None:
    main(["render", str(PILOT), "--runs-dir", str(tmp_path)])
    report = report_of(tmp_path)
    assert report["artifacts"] == {"resolved_manifest": "resolved-manifest.yaml"}


def test_a_gate_that_was_never_reached_is_absent_not_passing(tmp_path, capsys) -> None:
    main(["validate", str(INVALID / "v-1-unknown-version.yaml"), "--runs-dir", str(tmp_path)])
    report = report_of(tmp_path)
    names = [gate["name"] for gate in report["gates"]]
    assert names == ["schema-version"]
    assert report["gates"][0]["result"] == "fail"
    assert "schema" not in names


def test_two_reports_of_one_input_differ_only_in_run_identity(tmp_path, capsys) -> None:
    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    main(["render", str(PILOT), "--runs-dir", str(first_dir)])
    main(["render", str(PILOT), "--runs-dir", str(second_dir)])

    first, second = report_of(first_dir), report_of(second_dir)
    volatile = {"started_at"}
    assert {k: v for k, v in first.items() if k not in volatile} == {
        k: v for k, v in second.items() if k not in volatile
    }


def test_a_failed_run_still_writes_a_report(tmp_path, capsys) -> None:
    main(["validate", str(INVALID / "cf-2-duplicate-target.yaml"), "--runs-dir", str(tmp_path)])
    report = report_of(tmp_path)
    assert report["outcome"] == "invalid"
    assert report["findings"][0]["rule"] == "CF-2"
    assert report["artifacts"] == {}
