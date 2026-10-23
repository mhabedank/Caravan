"""caravan/v0 → caravan/v0.1, step by step (feature 006, contracts/manifest.md, Migration).

Principle IX: an older manifest is migrated in memory on every load, the file is never written, and
every field that changes is said out loud — one notice each.
"""

from __future__ import annotations

import copy

from caravan.manifest._yaml import read_mapping
from caravan.manifest.load import load_manifest
from caravan.manifest.migrate import (
    CURRENT_SCHEMA_VERSION,
    PREVIOUS_SCHEMA_VERSION,
    MigrationNotice,
    default_registry,
    migrate_v0_to_v01,
)
from caravan.manifest.schema.removed import (
    BENCHMARK_ONLY_PUBLISH_NOTICE,
    BUDGET_ADDED_NOTICE,
    BY_PATH,
)
from tests.support import VALID

PILOT = VALID / "picket-mlp.yaml"


def everything_removed() -> dict:
    """A previous-form manifest carrying every field the new form removed or moved."""
    return {
        "apiVersion": "caravan/v0",
        "model": {
            "name": "every-field",
            "version": "0.0.1",
            "topic": "automotive-security",
            "task": "can-ids",
            "template": "mlp",
            "params": {"hidden": [8]},
        },
        "dataset": {
            "source": "datasets/example/",
            "window": 32,
            "labels": ["normal", "attack"],
            "representative_samples": 100,
            "license": "CC-BY-4.0",
            "permitted_use": "training",
        },
        "export": {"targets": ["stm32h743"], "accuracy_drop_max": 0.05},
        "verify": {"emulator": "none"},
        "bench": {"metrics": ["flash"]},
        "publish": {"hf_repo": "someone/model", "license": "apache-2.0"},
        "compliance": {
            "eu_ai_act_class": "minimal-risk",
            "privacy": "no-personal-data",
            "intended_use": "A manifest that carries every removed field at once",
            "known_limits": ["exists for a test"],
        },
    }


def test_every_removed_field_is_dropped_or_moved_with_one_notice() -> None:
    migrated, notices = migrate_v0_to_v01(everything_removed())

    assert [(notice.path, notice.action) for notice in notices] == [
        ("model.topic", "dropped"),
        ("model.task", "dropped"),
        ("dataset.license", "dropped"),
        ("dataset.permitted_use", "dropped"),
        ("compliance", "dropped"),
        ("verify", "dropped"),
        ("bench", "dropped"),
        ("publish", "dropped"),
        ("dataset.window", "moved"),
        ("dataset.labels", "moved"),
        ("export.accuracy_drop_max", "moved"),
    ]
    for notice in notices:
        assert notice.reason == BY_PATH[notice.path].reason
        assert notice.to == BY_PATH[notice.path].to

    for gone in ("compliance", "verify", "bench", "publish"):
        assert gone not in migrated
    assert set(migrated["model"]) == {"name", "version", "template", "params"}
    assert set(migrated["dataset"]) == {"source", "representative_samples"}
    assert migrated["export"] == {"targets": ["stm32h743"]}


def test_the_declarations_carry_what_moved() -> None:
    migrated, _ = migrate_v0_to_v01(everything_removed())

    assert migrated["apiVersion"] == CURRENT_SCHEMA_VERSION
    assert migrated["inputs"] == [{"name": "input", "kind": "series", "window": 32}]
    assert migrated["outputs"] == [
        {
            "name": "output",
            "kind": "class",
            "column": "label",
            "labels": ["normal", "attack"],
            "accuracy_drop_max": 0.05,
        }
    ]


def test_an_unstated_budget_is_stated_by_the_migration() -> None:
    # The previous form defaulted it to 0.02; the new form requires it (Principle V, FR-029). The
    # migration writes the old default rather than a stricter or a looser one, and says so.
    document = everything_removed()
    del document["export"]["accuracy_drop_max"]

    migrated, notices = migrate_v0_to_v01(document)

    assert migrated["outputs"][0]["accuracy_drop_max"] == 0.02
    added = [notice for notice in notices if notice.action == "added"]
    assert added == [
        MigrationNotice(
            "export.accuracy_drop_max", "added", BUDGET_ADDED_NOTICE, "outputs[0].accuracy_drop_max"
        )
    ]


def test_a_benchmark_only_dataset_asked_for_publication_is_named_not_dropped_silently() -> None:
    document = everything_removed()
    document["dataset"]["permitted_use"] = "benchmark-only"

    _, notices = migrate_v0_to_v01(document)

    notice = next(n for n in notices if n.path == "dataset.permitted_use")
    assert notice.reason == BENCHMARK_ONLY_PUBLISH_NOTICE


def test_benchmark_only_without_publication_gets_the_ordinary_notice() -> None:
    document = everything_removed()
    document["dataset"]["permitted_use"] = "benchmark-only"
    del document["publish"]

    _, notices = migrate_v0_to_v01(document)

    notice = next(n for n in notices if n.path == "dataset.permitted_use")
    assert notice.reason == BY_PATH["dataset.permitted_use"].reason


def test_fields_never_written_produce_no_notice() -> None:
    minimal = {
        "model": {"name": "m", "version": "0.0.1", "template": "mlp"},
        "dataset": {"source": "d/"},
        "export": {"targets": ["esp32"], "accuracy_drop_max": 0.02},
    }
    _, notices = migrate_v0_to_v01(minimal)
    assert [notice.path for notice in notices] == ["export.accuracy_drop_max"]


def test_the_input_mapping_is_not_mutated() -> None:
    document = everything_removed()
    before = copy.deepcopy(document)
    migrate_v0_to_v01(document)
    assert document == before


def test_a_document_without_a_version_is_migrated_as_the_previous_form() -> None:
    document = everything_removed()
    del document["apiVersion"]

    result = default_registry().migrate(document)

    assert result.declared == PREVIOUS_SCHEMA_VERSION
    assert result.version_was_absent
    assert result.effective == CURRENT_SCHEMA_VERSION
    assert result.applied == (PREVIOUS_SCHEMA_VERSION,)
    assert len(result.notices) == 11


def test_the_committed_pilot_loads_and_its_file_is_untouched() -> None:
    before = PILOT.read_bytes()

    outcome = load_manifest(PILOT)

    assert outcome.is_valid, outcome.findings
    assert outcome.declared_version == PREVIOUS_SCHEMA_VERSION
    assert outcome.effective_version == CURRENT_SCHEMA_VERSION
    assert [(notice.path, notice.action) for notice in outcome.notices] == [
        ("model.topic", "dropped"),
        ("model.task", "dropped"),
        ("compliance", "dropped"),
        ("verify", "dropped"),
        ("bench", "dropped"),
        ("publish", "dropped"),
        ("dataset.window", "moved"),
        ("dataset.labels", "moved"),
        ("export.accuracy_drop_max", "moved"),
    ]
    assert PILOT.read_bytes() == before


def test_the_migrated_pilot_keeps_its_label_order_and_window() -> None:
    outcome = load_manifest(PILOT)
    assert outcome.manifest is not None
    original = read_mapping(PILOT)
    assert outcome.manifest.outputs[0].labels == original["dataset"]["labels"]
    assert outcome.manifest.inputs[0].window == original["dataset"]["window"]
    assert outcome.manifest.outputs[0].accuracy_drop_max == original["export"]["accuracy_drop_max"]
