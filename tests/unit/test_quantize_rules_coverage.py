"""Every quantization rule is provoked somewhere, and none pretends to be a manifest rule."""

from __future__ import annotations

from pathlib import Path

from caravan.manifest.errors import (
    ALL_RULES,
    MANIFEST_REJECTION_RULES,
    QUANTIZE_RULES,
    RUN_RULES,
)

TESTS = Path(__file__).resolve().parent.parent


def rule_constant_names() -> dict[str, str]:
    from caravan.manifest import errors

    return {
        value: name
        for name, value in vars(errors).items()
        if name.startswith("RULE_") and isinstance(value, str)
    }


def test_every_quantization_rule_is_provoked_by_a_test() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in TESTS.rglob("test_*.py")
        if path.name != Path(__file__).name
    )
    names = rule_constant_names()
    missing = sorted(rule for rule in QUANTIZE_RULES if names[rule] not in sources)
    assert not missing, (
        f"every quantization rule needs a test that provokes it; none mentions: {missing}"
    )


def test_the_groups_stay_separate() -> None:
    # Each group answers a different question, and the fixture coverage test of feature 001
    # demands an invalid *manifest* for everything in the rejection group — which a rule about a
    # produced model could never have.
    assert not QUANTIZE_RULES & MANIFEST_REJECTION_RULES
    assert not QUANTIZE_RULES & RUN_RULES
    assert QUANTIZE_RULES <= ALL_RULES


def test_the_gate_is_a_rule_like_any_other() -> None:
    # Q-4 is a budget saying no rather than a schema rule, and it travels through the same
    # machinery: an identifier, a field path, a message, exit code 1. That sameness is the point —
    # a continuous integration job should not need a second mechanism to notice a failed gate.
    from caravan.manifest.errors import RULE_ACCURACY_GATE

    assert RULE_ACCURACY_GATE in QUANTIZE_RULES
    assert RULE_ACCURACY_GATE in ALL_RULES
