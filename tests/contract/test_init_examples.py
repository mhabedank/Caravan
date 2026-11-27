"""Every missing answer names one option and a value that works (feature 015, FR-015, SC-005).

For every item that can be missing, run ``--yes`` without it, take the option and the example from
the message, add exactly those, and check the message is gone. The one exception is the data when
nothing readable is in the current directory: the message then names a placeholder.
"""

from __future__ import annotations

import re
import shlex
import shutil
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, EXIT_USAGE, main

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
EDGES = DATA / "init"
MESSAGE = re.compile(
    r"caravan init: no (?P<label>.+?): .*; give it with (?P<option>\S+), for example"
)


def missing(err: str) -> dict[str, str]:
    """label → example, from the two lines each missing answer prints."""
    lines = err.splitlines()
    out = {}
    for number, line in enumerate(lines):
        found = MESSAGE.match(line)
        if found:
            example = lines[number + 1].strip()
            out[found["label"]] = re.sub(
                r" \((registered|columns|values|allowed|sizes): .*\)$", "", example
            )
    return out


def run(tmp_path, monkeypatch, capsys, *args: str) -> tuple[int, dict[str, str]]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("caravan.cli.init._terminal", lambda: False)
    code = main(["init", *args])
    return code, missing(capsys.readouterr().err)


@pytest.mark.parametrize(
    ("args", "label"),
    [
        (["--dataset", str(DATA / "synthetic")], "board"),
        (["--dataset", str(EDGES / "no-output.csv"), "--board", "esp32"], "output column"),
        (
            [
                "--dataset",
                str(EDGES / "ok-fault.csv"),
                "--output",
                "state",
                "--output-type",
                "anomaly",
                "--board",
                "esp32",
            ],
            "value that means normal",
        ),
        (["--dataset", str(DATA / "soc"), "--output", "soc", "--board", "esp32"], "budget"),
    ],
)
def test_the_named_example_gets_past_its_message(tmp_path, monkeypatch, capsys, args, label):
    args = [*args, "--yes"]
    code, named = run(tmp_path, monkeypatch, capsys, *args)
    assert code == EXIT_USAGE and label in named, named
    args += shlex.split(named[label])
    for _ in range(3):  # an answer can reveal the next open item; follow each named example
        code, named = run(tmp_path, monkeypatch, capsys, *args)
        assert label not in named
        if code == EXIT_OK:
            break
        assert named, "refused without naming what is missing"
        args += shlex.split(next(iter(named.values())))
    assert code == EXIT_OK


def test_the_data_example_comes_from_the_current_directory(tmp_path, monkeypatch, capsys):
    shutil.copytree(DATA / "synthetic", tmp_path / "mydata")
    code, named = run(tmp_path, monkeypatch, capsys, "--board", "esp32", "--yes")
    assert code == EXIT_USAGE and named == {"data": "--dataset mydata"}
    code, named = run(
        tmp_path, monkeypatch, capsys, "--board", "esp32", "--yes", "--dataset", "mydata"
    )
    assert code == EXIT_OK and not named


def test_without_data_in_reach_the_data_example_is_a_placeholder(tmp_path, monkeypatch, capsys):
    code, named = run(tmp_path, monkeypatch, capsys, "--board", "esp32", "--yes")
    assert code == EXIT_USAGE
    assert named == {"data": "--dataset '<directory of CSV files>'"}
