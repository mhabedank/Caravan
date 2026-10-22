"""Every run rule is provoked somewhere, and no run rule pretends to be a manifest rule.

Feature 001 does this for the rules that refuse a manifest, against its fixture library. A run
rule cannot have a manifest fixture — the manifest is valid and the *data* disagrees with it — so
the coverage check is against the test suite instead: a rule nobody provokes is a rule nobody has
seen fire.
"""

from __future__ import annotations

from pathlib import Path

from caravan.manifest.errors import (
    ALL_RULES,
    ENTAILED_RULES,
    MANIFEST_REJECTION_RULES,
    RULE_DATASET_FEATURE_WIDTH,
    RUN_RULES,
)

TESTS = Path(__file__).resolve().parent.parent


def rule_constant_names() -> dict[str, str]:
    """Rule identifier -> the constant that carries it, so a test can refer to either."""
    from caravan.manifest import errors

    return {
        value: name
        for name, value in vars(errors).items()
        if name.startswith("RULE_") and isinstance(value, str)
    }


def test_every_run_rule_is_provoked_by_a_test() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in TESTS.rglob("test_*.py")
        if path.name != Path(__file__).name
    )
    names = rule_constant_names()
    missing = sorted(rule for rule in RUN_RULES if names[rule] not in sources)
    assert not missing, (
        f"every run rule must have a test that provokes it; no test mentions: {', '.join(missing)}"
    )


def test_no_run_rule_is_also_a_manifest_rejection_rule() -> None:
    # The two groups answer different questions — "is this manifest acceptable" and "do the data
    # and the manifest agree" — and the fixture coverage test of feature 001 demands an invalid
    # manifest for everything in the first group. A run rule in that group would demand a fixture
    # that cannot exist.
    overlap = sorted(RUN_RULES & MANIFEST_REJECTION_RULES)
    assert not overlap, f"these rules are in both groups: {', '.join(overlap)}"


def test_the_withdrawn_rule_is_entailed_and_not_expected_to_fire() -> None:
    # DS-7 was withdrawn during the analysis pass of feature 002: it would have compared the
    # data's feature width against what the manifest's window implies, and the manifest implies
    # nothing about feature width. It stays reserved rather than renumbering DS-8 and DS-9.
    assert RULE_DATASET_FEATURE_WIDTH in ENTAILED_RULES
    assert RULE_DATASET_FEATURE_WIDTH not in RUN_RULES
    assert RULE_DATASET_FEATURE_WIDTH in ALL_RULES


def test_every_rule_identifier_is_unique_and_accounted_for() -> None:
    names = rule_constant_names()
    assert len(names) == len(
        [
            name
            for name in vars(__import__("caravan.manifest.errors", fromlist=["x"]))
            if name.startswith("RULE_")
        ]
    ), "two rule constants share an identifier"
    assert set(names) == set(ALL_RULES)
