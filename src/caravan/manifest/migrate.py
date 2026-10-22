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

#: A transform takes the manifest as a mapping and returns the mapping one version newer.
Transform = Callable[[dict[str, Any]], dict[str, Any]]

CURRENT_SCHEMA_VERSION = "caravan/v0"


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
        index = self.versions.index(declared)
        for version in self.versions[index:-1]:
            transform = self.transforms.get(version)
            if transform is None:
                continue
            migrated = transform(migrated)
            applied.append(version)

        migrated["apiVersion"] = self.newest
        return MigrationResult(
            data=migrated,
            declared=declared,
            effective=self.newest,
            applied=tuple(applied),
            version_was_absent=absent,
        )


def default_registry() -> SchemaVersionRegistry:
    """The versions this build implements: one, with nothing to migrate yet."""
    return SchemaVersionRegistry(versions=(CURRENT_SCHEMA_VERSION,), transforms={})
