"""The export verb's surface, and the refusals that need no model to provoke.

Parser-level and manifest-level, so this runs on every Python in the matrix and in a clean
environment. What the stage produces is tested in ``tests/train``.
"""

from __future__ import annotations

import argparse
import json

import pytest

from caravan.cli.main import EXIT_RULE, EXIT_USAGE, build_parser, main
from caravan.manifest.errors import (
    RULE_FORMAT_NOT_IMPLEMENTED,
    RULE_NOTHING_TO_EXPORT,
    RunRuleFailure,
)
from caravan.stages.export import IMPLEMENTED_FORMATS, check_formats, load_model_bytes
from tests.support import INVALID

EXPECTED_OPTIONS = {
    "-h",
    "--help",
    "--runs-dir",
    "--cache-dir",
    "--fresh",
    "--framework-output",
    "--json",
    "-q",
    "--quiet",
}

#: Anything that would let the export set be changed from outside the manifest. What is exported
#: and for which boards is the manifest's business, so that the report describes the manifest.
FORBIDDEN = ("format", "target", "board", "arena", "resolver", "skip", "force", "only", "without")


def subparser(verb: str) -> argparse.ArgumentParser:
    for action in build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices[verb]
    raise AssertionError("no subcommands found")  # pragma: no cover


def test_the_options_are_exactly_the_documented_ones() -> None:
    options = {s for action in subparser("export")._actions for s in action.option_strings}
    assert options == EXPECTED_OPTIONS


def test_nothing_lets_the_export_set_be_chosen_on_the_command_line() -> None:
    options = {s for action in subparser("export")._actions for s in action.option_strings}
    offenders = sorted(o for o in options if any(word in o.lower() for word in FORBIDDEN))
    assert not offenders, f"these options would override the manifest: {offenders}"


def test_the_manifest_is_a_required_positional() -> None:
    positionals = [a.dest for a in subparser("export")._actions if not a.option_strings]
    assert positionals == ["manifest"]


def test_an_invalid_manifest_is_refused_before_anything_is_written(tmp_path, capsys) -> None:
    code = main(
        [
            "export",
            str(INVALID / "cf-1-split-sum.yaml"),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == EXIT_RULE
    assert "nothing was built" in capsys.readouterr().err


def test_an_unknown_option_exits_two() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["export", "manifest.yaml", "--format", "onnx"])
    assert caught.value.code == EXIT_USAGE


def test_json_goes_to_standard_output(tmp_path, capsys) -> None:
    main(
        [
            "export",
            str(INVALID / "cf-1-split-sum.yaml"),
            "--json",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert json.loads(capsys.readouterr().out)["outcome"] == "invalid"


def test_an_unimplemented_format_refuses_by_name() -> None:
    # X-1. The refusal names the format and what is implemented, so the author can act on it.
    with pytest.raises(RunRuleFailure) as raised:
        check_formats(["flatbuffer", "c_array", "onnx"])
    finding = raised.value.finding
    assert finding.rule == RULE_FORMAT_NOT_IMPLEMENTED
    assert "onnx" in finding.problem
    assert all(name in finding.problem for name in IMPLEMENTED_FORMATS)


def test_an_unimplemented_format_refuses_before_any_format_is_written() -> None:
    # The part worth asserting: the check runs over the whole list before the stage writes
    # anything, so a manifest asking for three formats where two are implemented gets nothing
    # rather than a run that exported two of three and exited 0.
    assert "Nothing was written" in _problem(["onnx"])


def test_the_implemented_formats_pass_unchanged() -> None:
    assert check_formats(list(IMPLEMENTED_FORMATS)) == IMPLEMENTED_FORMATS


def test_a_run_with_no_quantized_model_refuses_and_names_the_stage(tmp_path) -> None:
    # X-2. Reached when the accuracy gate failed, or when quantize was never run.
    with pytest.raises(RunRuleFailure) as raised:
        load_model_bytes(tmp_path)
    finding = raised.value.finding
    assert finding.rule == RULE_NOTHING_TO_EXPORT
    assert "caravan quantize" in finding.problem
    assert "failed accuracy gate" in finding.problem


def _problem(formats: list[str]) -> str:
    try:
        check_formats(formats)
    except RunRuleFailure as failure:
        return failure.finding.problem
    raise AssertionError("expected a refusal")  # pragma: no cover
