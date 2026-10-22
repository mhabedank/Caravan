"""Quickstart scenarios 1 and 2, plus the timing promise of SC-001."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, EXIT_RULE, main
from tests.support import MINIMAL, PILOT, invalid_cases


def run_cli(args: list[str]) -> int:
    return main(args)


def test_the_pilot_manifest_is_valid(tmp_path, capsys) -> None:
    code = run_cli(["validate", str(PILOT), "--runs-dir", str(tmp_path / "runs")])
    assert code == EXIT_OK

    report = json.loads(next((tmp_path / "runs").glob("*/report.json")).read_text())
    assert report["outcome"] == "valid"
    assert report["findings"] == []
    # Provenance Principle III names: both identifiers are fields of their own.
    assert report["dataset"] == "datasets/car-hacking/"
    assert report["template"] == "mlp"
    # A valid manifest is not a resolved dataset, and silence about a licence stays visible.
    kinds = {item["kind"] for item in report["unresolved"]}
    assert kinds == {"dataset-reference", "dataset-terms"}


@pytest.mark.parametrize(("name", "manifest", "expected"), invalid_cases())
def test_every_invalid_fixture_fires_its_own_rule(
    name: str, manifest: Path, expected: dict, tmp_path, capsys
) -> None:
    code = run_cli(["validate", str(manifest), "--json", "--runs-dir", str(tmp_path / name)])
    assert code == EXIT_RULE
    document = json.loads(capsys.readouterr().out)
    assert document["outcome"] == "invalid"
    first = document["findings"][0]
    assert first["path"] == expected["path"], name
    assert first.get("rule") == expected["rule"], name


def test_a_file_that_is_not_a_manifest_is_reported_as_what_it_is(tmp_path, capsys) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    assert run_cli(["validate", str(empty), "--no-report"]) == 2
    assert "the file is empty" in capsys.readouterr().err

    broken = tmp_path / "broken.yaml"
    broken.write_text("model: [unclosed\n", encoding="utf-8")
    assert run_cli(["validate", str(broken), "--no-report"]) == 2
    err = capsys.readouterr().err
    assert "not valid YAML" in err and "line" in err

    listish = tmp_path / "list.yaml"
    listish.write_text("- one\n- two\n", encoding="utf-8")
    assert run_cli(["validate", str(listish), "--no-report"]) == 2
    assert "must be a mapping" in capsys.readouterr().err


def test_line_endings_and_a_trailing_newline_do_not_change_the_verdict(tmp_path, capsys) -> None:
    original = MINIMAL.read_text(encoding="utf-8")
    variants = {
        "crlf.yaml": original.replace("\n", "\r\n"),
        "no-trailing-newline.yaml": original.rstrip("\n"),
        "extra-trailing-newlines.yaml": original + "\n\n",
    }
    for name, text in variants.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8", newline="")
        assert run_cli(["validate", str(path), "--no-report", "--quiet"]) == EXIT_OK, name


def test_a_verdict_arrives_in_under_two_seconds(tmp_path) -> None:
    # SC-001, measured rather than asserted. No network, no dataset present.
    start = time.monotonic()
    assert run_cli(["validate", str(PILOT), "--no-report", "--quiet"]) == EXIT_OK
    assert time.monotonic() - start < 2.0
