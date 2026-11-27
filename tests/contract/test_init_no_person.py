"""``caravan init`` without a person never asks; ``--yes`` accepts (feature 015, User Story 2).

Spec FR-012 to FR-017, SC-004; contracts/cli-init.md, "Without a person". Standard input is an
object that fails the test if anything reads it.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, EXIT_USAGE, main

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
SYNTHETIC = str(DATA / "synthetic")
SHIPPED = ("synthetic", "anomaly", "recordings", "soc", "bursts", "frames")


class Untouchable:
    def readline(self, *args: object) -> str:
        raise AssertionError("init read standard input without a person")

    def isatty(self) -> bool:
        return False


def init(tmp_path, monkeypatch, *args: str, terminal: bool = False) -> int:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", Untouchable())
    monkeypatch.setattr("caravan.cli.init._terminal", lambda: terminal)
    return main(["init", *args])


def test_without_yes_nothing_is_written_and_the_accepting_command_is_named(
    tmp_path, monkeypatch, capsys
):
    assert init(tmp_path, monkeypatch, "--dataset", SYNTHETIC) == EXIT_USAGE
    err = capsys.readouterr().err
    assert not list(tmp_path.iterdir())
    assert "caravan init — proposal from" in err
    assert "nothing written: no one to ask, and --yes was not given" in err
    last = err.strip().splitlines()[-1]
    assert last.startswith("caravan init: to accept the proposal: caravan init")
    assert last.endswith("--board esp32 --yes")


def test_yes_writes_and_lists_the_uncertain_proposals_it_took(tmp_path, monkeypatch, capsys):
    code = init(tmp_path, monkeypatch, "--dataset", SYNTHETIC, "--board", "s32k144", "--yes")
    out, err = capsys.readouterr()
    assert code == EXIT_OK, err
    assert out == "synthetic-mlp.yaml\n"
    assert "took 2 uncertain proposals" in err
    assert "can_id as category (--input can_id=number to change)" in err
    assert "dlc as category (--input dlc=number to change)" in err


def test_yes_does_not_choose_a_board(tmp_path, monkeypatch, capsys):
    assert init(tmp_path, monkeypatch, "--dataset", SYNTHETIC, "--yes") == EXIT_USAGE
    err = capsys.readouterr().err
    assert "no board: Caravan does not choose the hardware" in err
    assert "--board esp32 (registered: esp32, s32k144, stm32h743)" in err
    assert not list(tmp_path.iterdir())


def test_yes_does_not_confirm_an_overwrite(tmp_path, monkeypatch, capsys):
    (tmp_path / "synthetic-mlp.yaml").write_text("keep\n")
    args = ["--dataset", SYNTHETIC, "--board", "esp32", "--yes"]
    assert init(tmp_path, monkeypatch, *args) == EXIT_USAGE
    assert "--overwrite" in capsys.readouterr().err
    assert (tmp_path / "synthetic-mlp.yaml").read_text() == "keep\n"


@pytest.mark.parametrize("flag", ["--yes", "--no-input"])
def test_in_a_terminal_yes_and_no_input_ask_nothing(tmp_path, monkeypatch, capsys, flag):
    code = init(
        tmp_path, monkeypatch, "--dataset", SYNTHETIC, "--board", "esp32", flag, terminal=True
    )
    assert code == (EXIT_OK if flag == "--yes" else EXIT_USAGE)


def test_a_board_a_bound_exceeds_is_noted_and_still_written(tmp_path, monkeypatch, capsys):
    # FR-006: the note comes before writing; the gate is build's fit check, not init.
    args = ["--dataset", SYNTHETIC, "--board", "s32k144", "--yes"]
    big = ["--template", "mlp", "--params", "{hidden: [4096, 4096]}"]
    assert init(tmp_path, monkeypatch, *args, *big) == EXIT_OK
    err = capsys.readouterr().err
    assert "note: s32k144: the flash lower bound already exceeds the board" in err
    assert err.index("note: s32k144") < err.index("wrote synthetic-mlp.yaml")


@pytest.mark.parametrize("name", SHIPPED)
def test_every_shipped_dataset_ends_within_five_seconds_without_a_person(
    tmp_path, monkeypatch, capsys, name
):
    # SC-004: no run waits for input.
    started = time.perf_counter()
    code = init(tmp_path, monkeypatch, "--dataset", str(DATA / name))
    assert code == EXIT_USAGE
    assert time.perf_counter() - started < 5
