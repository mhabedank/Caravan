"""``caravan init`` with a person: one proposal, the few questions it needs, one decision.

Feature 015, User Story 1 (spec FR-005 to FR-011, SC-001; contracts/cli-init.md). A person is
present when standard input and standard error are terminals; these tests replace that check and
feed the answers on standard input, counting how many are read.
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

from caravan.cli.main import EXIT_OK, EXIT_USAGE, main
from caravan.init.memory import SHORT_LABEL
from caravan.manifest.load import load_manifest

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
SYNTHETIC = str(DATA / "synthetic")
ANOMALY = str(DATA / "anomaly")


class Answers(io.StringIO):
    """Standard input that counts the answers read."""

    def __init__(self, answers: list[str]) -> None:
        super().__init__("".join(f"{answer}\n" for answer in answers))
        self.reads = 0

    def readline(self, *args: object) -> str:  # type: ignore[override]
        line = super().readline(*args)  # type: ignore[arg-type]
        if line:
            self.reads += 1
        return line


def init(tmp_path, monkeypatch, *args: str, answers: list[str]) -> tuple[int, Answers]:
    monkeypatch.chdir(tmp_path)
    stdin = Answers(answers)
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("caravan.cli.init._terminal", lambda: True)
    return main(["init", *args]), stdin


def test_four_answers_write_a_valid_manifest_on_the_synthetic_data(tmp_path, monkeypatch, capsys):
    # SC-001: the data, the board (2 = s32k144), Enter for the uncertain columns, Enter to write.
    code, stdin = init(tmp_path, monkeypatch, answers=[SYNTHETIC, "2", "", ""])
    out, err = capsys.readouterr()
    assert code == EXIT_OK, err[-3000:]
    assert stdin.reads == 4
    assert out == "synthetic-mlp.yaml\n"
    outcome = load_manifest(tmp_path / "synthetic-mlp.yaml")
    assert outcome.manifest is not None, outcome.findings
    assert "targets: [s32k144]" in (tmp_path / "synthetic-mlp.yaml").read_text()


def test_the_proposal_comes_before_the_boards_and_the_columns_step_is_targeted(
    tmp_path, monkeypatch, capsys
):
    code, _ = init(tmp_path, monkeypatch, answers=[SYNTHETIC, "2", "", ""])
    err = capsys.readouterr().err
    assert code == EXIT_OK
    assert err.index("caravan init — proposal from") < err.index("Which boards")
    step = err[err.index("could be read more than one way") :]
    step = step[: step.index("Enter to accept as shown")]
    named = {line.split()[0] for line in step.splitlines()[1:] if line.strip()}
    assert named == {"can_id", "dlc"}


def test_the_board_question_shows_the_model_bounds_with_their_label(tmp_path, monkeypatch, capsys):
    init(tmp_path, monkeypatch, answers=[SYNTHETIC, "2", "", ""])
    err = capsys.readouterr().err
    boards = err[err.index("Which boards") : err.index("choose one or more")]
    assert boards.count("model ≥") == 3
    assert SHORT_LABEL in boards
    second = err[err.index("choose one or more") :]
    assert "memory" in second and "s32k144" in second and SHORT_LABEL in second


def test_adjust_one_item_then_write(tmp_path, monkeypatch, capsys):
    answers = [SYNTHETIC, "2", "", "a", "window", "8", ""]
    code, _ = init(tmp_path, monkeypatch, answers=answers)
    err = capsys.readouterr().err
    assert code == EXIT_OK, err[-3000:]
    assert "what your data allows" in err  # the window table of feature 013
    last = err[err.rindex("caravan init — proposal from") :]
    window = next(line for line in last.splitlines() if line.lstrip().startswith("window"))
    assert "8 rows" in window and "answered" in window
    assert "window_size: 8" in (tmp_path / "synthetic-mlp.yaml").read_text()


def test_stop_and_end_of_input_write_nothing(tmp_path, monkeypatch, capsys):
    code, _ = init(tmp_path, monkeypatch, answers=[SYNTHETIC, "2", "", "q"])
    assert code == EXIT_USAGE
    assert "nothing was written" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())
    code, _ = init(tmp_path, monkeypatch, answers=[SYNTHETIC, "2"])
    assert code == EXIT_USAGE
    assert not list(tmp_path.iterdir())


def test_going_back_keeps_the_answer_and_asks_it_again(tmp_path, monkeypatch, capsys):
    # The boards (s32k144), then back from the columns step, Enter keeps s32k144.
    answers = [SYNTHETIC, "2", "<", "", "", ""]
    code, _ = init(tmp_path, monkeypatch, answers=answers)
    assert code == EXIT_OK, capsys.readouterr().err[-3000:]
    assert "targets: [s32k144]" in (tmp_path / "synthetic-mlp.yaml").read_text()


def test_data_in_the_current_directory_is_offered(tmp_path, monkeypatch, capsys):
    shutil.copytree(SYNTHETIC, tmp_path / "mydata")
    code, _ = init(tmp_path, monkeypatch, answers=["1", "2", "", ""])
    err = capsys.readouterr().err
    assert code == EXIT_OK, err[-3000:]
    assert " 1) mydata" in err
    assert "dataset: mydata" in (tmp_path / "mydata-mlp.yaml").read_text()


def test_the_decision_refuses_to_write_while_an_answer_no_longer_fits(
    tmp_path, monkeypatch, capsys
):
    # Answer the output type, then move the output to a numeric column: the answered type no
    # longer fits, so Enter does not write and the item is named; then stop. After the move the
    # window is uncertain again and asked (Enter), and Enter at the decision only shows why not.
    answers = [SYNTHETIC, "2", "", "a", "kind", "category", "a", "output", "b0", "", "", "q"]
    code, _ = init(tmp_path, monkeypatch, answers=answers)
    err = capsys.readouterr().err
    assert code == EXIT_USAGE, err[-3000:]
    assert "not ready to write" in err
    assert "output type" in err[err.rindex("not ready to write") :]
    assert not (tmp_path / "synthetic-mlp.yaml").exists()


def test_an_open_item_with_a_proposal_from_the_examples_is_not_asked(tmp_path, monkeypatch, capsys):
    # The anomaly data: the output type (two values) and the window (fallback) are uncertain and
    # asked; the budget is a convention and is not.
    code, _ = init(tmp_path, monkeypatch, "--board", "s32k144", answers=[ANOMALY, "", "", ""])
    err = capsys.readouterr().err
    assert code == EXIT_OK, err[-3000:]
    assert "What kind of answer is it?" in err
    assert "How many rows go into each prediction?" in err
    assert "How much may int8 cost?" not in err


# --- moved from tests/contract/test_init_contract.py (feature 013), rewritten for the new flow ---


def test_the_flow_shows_the_window_table_and_the_memory_panel_under_adjust(
    tmp_path, monkeypatch, capsys
):
    answers = [SYNTHETIC, "3", "", "a", "window", "", "a", "quantize", "", ""]
    code, _ = init(tmp_path, monkeypatch, answers=answers)
    out, err = capsys.readouterr()
    assert code == EXIT_OK, err[-3000:]
    assert out == "synthetic-mlp.yaml\n"
    assert "what your data allows" in err and "memory on your boards" in err


def test_back_at_the_decision_and_at_the_item_list_returns_to_the_proposal(
    tmp_path, monkeypatch, capsys
):
    answers = [SYNTHETIC, "2", "", "<", "<", ""]
    code, _ = init(tmp_path, monkeypatch, answers=answers)
    assert code == EXIT_OK, capsys.readouterr().err[-3000:]
    text = (tmp_path / "synthetic-mlp.yaml").read_text()
    assert "targets: [s32k144]" in text and "quantization" not in text


def test_end_of_input_after_the_boards_writes_nothing(tmp_path, monkeypatch, capsys):
    code, _ = init(tmp_path, monkeypatch, answers=[SYNTHETIC, "3"])
    assert code == EXIT_USAGE
    assert "nothing was written" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())
