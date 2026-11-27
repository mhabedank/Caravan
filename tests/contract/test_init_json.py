"""``caravan init --json``: one document per run, whatever the outcome (feature 015, User Story 3).

Spec FR-021 to FR-024, SC-006; contracts/init-result.md.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

from caravan.cli import main as cli
from caravan.cli.main import main
from caravan.init.memory import LABEL
from caravan.init.result import OUTCOMES
from caravan.init.session import Session

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
SYNTHETIC = str(DATA / "synthetic")
KEYS = ["outcome", "written", "dataset", "items", "memory", "findings", "notes", "next"]


class Untouchable:
    def readline(self, *args: object) -> str:
        raise AssertionError("init read standard input with --json")


def run(tmp_path, monkeypatch, capsys, *args: str, terminal: bool = False):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", Untouchable())
    monkeypatch.setattr("caravan.cli.init._terminal", lambda: terminal)
    code = main(["init", *args, "--json"])
    out, err = capsys.readouterr()
    return code, out, err


def test_the_outcomes_have_the_exit_codes_of_the_command_line() -> None:
    assert OUTCOMES == {
        "written": cli.EXIT_OK,
        "invalid": cli.EXIT_RULE,
        "unusable": cli.EXIT_RULE,
        "proposed": cli.EXIT_USAGE,
        "incomplete": cli.EXIT_USAGE,
        "refused": cli.EXIT_USAGE,
    }


def invalid_document(monkeypatch) -> None:
    # Every offered choice validates, so a refused manifest is made by hand: an unknown field.
    original = Session.document
    monkeypatch.setattr(Session, "document", lambda self: original(self) + "unknown: 1\n")


@pytest.mark.parametrize(
    ("outcome", "args"),
    [
        ("written", ["--dataset", SYNTHETIC, "--board", "esp32", "--yes"]),
        ("invalid", ["--dataset", SYNTHETIC, "--board", "esp32", "--yes"]),
        ("unusable", ["--dataset", str(DATA / "images"), "--board", "esp32", "--yes"]),
        ("proposed", ["--dataset", SYNTHETIC]),
        ("incomplete", ["--dataset", SYNTHETIC, "--yes"]),
        ("refused", ["--dataset", SYNTHETIC, "--template", "autoencoder"]),
    ],
)
def test_every_outcome_prints_one_document_and_nothing_else(
    tmp_path, monkeypatch, capsys, outcome, args
):
    if outcome == "invalid":
        invalid_document(monkeypatch)
    code, out, err = run(tmp_path, monkeypatch, capsys, *args)
    document = json.loads(out)
    assert list(document) == KEYS
    assert document["outcome"] == outcome
    assert code == OUTCOMES[outcome]
    assert err == ""
    assert out.endswith("}\n") and out.count("\n}\n") == 1
    if outcome == "written":
        assert document["written"] == ["synthetic-mlp.yaml"]
        assert document["next"] == "caravan build synthetic-mlp.yaml"
    else:
        assert document["written"] == []
    if outcome == "invalid":
        assert document["findings"] and all(
            "path" in f and "problem" in f for f in document["findings"]
        )
        assert not (tmp_path / "synthetic-mlp.yaml").exists()
    if outcome in ("refused", "unusable"):
        assert document["notes"] and document["notes"][0]["kind"] == outcome


def test_items_and_memory_follow_the_contract(tmp_path, monkeypatch, capsys):
    _, out, _ = run(tmp_path, monkeypatch, capsys, "--dataset", SYNTHETIC, "--board", "esp32")
    document = json.loads(out)
    assert document["dataset"] == {"path": SYNTHETIC, "rows_read": 5184, "complete": True}
    for item in document["items"]:
        assert item["source"] in ("given", "answered", "proposed")
        if item["source"] != "proposed":
            assert item["certainty"] is None
        else:
            assert item["certainty"] in ("certain", "uncertain", "convention", "open")
        assert item["option"] and item["example"], item  # FR-031
    assert [m["board"] for m in document["memory"]] == ["esp32"]
    assert document["memory"][0]["label"] == LABEL


def test_json_in_a_terminal_asks_nothing(tmp_path, monkeypatch, capsys):
    _, out, _ = run(tmp_path, monkeypatch, capsys, "--dataset", SYNTHETIC, terminal=True)
    assert json.loads(out)["outcome"] == "proposed"


def test_the_same_command_prints_the_same_bytes(tmp_path, monkeypatch, capsys):
    first = run(tmp_path, monkeypatch, capsys, "--dataset", SYNTHETIC)[1]
    assert run(tmp_path, monkeypatch, capsys, "--dataset", SYNTHETIC)[1] == first


def test_the_next_command_of_a_preview_writes_the_manifest(tmp_path, monkeypatch, capsys):
    # SC-006: a script that reads only the document can build the command that writes.
    _, out, _ = run(tmp_path, monkeypatch, capsys, "--dataset", SYNTHETIC)
    words = shlex.split(json.loads(out)["next"])
    assert words[:2] == ["caravan", "init"] and "--yes" in words and "--json" in words
    monkeypatch.setattr("sys.stdin", Untouchable())
    code = main(words[1:])
    document = json.loads(capsys.readouterr().out)
    assert (code, document["outcome"]) == (0, "written")
    assert (tmp_path / document["written"][0]).exists()
