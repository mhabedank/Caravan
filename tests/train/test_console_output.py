"""A run's console shows Caravan's lines, not the framework's (feature 007, User Story 2).

Measured before this feature on the pilot fixture: 26 lines of a Keras export listing on stdout and
35 framework lines on stderr around Caravan's 9 (research R1). The listing on stdout also broke
``--json``. After it, the framework's output is kept in ``framework.log`` in the run directory.
"""

from __future__ import annotations

import json
import os
import re

import pytest

from caravan.cli.main import EXIT_INTERNAL, EXIT_OK, EXIT_RULE, main
from tests.support import PILOT_FIXTURE
from tests.train.conftest import latest_run

#: Lines that only the framework, the converter or Keras print (research R1).
FRAMEWORK_LINE = re.compile(
    r"^(I|W|E)0000 |Saved artifact|TensorSpec\(|fully_quantize|oneDNN|absl::|XNNPACK", re.MULTILINE
)


def export(root, *extra: str) -> int:
    return main(
        [
            "export",
            str(PILOT_FIXTURE),
            "--runs-dir",
            str(root / "runs"),
            "--cache-dir",
            str(root / "cache"),
            *extra,
        ]
    )


def test_the_console_holds_only_caravans_lines(tmp_path, capfd) -> None:
    assert export(tmp_path, "--fresh") == EXIT_OK
    seen = capfd.readouterr()
    console = seen.out + seen.err
    assert not FRAMEWORK_LINE.search(console), console
    assert len(console.splitlines()) <= 25, console
    run = latest_run(tmp_path / "runs")
    log = run / "framework.log"
    assert log.is_file()
    assert "fully_quantize" in log.read_text(encoding="utf-8")
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    assert report["artifacts"]["framework_log"] == "framework.log"


def test_json_on_standard_output_is_one_document(tmp_path, capfd) -> None:
    assert export(tmp_path, "--fresh", "--json") == EXIT_OK
    document = json.loads(capfd.readouterr().out)
    assert document["outcome"] == "valid"


def test_the_switch_shows_the_framework_again(tmp_path, capfd) -> None:
    assert export(tmp_path, "--fresh", "--framework-output") == EXIT_OK
    seen = capfd.readouterr()
    assert FRAMEWORK_LINE.search(seen.out + seen.err)
    assert not (latest_run(tmp_path / "runs") / "framework.log").exists()


def test_a_failure_inside_the_framework_names_the_stage_and_the_log(
    tmp_path, capfd, monkeypatch
) -> None:
    import caravan.convert.tflite as tflite

    def failing(*_args, **_kwargs):
        os.write(2, b"E0000 converter: something went wrong underneath\n")
        raise ValueError("the converter gave up")

    monkeypatch.setattr(tflite, "_convert", failing)
    assert export(tmp_path, "--fresh") == EXIT_RULE
    err = capfd.readouterr().err
    run = latest_run(tmp_path / "runs")
    assert "stage quantize failed" in err
    assert f"framework output: {run / 'framework.log'}" in err
    assert "something went wrong underneath" not in err
    assert "something went wrong underneath" in (run / "framework.log").read_text(encoding="utf-8")


def test_an_internal_error_names_the_stage_too(tmp_path, capfd, monkeypatch) -> None:
    import caravan.convert.tflite as tflite

    def broken(*_args, **_kwargs):
        os.write(2, b"E0000 converter: crashed\n")
        raise RuntimeError("a defect")

    monkeypatch.setattr(tflite, "convert", broken)
    assert export(tmp_path, "--fresh") == EXIT_INTERNAL
    err = capfd.readouterr().err
    assert "stage quantize failed" in err
    assert "framework output:" in err


@pytest.mark.parametrize("verb", ["build", "train"])
def test_every_stage_verb_keeps_the_console_clean(tmp_path, capfd, verb) -> None:
    code = main(
        [verb, str(PILOT_FIXTURE), "--runs-dir", str(tmp_path / "r"), "--cache-dir", str(tmp_path)]
    )
    assert code == EXIT_OK
    seen = capfd.readouterr()
    assert not FRAMEWORK_LINE.search(seen.out + seen.err)
