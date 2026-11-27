"""One interface: the line mode (feature 015, User Story 5; spec FR-018 to FR-020, SC-010).

The full-screen interface and its ``authoring`` extra are gone; what they showed is under "adjust"
in the line mode; and nothing outside the change note still mentions them.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, main

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tests" / "fixtures" / "datasets"
SYNTHETIC = str(DATA / "synthetic")

#: research R9: the backticked and the spaced spellings today's pages used are caught too.
PATTERNS = re.compile(
    r"`?authoring`?\s+extra|\[authoring|authoring =|textual|full[-\s]screen|--plain", re.IGNORECASE
)
SEARCHED = ("src", "docs", "README.md", "pyproject.toml", ".github")
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".txt", ".html", ".css", ".js", ".json"}
CHANGE_NOTE = "docs/releases/0.1.0.md"


@pytest.mark.parametrize("option", ["--plain", "--tui"])
def test_the_removed_options_are_unknown(option: str) -> None:
    with pytest.raises(SystemExit) as stop:
        main(["init", option])
    assert stop.value.code == 2


def adjust(tmp_path, monkeypatch, capsys, item: str, answer: str = "") -> str:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("caravan.cli.init._terminal", lambda: True)
    answers = ["", "a", item, answer, ""]
    monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(answers) + "\n"))
    assert main(["init", "--dataset", SYNTHETIC, "--board", "esp32"]) == EXIT_OK
    err = capsys.readouterr().err
    return err[err.index("? Which item?") :]


def test_adjust_shows_the_drawing_for_the_template(tmp_path, monkeypatch, capsys):
    assert "— the network (mlp)" in adjust(tmp_path, monkeypatch, capsys, "template")


def test_adjust_shows_the_presets_and_the_form_for_the_parameters(tmp_path, monkeypatch, capsys):
    shown = adjust(tmp_path, monkeypatch, capsys, "params")
    assert "e) edit the values one by one" in shown and " 1) " in shown


def test_adjust_shows_the_memory_panel_for_the_quantization(tmp_path, monkeypatch, capsys):
    assert "— memory on your boards" in adjust(tmp_path, monkeypatch, capsys, "quantize")


def test_nothing_but_the_change_note_mentions_the_removed_interface() -> None:
    found = set()
    for name in SEARCHED:
        path = ROOT / name
        files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
        for file in files:
            if file.suffix not in TEXT_SUFFIXES or "__pycache__" in file.parts:
                continue
            if PATTERNS.search(file.read_text(encoding="utf-8", errors="replace")):
                found.add(str(file.relative_to(ROOT)))
    assert found == {CHANGE_NOTE}


def test_the_search_catches_the_spellings_the_pages_used() -> None:
    # Checked against the roadmap row and the install page as they read before feature 015.
    assert PATTERNS.search("full screen with the `authoring` extra")
    assert PATTERNS.search("With the `authoring`\nextra it opens")
    assert PATTERNS.search("it opens a full\nscreen interface")
    assert not PATTERNS.search("`init` is admitted as an authoring aid")
