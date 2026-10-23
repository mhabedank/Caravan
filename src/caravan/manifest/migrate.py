"""Schema versions and the migrations between them.

Principle IX: an older manifest is migrated, not refused. A manifest is also the archival record
of how a published model was built, so refusing it would turn the record of every published model
into dead weight the moment the schema moves.

The registry is an **instance**, not a module-level singleton, so a test can build one containing
a synthetic older version with a real transform. A mechanism with nothing in it is only credible
if it is exercised (research R6).
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

#: The oldest form this build reads: the manifest of features 001 to 005.
PREVIOUS_SCHEMA_VERSION = "caravan/v0"
#: The form of feature 006: declared inputs and outputs, no compliance layer.
CURRENT_SCHEMA_VERSION = "caravan/v0.1"


@dataclass(frozen=True)
class MigrationNotice:
    """One field a migration dropped, moved or added, and why — said once, never silently."""

    path: str
    #: ``dropped``, ``moved`` or ``added``.
    action: str
    reason: str
    #: The new path, for a moved or added field.
    to: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"path": self.path, "action": self.action, "reason": self.reason}
        if self.to is not None:
            out["to"] = self.to
        return out

    def line(self) -> str:
        """The one line ``validate`` prints for it."""
        if self.action == "moved":
            return f"moved {self.path} → {self.to}"
        if self.action == "added":
            return f"added {self.to} — {self.reason}"
        return f"dropped {self.path} — {self.reason}"


#: A transform takes the manifest as a mapping and returns the mapping one version newer, with a
#: notice for every field it dropped, moved or added.
Transform = Callable[[dict[str, Any]], tuple[dict[str, Any], tuple[MigrationNotice, ...]]]


class UnknownSchemaVersion(Exception):
    """The manifest declares a schema version this build does not implement (rule V-1)."""

    def __init__(self, declared: str, known: Sequence[str]) -> None:
        self.declared = declared
        self.known = tuple(known)
        super().__init__(f"unknown schema version {declared!r}; this build implements {self.known}")


@dataclass(frozen=True)
class MigrationResult:
    """What a load needs to record about the version it read (FR-010)."""

    data: dict[str, Any]
    declared: str
    effective: str
    applied: tuple[str, ...] = ()
    version_was_absent: bool = False
    notices: tuple[MigrationNotice, ...] = ()


@dataclass
class SchemaVersionRegistry:
    """Known schema versions, oldest first, and the transform that follows each one.

    ``transforms[v]`` brings a manifest written against ``v`` up to the next version in
    ``versions``. The newest version has no transform.
    """

    versions: tuple[str, ...] = (CURRENT_SCHEMA_VERSION,)
    transforms: Mapping[str, Transform] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.versions:
            raise ValueError("a registry needs at least one schema version")
        unknown = set(self.transforms) - set(self.versions)
        if unknown:
            raise ValueError(f"transforms for unknown versions: {sorted(unknown)}")
        if self.newest in self.transforms:
            raise ValueError(f"the newest version {self.newest!r} must have no transform")

    @property
    def oldest(self) -> str:
        return self.versions[0]

    @property
    def newest(self) -> str:
        return self.versions[-1]

    @property
    def known(self) -> tuple[str, ...]:
        return self.versions

    def migrate(self, data: Mapping[str, Any]) -> MigrationResult:
        """Bring a manifest up to the newest version, in memory, on a copy.

        The caller's mapping is never modified, and neither is the file it came from.
        """
        declared_raw = data.get("apiVersion")
        absent = declared_raw is None
        declared = self.oldest if absent else str(declared_raw)

        if declared not in self.versions:
            raise UnknownSchemaVersion(declared, self.known)

        migrated = copy.deepcopy(dict(data))
        applied: list[str] = []
        notices: list[MigrationNotice] = []
        index = self.versions.index(declared)
        for version in self.versions[index:-1]:
            transform = self.transforms.get(version)
            if transform is None:
                continue
            migrated, said = transform(migrated)
            notices.extend(said)
            applied.append(version)

        migrated["apiVersion"] = self.newest
        return MigrationResult(
            data=migrated,
            declared=declared,
            effective=self.newest,
            applied=tuple(applied),
            version_was_absent=absent,
            notices=tuple(notices),
        )


def migrate_v0_to_v01(
    data: dict[str, Any],
) -> tuple[dict[str, Any], tuple[MigrationNotice, ...]]:
    """``caravan/v0`` → ``caravan/v0.1``, exactly as ``contracts/manifest.md`` (Migration) says.

    A pure mapping transform: no I/O, no framework, so it runs in the core like the rest of loading.
    Fields that were never written produce no notice — a notice reports what changed in *this*
    manifest, not what the schema changed in general.
    """
    from caravan.manifest.schema.removed import (
        BENCHMARK_ONLY_PUBLISH_NOTICE,
        BUDGET_ADDED_NOTICE,
        BY_PATH,
        PREVIOUS_DEFAULT_BUDGET,
    )

    out = copy.deepcopy(data)
    notices: list[MigrationNotice] = []
    model = out.get("model") if isinstance(out.get("model"), dict) else None
    dataset = out.get("dataset") if isinstance(out.get("dataset"), dict) else None
    export = out.get("export") if isinstance(out.get("export"), dict) else None

    def drop(section: dict[str, Any] | None, key: str, path: str, reason: str | None = None):
        if section is not None and key in section:
            value = section.pop(key)
            notices.append(MigrationNotice(path, "dropped", reason or BY_PATH[path].reason))
            return value
        return None

    drop(model, "topic", "model.topic")
    drop(model, "task", "model.task")
    drop(dataset, "license", "dataset.license")
    benchmark_only = (dataset or {}).get("permitted_use") == "benchmark-only" and "publish" in out
    drop(
        dataset,
        "permitted_use",
        "dataset.permitted_use",
        BENCHMARK_ONLY_PUBLISH_NOTICE if benchmark_only else None,
    )
    for section in ("compliance", "verify", "bench", "publish"):
        drop(out, section, section)

    declared_input: dict[str, Any] = {"name": "input", "kind": "series"}
    if dataset is not None and "window" in dataset:
        declared_input["window"] = dataset.pop("window")
        notices.append(
            MigrationNotice(
                "dataset.window", "moved", BY_PATH["dataset.window"].reason, "inputs[0].window"
            )
        )

    declared_output: dict[str, Any] = {"name": "output", "kind": "class", "column": "label"}
    if dataset is not None and "labels" in dataset:
        declared_output["labels"] = dataset.pop("labels")
        notices.append(
            MigrationNotice(
                "dataset.labels", "moved", BY_PATH["dataset.labels"].reason, "outputs[0].labels"
            )
        )
    if export is not None and "accuracy_drop_max" in export:
        declared_output["accuracy_drop_max"] = export.pop("accuracy_drop_max")
        notices.append(
            MigrationNotice(
                "export.accuracy_drop_max",
                "moved",
                BY_PATH["export.accuracy_drop_max"].reason,
                "outputs[0].accuracy_drop_max",
            )
        )
    else:
        declared_output["accuracy_drop_max"] = PREVIOUS_DEFAULT_BUDGET
        notices.append(
            MigrationNotice(
                "export.accuracy_drop_max",
                "added",
                BUDGET_ADDED_NOTICE,
                "outputs[0].accuracy_drop_max",
            )
        )

    out["inputs"] = [declared_input]
    out["outputs"] = [declared_output]
    out["apiVersion"] = CURRENT_SCHEMA_VERSION
    return out, tuple(notices)


def default_registry() -> SchemaVersionRegistry:
    """The versions this build implements, oldest first, with the transform between them."""
    return SchemaVersionRegistry(
        versions=(PREVIOUS_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION),
        transforms={PREVIOUS_SCHEMA_VERSION: migrate_v0_to_v01},
    )
