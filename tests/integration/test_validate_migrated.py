"""SC-002 of feature 006: every manifest that was valid keeps loading, and says what changed.

Principle IX: an older manifest is migrated in memory on every load, never rewritten, and never
silently reinterpreted — so each previous-form fixture carries, in a sibling ``.notices.json``, the
exact notices it must produce. A new-form fixture produces none.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from caravan.manifest.load import load_manifest
from caravan.manifest.migrate import CURRENT_SCHEMA_VERSION
from tests.support import MIGRATION, VALID

MANIFESTS = sorted([*VALID.glob("*.yaml"), *MIGRATION.glob("*.yaml")])


def expected_notices(path: Path) -> list[dict]:
    sibling = path.with_suffix(".notices.json")
    if not sibling.exists():
        return []
    return json.loads(sibling.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda path: path.name)
def test_every_manifest_loads_with_exactly_its_notices(path: Path) -> None:
    before = path.read_bytes()

    outcome = load_manifest(path)

    assert outcome.is_valid, outcome.findings
    assert outcome.effective_version == CURRENT_SCHEMA_VERSION
    assert [notice.as_dict() for notice in outcome.notices] == expected_notices(path)
    assert path.read_bytes() == before


def test_every_previous_form_fixture_has_its_expectation_written_down() -> None:
    # A previous-form manifest without a .notices.json would pass the test above by expecting
    # nothing, which is the one thing a migrated manifest never produces.
    for path in MANIFESTS:
        declared = load_manifest(path).declared_version
        if declared != CURRENT_SCHEMA_VERSION:
            assert path.with_suffix(".notices.json").exists(), path.name


def test_the_retired_rules_fixtures_now_load() -> None:
    # They were invalid only because of CF-3, CF-7 and CF-8, which no longer exist.
    names = {path.stem for path in MIGRATION.glob("*.yaml")}
    assert names == {
        "cf-3-personal-data-minimal-risk",
        "cf-7-emulator-without-platform",
        "cf-8-benchmark-only-publish",
    }
