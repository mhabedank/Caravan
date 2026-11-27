"""The ``AGENTS.md`` beside the manifest (feature 015, User Story 4; contracts/agents-md.md).

Spec FR-025 to FR-029, constitution v4.5.0 Principle XII: written only when asked and only after
the manifest validates, never over an existing one, together with the manifest or not at all, and
naming nothing from the manifest but its file name.
"""

from __future__ import annotations

import io
import json
import os
import shlex
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_INTERNAL, EXIT_OK, build_parser, main
from caravan.init import guide

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
SYNTHETIC = str(DATA / "synthetic")
CONTRACT = (
    Path(__file__).resolve().parents[2] / "specs/015-init-one-proposal/contracts/agents-md.md"
)
YES = ["--dataset", SYNTHETIC, "--board", "esp32", "--yes"]


def init(tmp_path, monkeypatch, *args: str) -> int:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("caravan.cli.init._terminal", lambda: False)
    return main(["init", *args])


def test_the_text_is_the_contract_text() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")
    assert contract.split("````markdown\n", 1)[1].split("````", 1)[0] == guide.TEXT


def test_the_guide_is_written_beside_the_manifest(tmp_path, monkeypatch, capsys):
    assert init(tmp_path, monkeypatch, *YES, "--agents-md") == EXIT_OK
    err = capsys.readouterr().err
    assert "wrote AGENTS.md" in err
    assert (tmp_path / "AGENTS.md").read_text() == guide.render("synthetic-mlp.yaml")


def test_beside_a_manifest_in_a_subdirectory(tmp_path, monkeypatch, capsys):
    (tmp_path / "model").mkdir()
    assert init(tmp_path, monkeypatch, "model/m.yaml", *YES, "--agents-md") == EXIT_OK
    assert (tmp_path / "model" / "AGENTS.md").read_text() == guide.render("m.yaml")
    assert not (tmp_path / "AGENTS.md").exists()


@pytest.mark.parametrize("overwrite", [[], ["--overwrite"]])
def test_an_existing_guide_is_never_changed(tmp_path, monkeypatch, capsys, overwrite):
    (tmp_path / "AGENTS.md").write_text("# mine\n")
    (tmp_path / "synthetic-mlp.yaml").write_text("old\n") if overwrite else None
    assert init(tmp_path, monkeypatch, *YES, "--agents-md", *overwrite) == EXIT_OK
    assert "kept AGENTS.md: it exists, and init never changes it" in capsys.readouterr().err
    assert (tmp_path / "AGENTS.md").read_text() == "# mine\n"
    assert "apiVersion" in (tmp_path / "synthetic-mlp.yaml").read_text()


def test_the_kept_guide_is_a_note_in_the_document(tmp_path, monkeypatch, capsys):
    (tmp_path / "AGENTS.md").write_text("# mine\n")
    assert init(tmp_path, monkeypatch, *YES, "--agents-md", "--json") == EXIT_OK
    document = json.loads(capsys.readouterr().out)
    assert [note["kind"] for note in document["notes"]] == ["uncertain-taken"] * 2 + [
        "agents-md-kept"
    ]
    assert document["written"] == ["synthetic-mlp.yaml"]


def test_written_guides_are_listed_in_the_document(tmp_path, monkeypatch, capsys):
    assert init(tmp_path, monkeypatch, *YES, "--agents-md", "--json") == EXIT_OK
    document = json.loads(capsys.readouterr().out)
    assert document["written"] == ["synthetic-mlp.yaml", "AGENTS.md"]


def test_no_guide_unless_asked(tmp_path, monkeypatch, capsys):
    assert init(tmp_path, monkeypatch, *YES) == EXIT_OK
    assert sorted(p.name for p in tmp_path.iterdir()) == ["synthetic-mlp.yaml"]


def test_the_guide_is_the_same_bytes_and_names_only_the_file(tmp_path, monkeypatch, capsys):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    assert init(first, monkeypatch, "m.yaml", *YES, "--agents-md") == EXIT_OK
    other = ["m.yaml", "--dataset", str(DATA / "anomaly"), "--board", "s32k144", "--yes"]
    assert init(second, monkeypatch, *other, "--agents-md", "--name", "other-model") == EXIT_OK
    assert (first / "AGENTS.md").read_bytes() == (second / "AGENTS.md").read_bytes()
    assert "other-model" not in (second / "AGENTS.md").read_text()


def test_when_the_manifest_cannot_be_moved_neither_file_is_left(tmp_path, monkeypatch, capsys):
    real = os.replace

    def failing(source, target):
        if str(target).endswith(".yaml"):
            raise OSError("disk full")
        return real(source, target)

    monkeypatch.setattr("caravan.init.session.os.replace", failing)
    assert init(tmp_path, monkeypatch, *YES, "--agents-md") == EXIT_INTERNAL  # reported, no trace
    assert not list(tmp_path.iterdir())


def test_every_command_in_the_guide_parses() -> None:
    parser = build_parser()
    text = guide.render("m.yaml")
    commands = [part for part in text.split("`") if part.startswith("caravan ") and " " in part]
    assert len(commands) >= 3
    for command in commands:
        # "Then, in order: `caravan train`, … each with `m.yaml --json`".
        if "m.yaml" not in command:
            command += " m.yaml --json"
        parser.parse_args(shlex.split(command)[1:])


def test_the_line_mode_offers_the_guide_under_adjust(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("caravan.cli.init._terminal", lambda: True)
    monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(["", "a", "AGENTS.md", "2", ""]) + "\n"))
    assert main(["init", "--dataset", SYNTHETIC, "--board", "esp32"]) == EXIT_OK
    assert (tmp_path / "AGENTS.md").exists()
