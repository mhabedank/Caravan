"""Every rule that can reject a manifest has a fixture, and only those do.

This is the test that keeps SC-002 true as rules are added, rather than true only today. It also
checks the other direction: an identifier that can never reject a manifest must not have an
invalid fixture, because such a fixture could only ever be a lie about what the rule does.
"""

from __future__ import annotations

from caravan.manifest.errors import (
    BOARD_RULES,
    ENTAILED_RULES,
    INFORMATIONAL_RULES,
    MANIFEST_REJECTION_RULES,
)
from tests.support import invalid_cases


def test_every_rejection_rule_has_a_fixture() -> None:
    covered = {expected["rule"] for _, _, expected in invalid_cases() if expected["rule"]}
    missing = MANIFEST_REJECTION_RULES - covered
    assert not missing, f"rules with no invalid manifest fixture: {sorted(missing)}"


def test_no_fixture_claims_a_rule_that_cannot_reject_a_manifest() -> None:
    covered = {expected["rule"] for _, _, expected in invalid_cases() if expected["rule"]}
    cannot = BOARD_RULES | INFORMATIONAL_RULES | ENTAILED_RULES
    wrong = covered & cannot
    assert not wrong, (
        f"these identifiers cannot reject a manifest, so they must not have an invalid "
        f"manifest fixture: {sorted(wrong)}"
    )


def test_rule_groups_do_not_overlap() -> None:
    groups = [MANIFEST_REJECTION_RULES, BOARD_RULES, INFORMATIONAL_RULES, ENTAILED_RULES]
    for index, first in enumerate(groups):
        for second in groups[index + 1 :]:
            assert not first & second, f"a rule is in two groups: {sorted(first & second)}"
