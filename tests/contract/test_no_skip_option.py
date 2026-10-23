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


def test_the_walk_reaches_every_stage_verb() -> None:
    # The walk below is recursive, so each stage verb was covered the moment it was added. This
    # says so out loud: a guarantee that holds by accident is one that stops holding the first time
    # somebody flattens the walk.
    options = all_option_strings(build_parser())
    assert "--cache-dir" in options and "--fresh" in options


def test_every_stage_verb_is_actually_present_to_be_walked() -> None:
    # The other half, and the one that would have gone unnoticed: the walk above proves the
    # *options* are reached, not that a verb exists. A verb added without its options, or removed,
    # would leave the check above passing on somebody else's flags.
    import argparse

    parser = build_parser()
    subcommands = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    for verb in ("build", "train", "quantize", "export"):
        assert verb in subcommands.choices, f"{verb} is not a subcommand"
        options = all_option_strings(subcommands.choices[verb])
        assert "--cache-dir" in options and "--fresh" in options, verb


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


def test_the_fit_check_has_no_switch_of_its_own() -> None:
    # Feature 006: the check before training runs in every verb that builds. No flag (above), no
    # manifest field and no environment variable reaches it: it reads the targets and the
    # quantization, and nothing that could turn it off.
    import inspect

    from caravan.cli import pipeline
    from caravan.stages import fit
    from caravan.targets import fit as arithmetic

    assert fit.SPEC.reads == ("export.targets", "export.quantization")
    for module in (fit, arithmetic):
        source = inspect.getsource(module)
        assert "environ" not in source and "getenv" not in source, module.__name__
    # The pipeline inserts it after every build, unconditionally.
    assert 'if plan.spec.name == "build":' in inspect.getsource(pipeline.run_pipeline)
