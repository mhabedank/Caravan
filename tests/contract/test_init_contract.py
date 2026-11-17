"""``caravan init``: streams, exit codes, options, aborts (feature 013, contracts/cli-init.md)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, EXIT_RULE, EXIT_USAGE, main
from caravan.manifest.load import load_manifest

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
SYNTHETIC = str(DATA / "synthetic")


def init(tmp_path, monkeypatch, *args: str, stdin: str = "") -> int:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    return main(["init", *args])


def test_no_input_writes_a_valid_manifest_and_prints_its_path(tmp_path, monkeypatch, capsys):
    code = init(tmp_path, monkeypatch, "--no-input", "--dataset", SYNTHETIC, "--board", "s32k144")
    out, err = capsys.readouterr()
    assert code == EXIT_OK
    assert out == "synthetic-mlp.yaml\n"
    assert "wrote synthetic-mlp.yaml — valid" in err
    assert "next: caravan build synthetic-mlp.yaml" in err
    outcome = load_manifest(tmp_path / "synthetic-mlp.yaml")
    assert outcome.manifest is not None, outcome.findings
    assert sorted(p.name for p in tmp_path.iterdir()) == ["synthetic-mlp.yaml"]


def test_a_board_is_never_proposed(tmp_path, monkeypatch, capsys):
    assert init(tmp_path, monkeypatch, "--no-input", "--dataset", SYNTHETIC) == EXIT_USAGE
    assert "--board" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_without_data_the_missing_option_is_named(tmp_path, monkeypatch, capsys):
    assert init(tmp_path, monkeypatch, "--no-input", "--board", "esp32") == EXIT_USAGE
    assert "--dataset" in capsys.readouterr().err


def test_a_number_output_has_no_budget_proposal(tmp_path, monkeypatch, capsys):
    args = ["--no-input", "--dataset", str(DATA / "soc"), "--board", "esp32", "--output", "soc"]
    assert init(tmp_path, monkeypatch, *args) == EXIT_USAGE
    assert "--budget" in capsys.readouterr().err
    assert init(tmp_path, monkeypatch, *args, "--budget", "0.01") == EXIT_OK
    text = (tmp_path / "soc-mlp.yaml").read_text()
    assert "mae_increase_max: 0.01" in text and "type: number" in text


def test_an_existing_file_needs_overwrite(tmp_path, monkeypatch, capsys):
    (tmp_path / "m.yaml").write_text("keep\n")
    args = ["m.yaml", "--no-input", "--dataset", SYNTHETIC, "--board", "esp32"]
    assert init(tmp_path, monkeypatch, *args) == EXIT_USAGE
    assert "end it with !" in capsys.readouterr().err
    assert (tmp_path / "m.yaml").read_text() == "keep\n"
    assert init(tmp_path, monkeypatch, *args, "--overwrite") == EXIT_OK
    assert "apiVersion" in (tmp_path / "m.yaml").read_text()


def test_a_template_that_does_not_answer_the_output_is_refused(tmp_path, monkeypatch, capsys):
    args = ["--no-input", "--dataset", SYNTHETIC, "--board", "esp32", "--template", "autoencoder"]
    assert init(tmp_path, monkeypatch, *args) == EXIT_USAGE
    assert "does not answer a category output" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_inputs_are_changed_one_by_one(tmp_path, monkeypatch):
    args = ["--no-input", "--dataset", SYNTHETIC, "--board", "esp32"]
    edits = ["--input", "dlc=number", "--input", "b2=-"]
    assert init(tmp_path, monkeypatch, *args, *edits) == EXIT_OK
    text = (tmp_path / "synthetic-mlp.yaml").read_text()
    assert "{name: dlc, type: number}" in text
    assert "name: b2" not in text
    assert "# left out: b2" in text


def test_a_window_too_short_for_the_parameters_is_refused(tmp_path, monkeypatch, capsys):
    args = ["--no-input", "--dataset", SYNTHETIC, "--board", "esp32", "--template", "conv1d"]
    assert init(tmp_path, monkeypatch, *args, "--window", "4") == EXIT_USAGE
    assert "conv1d template needs more window" in capsys.readouterr().err


def test_quantization_none_is_written_and_needs_no_calibration(tmp_path, monkeypatch):
    args = ["--no-input", "--dataset", SYNTHETIC, "--board", "esp32", "--quantization", "none"]
    assert init(tmp_path, monkeypatch, *args) == EXIT_OK
    text = (tmp_path / "synthetic-mlp.yaml").read_text()
    assert "quantization: none" in text and "representative_samples" not in text


def test_params_are_given_as_a_flow_mapping(tmp_path, monkeypatch):
    args = ["--no-input", "--dataset", SYNTHETIC, "--board", "esp32", "--params", "{hidden: [8]}"]
    assert init(tmp_path, monkeypatch, *args) == EXIT_OK
    assert "hidden: [8]" in (tmp_path / "synthetic-mlp.yaml").read_text()


def test_the_dialogue_accepts_every_proposal_with_enter(tmp_path, monkeypatch, capsys):
    answers = "\n".join([SYNTHETIC, "3", *[""] * 12]) + "\n"
    code = init(tmp_path, monkeypatch, "--plain", stdin=answers)
    out, err = capsys.readouterr()
    assert code == EXIT_OK, err[-2000:]
    assert out == "synthetic-mlp.yaml\n"
    assert "what your data allows" in err and "memory on your boards" in err


def test_going_back_keeps_the_answers(tmp_path, monkeypatch, capsys):
    # s32k144, int8, back twice to the boards: Enter keeps s32k144, then every proposal.
    answers = "\n".join([SYNTHETIC, "2", "", "<", "<", "", *[""] * 12]) + "\n"
    assert init(tmp_path, monkeypatch, "--plain", stdin=answers) == EXIT_OK
    text = (tmp_path / "synthetic-mlp.yaml").read_text()
    assert "targets: [s32k144]" in text and "quantization" not in text


def test_end_of_input_writes_nothing(tmp_path, monkeypatch, capsys):
    code = init(tmp_path, monkeypatch, "--plain", stdin=f"{SYNTHETIC}\n3\n")
    assert code == EXIT_USAGE
    assert "nothing was written" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_unreadable_data_is_a_usage_error(tmp_path, monkeypatch, capsys):
    bad = str(DATA / "init" / "headers-differ")
    assert init(tmp_path, monkeypatch, "--no-input", "--dataset", bad) == EXIT_USAGE
    assert "different headers" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["float16", "int4"])
def test_only_int8_and_none_are_offered(tmp_path, monkeypatch, capsys, value):
    args = ["--no-input", "--dataset", SYNTHETIC, "--board", "esp32", "--quantization", value]
    assert init(tmp_path, monkeypatch, *args) == EXIT_USAGE
    assert "int8 or none" in capsys.readouterr().err


def test_exit_rule_is_reserved_for_a_refused_manifest() -> None:
    # Every offered choice validates (tests/integration/test_init_combinations.py), so code 1 is
    # reachable only through a free-form answer the session cannot check ahead.
    assert EXIT_RULE == 1
