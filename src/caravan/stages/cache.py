"""The stage cache: the mechanism Principle III's reuse obligation needs.

This is the one place in the feature where being approximately right is the same as being wrong.
A cache that reuses a result it should not have is a silent incorrect answer — not a crash, not a
warning, a model that claims to come from a manifest it does not come from. Hence two choices that
look stricter than necessary:

* the key is computed from a *projection* of the manifest (see ``base.project``), so a stage
  cannot contribute a field it did not declare;
* an entry is inserted by renaming a finished directory into place, so an interrupted run leaves
  no half-written entry to be found later and trusted.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from caravan import __version__
from caravan.manifest.migrate import CURRENT_SCHEMA_VERSION

RESULT_NAME = "result.json"
WORK_DIR_NAME = ".tmp"

OUTCOME_PRODUCED = "produced"
OUTCOME_REUSED = "reused"


def canonical_json(payload: Any) -> str:
    """One text form for one value, so a key depends on the value and not on its formatting."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def cache_key(
    stage: str,
    inputs: Mapping[str, Any],
    *,
    dataset_version: str | None = None,
    upstream_key: str | None = None,
) -> str:
    """The identity of a stage result.

    The tool version is part of it on purpose. A different version of Caravan may build a
    different model from the same manifest, and Principle III makes provenance part of the result
    — so a version bump retrains rather than quietly inheriting the old artifact. At this size
    that costs seconds and buys an honest record.
    """
    payload = {
        "tool": __version__,
        "schema": CURRENT_SCHEMA_VERSION,
        "stage": stage,
        "inputs": dict(inputs),
        "dataset": dataset_version,
        "upstream": upstream_key,
    }
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CacheEntry:
    """A stored stage result, and the record that explains itself."""

    path: Path
    stage: str
    key: str
    artifacts: tuple[str, ...]
    produced_by_run: str | None
    produced_at: str | None
    inputs: dict[str, Any]

    def artifact_paths(self) -> tuple[Path, ...]:
        return tuple(self.path / name for name in self.artifacts)


def entry_dir(cache_dir: Path, stage: str, key: str) -> Path:
    # The key carries its algorithm as a prefix; a colon is not a portable path character.
    return cache_dir / stage / key.replace(":", "-")


def load(cache_dir: Path, stage: str, key: str) -> CacheEntry | None:
    """The stored result for this key, or ``None``.

    A missing, unreadable or incomplete entry is a **miss**, never an error (FR-018). A cache that
    fails a run because its own bookkeeping is damaged is worse than a cache that recomputes.
    """
    path = entry_dir(cache_dir, stage, key)
    record = path / RESULT_NAME
    if not record.is_file():
        return None
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    artifacts = tuple(data.get("artifacts", ()))
    if not artifacts or any(not (path / name).is_file() for name in artifacts):
        return None
    return CacheEntry(
        path=path,
        stage=stage,
        key=key,
        artifacts=artifacts,
        produced_by_run=data.get("produced_by_run"),
        produced_at=data.get("produced_at"),
        inputs=data.get("inputs", {}),
    )


def new_work_dir(cache_dir: Path, stage: str) -> Path:
    """A private directory for a stage to write into before anything is published.

    Beside the cache rather than in the system temporary directory, so that publishing an entry is
    a rename on one filesystem rather than a copy across two.
    """
    work = cache_dir / WORK_DIR_NAME / f"{stage}-{uuid.uuid4().hex}"
    work.mkdir(parents=True, exist_ok=False)
    return work


def insert(
    cache_dir: Path,
    stage: str,
    key: str,
    work: Path,
    *,
    artifacts: tuple[str, ...],
    inputs: Mapping[str, Any],
    dataset_version: str | None,
    upstream_key: str | None,
    run_id: str | None,
) -> CacheEntry:
    """Publish a finished work directory as the entry for this key.

    A stage that did not write an artifact it declared is a defect in the stage, not a cache miss,
    so it raises here rather than storing a partial entry: the constitution's stage contract says
    a stage declares what it writes, and a declaration that is not kept has to be loud.
    """
    missing = [name for name in artifacts if not (work / name).is_file()]
    if missing:
        raise RuntimeError(
            f"stage {stage!r} declared artifacts it did not write: {', '.join(sorted(missing))}"
        )

    record = {
        "stage": stage,
        "key": key,
        "artifacts": list(artifacts),
        "inputs": dict(inputs),
        "dataset_version": dataset_version,
        "upstream_key": upstream_key,
        "tool": __version__,
        "produced_by_run": run_id,
        "produced_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (work / RESULT_NAME).write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    target = entry_dir(cache_dir, stage, key)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        # Only reachable under --fresh, or if two runs raced to the same key. Either way the
        # content is a recomputation of the same inputs, so replacing it changes nothing but the
        # timestamp.
        shutil.rmtree(target)
    os.replace(work, target)

    entry = load(cache_dir, stage, key)
    if entry is None:  # pragma: no cover - the rename just succeeded
        raise RuntimeError(f"the cache entry for {stage!r} could not be read back")
    return entry


def copy_into_run(entry: CacheEntry, run_dir: Path) -> tuple[str, ...]:
    """Copy an entry's artifacts into a run directory.

    Copied, never linked and never referenced. A run directory has to be complete on its own: a
    report that pointed into the cache would stop being readable the moment the cache was cleaned,
    and a hard link would let a later run mutate a cached artifact through it.
    """
    for name in entry.artifacts:
        destination = run_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(entry.path / name, destination)
    return entry.artifacts
