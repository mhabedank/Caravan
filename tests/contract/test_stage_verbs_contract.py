"""The surface of `build` and `train`: their options, their exit codes, and what they never offer.

Parser-level and manifest-level only, so this runs on every Python in the matrix and in the clean
environment. What the stages actually *do* is tested in ``tests/train/``, which is the one place
that needs a training framework.
"""

from __future__ import annotations

import argparse
import json

import pytest

from caravan.cli.main import (
    EXIT_ENVIRONMENT,
    EXIT_RULE,
    EXIT_USAGE,
    build_parser,
    main,
)
from caravan.env import training_framework_available
from tests.support import INVALID, PILOT_FIXTURE

STAGE_VERBS = ("build", "train")

#: Exactly the options ``contracts/cli.md`` fixes for a stage verb. An option that is not here
#: does not exist, and one that is must keep existing.
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


def subparser(verb: str) -> argparse.ArgumentParser:
    for action in build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices[verb]
    raise AssertionError("no subcommands found")  # pragma: no cover


@pytest.mark.parametrize("verb", STAGE_VERBS)
def test_the_options_are_exactly_the_documented_ones(verb) -> None:
    options = {string for action in subparser(verb)._actions for string in action.option_strings}
    assert options == EXPECTED_OPTIONS


@pytest.mark.parametrize("verb", STAGE_VERBS)
def test_the_manifest_is_a_required_positional(verb) -> None:
    positionals = [action.dest for action in subparser(verb)._actions if not action.option_strings]
    assert positionals == ["manifest"]


@pytest.mark.parametrize("verb", STAGE_VERBS)
def test_the_cache_defaults_beside_the_runs_directory(verb) -> None:
    defaults = {action.dest: action.default for action in subparser(verb)._actions}
    assert defaults["cache_dir"] == ".caravan/cache"
    assert defaults["runs_dir"] == "runs"
    assert defaults["fresh"] is False


@pytest.mark.parametrize("verb", STAGE_VERBS)
def test_an_invalid_manifest_is_refused_before_anything_is_built(verb, tmp_path, capsys) -> None:
    # Exit 1, not 4: the manifest is checked first, so a broken manifest is answered the same way
    # whether or not a training framework is installed anywhere.
    code = main(
        [
            verb,
            str(INVALID / "cf-1-split-sum.yaml"),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == EXIT_RULE
    assert "nothing was built" in capsys.readouterr().err


@pytest.mark.parametrize("verb", STAGE_VERBS)
def test_an_unreadable_manifest_exits_two(verb, capsys) -> None:
    assert main([verb, "no/such/manifest.yaml"]) == EXIT_USAGE


@pytest.mark.parametrize("verb", STAGE_VERBS)
def test_an_unknown_option_exits_two(verb) -> None:
    with pytest.raises(SystemExit) as caught:
        main([verb, "manifest.yaml", "--not-an-option"])
    assert caught.value.code == EXIT_USAGE


@pytest.mark.parametrize("verb", STAGE_VERBS)
def test_json_goes_to_standard_output_and_the_summary_to_standard_error(
    verb, tmp_path, capsys
) -> None:
    # The split that makes ``caravan train manifest.yaml --json > result.json`` safe. Asserted on
    # the refusal path, which is available without a framework.
    main(
        [
            verb,
            str(INVALID / "cf-1-split-sum.yaml"),
            "--json",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document["outcome"] == "invalid"
    assert captured.err == ""


@pytest.mark.parametrize("verb", STAGE_VERBS)
@pytest.mark.skipif(
    training_framework_available(),
    reason="the environment-incomplete code is only reachable without the framework",
)
def test_a_missing_framework_is_its_own_exit_code(verb, tmp_path) -> None:
    code = main(
        [
            verb,
            str(PILOT_FIXTURE),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == EXIT_ENVIRONMENT


def test_neither_verb_offers_a_way_to_train_on_data_the_author_forbade() -> None:
    # The specific thing a user might reach for when DS-9 refuses. There is no flag for it, and
    # there is no flag that lowers a split or silences a rule either — ``--fresh`` recomputes,
    # which is the only thing the cache options can do.
    options = set()
    for verb in STAGE_VERBS:
        options |= {
            string for action in subparser(verb)._actions for string in action.option_strings
        }
    forbidden = ("permit", "licen", "anyway", "accept", "split", "threshold", "drop")
    offenders = sorted(
        option for option in options if any(word in option.lower() for word in forbidden)
    )
    assert not offenders, offenders
