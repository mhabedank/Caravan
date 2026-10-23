"""Constitution 4.0.0, Principle IX: before 1.0.0 one schema version is read, every other refused.

An older form, a newer one, or none at all is refused with V-1. Nothing is migrated or
reinterpreted, the author's file is left as it is, and the refusal names the implemented version
and the change note that says what to edit by hand.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from caravan.manifest.errors import RULE_UNKNOWN_SCHEMA_VERSION
from caravan.manifest.load import load_manifest
from caravan.manifest.version import (
    CHANGE_NOTE,
    SCHEMA_VERSION,
    UnknownSchemaVersion,
    check_version,
)
from tests.support import INVALID, MINIMAL

ROOT = Path(__file__).resolve().parents[2]


def test_the_implemented_version_passes() -> None:
    assert check_version({"apiVersion": SCHEMA_VERSION}) == SCHEMA_VERSION


@pytest.mark.parametrize("declared", ["caravan/v0", "caravan/v1", "v0.1", 0.1])
def test_any_other_version_is_refused(declared) -> None:
    with pytest.raises(UnknownSchemaVersion) as caught:
        check_version({"apiVersion": declared})
    assert caught.value.declared == str(declared)


def test_an_undeclared_version_is_refused_not_read_as_some_version() -> None:
    with pytest.raises(UnknownSchemaVersion) as caught:
        check_version({})
    assert caught.value.declared is None
    assert caught.value.problem().startswith("no schema version declared")


REFUSED = ["v-1-previous-version", "v-1-no-version", "v-1-unknown-version"]


@pytest.mark.parametrize("fixture", REFUSED)
def test_the_refusal_names_the_version_and_the_change_note(fixture) -> None:
    path = INVALID / f"{fixture}.yaml"
    before = path.read_bytes()
    outcome = load_manifest(path)
    assert outcome.manifest is None
    (finding,) = outcome.findings
    assert finding.rule == RULE_UNKNOWN_SCHEMA_VERSION
    assert finding.path == "apiVersion"
    assert finding.accepted == (SCHEMA_VERSION,)
    assert SCHEMA_VERSION in finding.problem
    assert CHANGE_NOTE in finding.problem
    assert path.read_bytes() == before


def test_the_change_note_exists() -> None:
    assert (ROOT / CHANGE_NOTE).is_file()


def test_a_current_manifest_records_its_version() -> None:
    assert load_manifest(MINIMAL).schema_version == SCHEMA_VERSION
