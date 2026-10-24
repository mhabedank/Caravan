"""The quantize verb's surface, and the one thing it must never offer.

Parser-level and manifest-level, so this runs on every Python in the matrix and in a clean
environment. What the stage does is tested in ``tests/train``.
"""

from __future__ import annotations

import argparse
import json

import pytest

from caravan.cli.main import EXIT_RULE, EXIT_USAGE, build_parser, main
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

#: Anything that would let a budget be loosened from outside the manifest. Principle V: loosening
#: a budget is an edit to the manifest, visible in version control.
FORBIDDEN = (
    "accuracy",
    "threshold",
    "drop",
    "gate",
    "tolerance",
    "accept",
    "force",
    "skip",
    "ignore",
    "allow",
    "disable",
    "override",
)


def subparser(verb: str) -> argparse.ArgumentParser:
    for action in build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices[verb]
    raise AssertionError("no subcommands found")  # pragma: no cover


def test_the_options_are_exactly_the_documented_ones() -> None:
    options = {s for action in subparser("quantize")._actions for s in action.option_strings}
    assert options == EXPECTED_OPTIONS


def test_nothing_in_the_option_surface_can_loosen_the_gate() -> None:
    # SC-006, and the assertion is over the *whole* command line rather than this verb alone:
    # a flag added to a shared option group would be just as silencing.
    from tests.contract.test_no_skip_option import all_option_strings

    options = all_option_strings(build_parser())
    offenders = sorted(o for o in options if any(word in o.lower() for word in FORBIDDEN))
    assert not offenders, (
        f"these options could be read as loosening a budget: {offenders}; the threshold lives in "
        "the manifest and nowhere else (Principle V)"
    )


def test_the_manifest_is_a_required_positional() -> None:
    positionals = [a.dest for a in subparser("quantize")._actions if not a.option_strings]
    assert positionals == ["manifest"]


def test_an_invalid_manifest_is_refused_before_anything_is_converted(tmp_path, capsys) -> None:
    code = main(
        [
            "quantize",
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
        main(["quantize", "manifest.yaml", "--accuracy-drop-max", "0.5"])
    assert caught.value.code == EXIT_USAGE


def test_json_goes_to_standard_output(tmp_path, capsys) -> None:
    main(
        [
            "quantize",
            str(INVALID / "cf-1-split-sum.yaml"),
            "--json",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["outcome"] == "invalid"
    assert captured.err == ""
