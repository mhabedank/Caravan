"""Principle IX in executable form: an archived manifest keeps working.

The registry is exercised twice: with a synthetic older version here, which is only possible
because the registry is an instance rather than a module-level singleton (research R6), and with
the real caravan/v0 → caravan/v0.1 transform of feature 006 in ``test_migration_v01.py``.
"""

from __future__ import annotations

import pytest

from caravan.manifest.load import load_manifest
from caravan.manifest.migrate import (
    CURRENT_SCHEMA_VERSION,
    PREVIOUS_SCHEMA_VERSION,
    SchemaVersionRegistry,
    UnknownSchemaVersion,
    default_registry,
)
from tests.support import INVALID, NO_VERSION

OLD = "caravan/v-test-old"


def rename_window(data: dict) -> tuple[dict, tuple]:
    """A synthetic migration: an older schema called the input's window ``frame``."""
    migrated = dict(data)
    inputs = [dict(entry) for entry in migrated.get("inputs", [])]
    for entry in inputs:
        if "frame" in entry:
            entry["window"] = entry.pop("frame")
    migrated["inputs"] = inputs
    return migrated, ()


@pytest.fixture
def registry_with_history() -> SchemaVersionRegistry:
    return SchemaVersionRegistry(
        versions=(OLD, CURRENT_SCHEMA_VERSION), transforms={OLD: rename_window}
    )


def test_an_older_manifest_is_migrated_in_memory(tmp_path, registry_with_history) -> None:
    source = (
        "apiVersion: caravan/v-test-old\n"
        "model:\n"
        "  name: old-manifest\n"
        "  version: 0.0.1\n"
        "  template: mlp\n"
        "  params:\n"
        "    hidden: [8]\n"
        "inputs:\n"
        "  - {name: frames, kind: series, frame: 32}\n"
        "outputs:\n"
        "  - {name: verdict, kind: class, accuracy_drop_max: 0.02}\n"
        "dataset:\n"
        "  source: datasets/example/\n"
        "  representative_samples: 100\n"
        "export:\n"
        "  targets: [stm32h743]\n"
    )
    manifest = tmp_path / "archived.yaml"
    manifest.write_text(source, encoding="utf-8")
    before = manifest.read_bytes()

    outcome = load_manifest(manifest, versions=registry_with_history)

    assert outcome.is_valid, outcome.findings
    assert outcome.manifest is not None
    assert outcome.manifest.inputs[0].window == 32
    assert outcome.declared_version == OLD
    assert outcome.effective_version == CURRENT_SCHEMA_VERSION
    assert outcome.migrations_applied == (OLD,)
    # The file on disk is untouched: reading an archived manifest must not rewrite it.
    assert manifest.read_bytes() == before


def test_a_manifest_without_a_version_is_the_oldest_known_one() -> None:
    outcome = load_manifest(NO_VERSION)
    assert outcome.is_valid, outcome.findings
    assert outcome.declared_version == PREVIOUS_SCHEMA_VERSION
    assert outcome.effective_version == CURRENT_SCHEMA_VERSION


def test_an_unknown_version_is_refused_and_names_what_is_implemented() -> None:
    outcome = load_manifest(INVALID / "v-1-unknown-version.yaml")
    assert not outcome.is_valid
    finding = outcome.findings[0]
    assert finding.rule == "V-1"
    assert finding.accepted == (PREVIOUS_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION)


def test_the_registry_refuses_a_transform_for_the_newest_version() -> None:
    with pytest.raises(ValueError, match="newest version"):
        SchemaVersionRegistry(
            versions=(CURRENT_SCHEMA_VERSION,), transforms={CURRENT_SCHEMA_VERSION: dict}
        )


def test_the_shipped_registry_knows_both_forms() -> None:
    registry = default_registry()
    assert registry.known == (PREVIOUS_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION)
    assert registry.migrate({"apiVersion": CURRENT_SCHEMA_VERSION}).applied == ()


def test_an_unknown_version_raises_with_the_known_ones() -> None:
    with pytest.raises(UnknownSchemaVersion) as caught:
        default_registry().migrate({"apiVersion": "caravan/v9"})
    assert caught.value.known == (PREVIOUS_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION)
