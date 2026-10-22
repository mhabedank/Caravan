"""FR-005: no option skips, forces, ignores or downgrades a check.

Principle V in executable form. An absent flag is exactly the kind of thing that gets added back
by accident, so its absence is asserted rather than assumed.
"""

from __future__ import annotations

import argparse

from caravan.cli.main import build_parser

FORBIDDEN_SUBSTRINGS = (
    "force",
    "skip",
    "ignore",
    "no-validate",
    "no-check",
    "allow-",
    "disable",
    "unsafe",
    "override",
    "relax",
    "lenient",
    "warn-only",
)


def all_option_strings(parser: argparse.ArgumentParser) -> set[str]:
    options = {string for action in parser._actions for string in action.option_strings}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                options |= all_option_strings(sub)
    return options


def test_the_walk_reaches_the_stage_verbs_of_feature_002() -> None:
    # The walk below is recursive, so ``build`` and ``train`` were covered the moment they were
    # added. This says so out loud: a guarantee that holds by accident is one that stops holding
    # the first time somebody flattens the walk.
    options = all_option_strings(build_parser())
    assert "--cache-dir" in options and "--fresh" in options


def test_no_option_can_silence_a_gate() -> None:
    options = all_option_strings(build_parser())
    offenders = sorted(
        option
        for option in options
        for token in FORBIDDEN_SUBSTRINGS
        if token in option.lower().lstrip("-")
    )
    assert not offenders, (
        "a budget or a rule must not be skippable by a flag (FR-005, Principle V); "
        f"found: {offenders}"
    )


def test_the_options_that_do_exist_only_change_where_output_goes() -> None:
    # --no-report and --stdout suppress *writing*, never checking: both still run every rule.
    options = all_option_strings(build_parser())
    assert "--no-report" in options
    assert "--stdout" in options
