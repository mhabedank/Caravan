"""Every export rule is provoked somewhere, and none pretends to be a manifest rule.

The same guard the quantization rules have, for the same reason: an identifier nothing can reach is
a promise in a document rather than a refusal in a tool.
"""

from __future__ import annotations

from pathlib import Path

from caravan.manifest.errors import (
    ALL_RULES,
    EXPORT_RULES,
    MANIFEST_REJECTION_RULES,
    QUANTIZE_RULES,
    RUN_RULES,
)

TESTS = Path(__file__).resolve().parent.parent
SOURCE = Path(__file__).resolve().parents[2] / "src" / "caravan"


def rule_constant_names() -> dict[str, str]:
    from caravan.manifest import errors

    return {
        value: name
        for name, value in vars(errors).items()
        if name.startswith("RULE_") and isinstance(value, str)
    }


def test_every_export_rule_is_provoked_by_a_test() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in TESTS.rglob("test_*.py")
        if path.name != Path(__file__).name
    )
    names = rule_constant_names()
    missing = sorted(rule for rule in EXPORT_RULES if names[rule] not in sources)
    assert not missing, f"every export rule needs a test that provokes it; none mentions: {missing}"


def test_every_export_rule_is_raised_by_the_code_that_owns_it() -> None:
    # The other half: a rule mentioned only by a test that builds its own failure would pass the
    # check above while nothing ever refused anything.
    #
    # Read across the stage *and* the export package, because that is where the rules live: X-1,
    # X-2 and X-3 are the stage's, and X-4 belongs to the resolver, which is the only code that can
    # know whether the runtime has a method for an operator. Pinning the check to the stage file
    # alone was this test's first form, and it failed for a good reason.
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            SOURCE / "stages" / "export.py",
            *sorted((SOURCE / "export").glob("*.py")),
        )
    )
    names = rule_constant_names()
    missing = sorted(rule for rule in EXPORT_RULES if names[rule] not in source)
    assert not missing, f"nothing raises: {missing}"


def test_the_groups_stay_separate() -> None:
    assert not EXPORT_RULES & MANIFEST_REJECTION_RULES
    assert not EXPORT_RULES & RUN_RULES
    assert not EXPORT_RULES & QUANTIZE_RULES
    assert EXPORT_RULES <= ALL_RULES


def test_the_x_prefix_belongs_to_the_export_and_to_nothing_else() -> None:
    # E was taken by the board emulator rules, which is why these are X. Asserted so that a future
    # group does not quietly reuse a letter and make two unrelated refusals look related.
    #
    # X-5 is the one X identifier outside EXPORT_RULES, and deliberately so: it was written to
    # refuse a board naming an accelerated library with no sourced coverage data, and the board
    # schema turned out to make that board impossible. It lives in ENTAILED_RULES with DS-7, which
    # was withdrawn for the same kind of reason in feature 003.
    from caravan.manifest.errors import ENTAILED_RULES, RULE_KERNEL_COVERAGE_UNKNOWN

    assert all(rule.startswith("X-") for rule in EXPORT_RULES)
    outside = {rule for rule in ALL_RULES - EXPORT_RULES if rule.startswith("X-")}
    assert outside == {RULE_KERNEL_COVERAGE_UNKNOWN}
    assert RULE_KERNEL_COVERAGE_UNKNOWN in ENTAILED_RULES
