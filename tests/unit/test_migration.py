"""Principle IX in executable form: an archived manifest keeps working.

The schema has one version today, so the mechanism is exercised with a synthetic older one. That
is only possible because the registry is an instance rather than a module-level singleton
(research R6) — and a mechanism with nothing in it is credible only if it is exercised.
"""

from __future__ import annotations

import pytest

from caravan.manifest.load import load_manifest
from caravan.manifest.migrate import (
    CURRENT_SCHEMA_VERSION,
    SchemaVersionRegistry,
    UnknownSchemaVersion,
    default_registry,
)
from tests.support import INVALID, NO_VERSION

OLD = "caravan/v-test-old"


def rename_window(data: dict) -> dict:
    """A synthetic migration: an older schema called the field ``frame``."""
    migrated = dict(data)
    dataset = dict(migrated.get("dataset", {}))
    if "frame" in dataset:
        dataset["window"] = dataset.pop("frame")
    migrated["dataset"] = dataset
    return migrated


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
        "  topic: automotive-security\n"
        "  task: can-ids\n"
        "  template: mlp\n"
        "  params:\n"
        "    hidden: [8]\n"
        "dataset:\n"
        "  source: datasets/example/\n"
        "  frame: 32\n"
        "  labels: [normal, attack]\n"
        "  representative_samples: 100\n"
        "export:\n"
        "  targets: [stm32h743]\n"
        "compliance:\n"
        "  eu_ai_act_class: minimal-risk\n"
        "  privacy: no-personal-data\n"
        "  intended_use: 'Archived manifest from an older schema version'\n"
        "  known_limits: ['Exists to exercise the migration registry']\n"
    )
    manifest = tmp_path / "archived.yaml"
    manifest.write_text(source, encoding="utf-8")
    before = manifest.read_bytes()

    outcome = load_manifest(manifest, versions=registry_with_history)

    assert outcome.is_valid, outcome.findings
    assert outcome.manifest is not None
    assert outcome.manifest.dataset.window == 32
    assert outcome.declared_version == OLD
    assert outcome.effective_version == CURRENT_SCHEMA_VERSION
    assert outcome.migrations_applied == (OLD,)
    # The file on disk is untouched: reading an archived manifest must not rewrite it.
    assert manifest.read_bytes() == before


def test_a_manifest_without_a_version_is_the_oldest_known_one() -> None:
    outcome = load_manifest(NO_VERSION)
    assert outcome.is_valid, outcome.findings
    assert outcome.declared_version == CURRENT_SCHEMA_VERSION
    assert outcome.effective_version == CURRENT_SCHEMA_VERSION


def test_an_unknown_version_is_refused_and_names_what_is_implemented() -> None:
    outcome = load_manifest(INVALID / "v-1-unknown-version.yaml")
    assert not outcome.is_valid
    finding = outcome.findings[0]
    assert finding.rule == "V-1"
    assert finding.accepted == (CURRENT_SCHEMA_VERSION,)


def test_the_registry_refuses_a_transform_for_the_newest_version() -> None:
    with pytest.raises(ValueError, match="newest version"):
        SchemaVersionRegistry(
            versions=(CURRENT_SCHEMA_VERSION,), transforms={CURRENT_SCHEMA_VERSION: dict}
        )


def test_the_shipped_registry_has_nothing_to_migrate_yet() -> None:
    registry = default_registry()
    assert registry.known == (CURRENT_SCHEMA_VERSION,)
    assert registry.migrate({"apiVersion": CURRENT_SCHEMA_VERSION}).applied == ()


def test_an_unknown_version_raises_with_the_known_ones() -> None:
    with pytest.raises(UnknownSchemaVersion) as caught:
        default_registry().migrate({"apiVersion": "caravan/v9"})
    assert caught.value.known == (CURRENT_SCHEMA_VERSION,)
