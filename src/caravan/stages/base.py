"""What a stage is, what it may read, and how a stage is run.

The important idea is small: a stage declares the manifest fields it reads, and the runner hands
it a **projection** containing exactly those fields and nothing else. "The fields this stage
reads" is then true by construction rather than by review — the declaration is the only access
path, so it cannot drift from the code the way a comment would (research R7).

Everything here is core. A stage whose work needs a training framework loads it by name inside its
own function, so importing a stage module never imports a framework.
"""

from __future__ import annotations

import re
import shutil
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caravan.run.report import StageOutcome
from caravan.stages import cache as cache_module
from caravan.stages.cache import OUTCOME_PRODUCED, OUTCOME_REUSED

#: What a stage receives: dotted manifest path -> value. Nothing else reaches a stage.
StageInputs = Mapping[str, Any]

#: What a stage does: write its declared artifacts into the directory it is given.
StageFunction = Callable[[StageInputs, Path], None]


@dataclass
class StageContext:
    """What a stage needs that is not a manifest field, and a dataset read at most once.

    It deliberately carries no manifest values. Letting a stage reach the manifest through here
    would defeat the projection, which is the whole mechanism: a stage sees the fields it declared
    and nothing else. What it does carry is the *resolved dataset* — files and a version, not a
    manifest field — and a lazy reader, so that one invocation of ``caravan train`` reads the data
    once even though two stages need it, and a reused build reads it not at all.
    """

    dataset: Any
    #: Where this run's artifacts land. A stage reads the previous stage's artifacts from here,
    #: which is what makes the constitution's "resumable from the artifacts of the stage before
    #: it" true for a reused result as much as for a fresh one.
    run_dir: Path
    run_id: str | None = None
    #: The input's columns as declared, or ``None`` for every column but the output's. Not a manifest
    #: value reaching a stage: it decides how the data is *read*, which every stage reading the data
    #: needs identically, and the ``data`` stage records what it produced (feature 006).
    input_columns: tuple[str, ...] | None = None
    output_column: str = "label"
    _records: Any = None

    @property
    def records_if_read(self) -> Any:
        """What has been read so far, without reading anything. ``None`` until first use."""
        return self._records

    def records(self) -> Any:
        """Every record, read on first use. Imports the reader, so never called by the core."""
        if self._records is None:
            from caravan.data.reader import read_records

            self._records = read_records(
                self.dataset, input_columns=self.input_columns, output_column=self.output_column
            )
        return self._records


class DeclarationError(Exception):
    """A stage declared a manifest field that does not exist. A bug in the stage, not in input."""


@dataclass(frozen=True)
class StageSpec:
    """A stage, as the constitution's pipeline contract requires it to declare itself."""

    name: str
    #: Dotted paths into the resolved manifest. The stage receives these and only these.
    reads: tuple[str, ...]
    #: Whether the dataset's content is an input to the result, and so part of the key.
    reads_dataset: bool
    #: The stage whose key this one's key is derived from, if any.
    upstream: str | None
    #: Relative paths this stage writes. A declared artifact that is not written is an error.
    artifacts: tuple[str, ...]
    #: Further artifacts whose *names* depend on the manifest — one runner skeleton per target
    #: board, say. Computed from the projection and from nothing else, so the declaration stays a
    #: declaration: a stage cannot name a file by reading a field it did not declare. Everything
    #: this returns is held to the same contract as ``artifacts``, including the check that a
    #: declared artifact which was not written is a defect.
    artifacts_from: Callable[[StageInputs], tuple[str, ...]] | None = None

    def declared_artifacts(self, inputs: StageInputs) -> tuple[str, ...]:
        """Everything this stage promises to write for these inputs."""
        if self.artifacts_from is None:
            return self.artifacts
        return (*self.artifacts, *self.artifacts_from(inputs))


#: One step of a projection path: a key, optionally followed by an index — ``outputs[0]``.
_STEP = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)(?:\[(?P<index>\d+)\])?$")


def _step(current: Any, part: str) -> Any:
    match = _STEP.match(part)
    if match is None or not isinstance(current, Mapping) or match["key"] not in current:
        raise KeyError(part)
    current = current[match["key"]]
    if match["index"] is not None:
        index = int(match["index"])
        if not isinstance(current, list) or index >= len(current):
            raise KeyError(part)
        current = current[index]
    return current


def project(resolved: Mapping[str, Any], spec: StageSpec) -> dict[str, Any]:
    """Build a stage's inputs from its declaration.

    A path may index a list, ``outputs[0].labels``, so a stage reads one field of a declaration
    rather than the whole list: a budget change must not touch the key of a stage that does not
    read the budget (Principle III, feature 006 FR-031).

    A path the resolved manifest does not have raises: a stage that declares a field which does
    not exist is a defect to find at the first test, not a key that quietly includes ``None``.
    """
    inputs: dict[str, Any] = {}
    for path in spec.reads:
        current: Any = resolved
        try:
            for part in path.split("."):
                current = _step(current, part)
        except KeyError:
            raise DeclarationError(
                f"stage {spec.name!r} declares it reads {path!r}, which the resolved "
                "manifest does not contain"
            ) from None
        inputs[path] = current
    return inputs


def run_stage(
    spec: StageSpec,
    stage_fn: StageFunction,
    *,
    resolved: Mapping[str, Any],
    run_dir: Path,
    cache_dir: Path,
    dataset_version: str | None = None,
    upstream_key: str | None = None,
    fresh: bool = False,
    run_id: str | None = None,
) -> StageOutcome:
    """Produce the stage's result, or reuse the stored one, and say which happened.

    The stage writes into a private directory that is only published once it has finished. That is
    what makes FR-012 hold without the stage having to clean up after itself: a run that fails,
    diverges or is interrupted leaves no artifact anywhere, because nothing was ever moved into
    place.
    """
    inputs = project(resolved, spec)
    key = cache_module.cache_key(
        spec.name,
        inputs,
        dataset_version=dataset_version if spec.reads_dataset else None,
        upstream_key=upstream_key,
    )

    if not fresh:
        entry = cache_module.load(cache_dir, spec.name, key)
        if entry is not None:
            started = time.perf_counter()
            artifacts = cache_module.copy_into_run(entry, run_dir)
            return StageOutcome(
                name=spec.name,
                outcome=OUTCOME_REUSED,
                key=key,
                artifacts=artifacts,
                upstream_key=upstream_key,
                produced_by_run=entry.produced_by_run,
                duration_s=time.perf_counter() - started,
                fresh=False,
            )

    work = cache_module.new_work_dir(cache_dir, spec.name)
    started = time.perf_counter()
    try:
        stage_fn(inputs, work)
        entry = cache_module.insert(
            cache_dir,
            spec.name,
            key,
            work,
            artifacts=spec.declared_artifacts(inputs),
            inputs=inputs,
            dataset_version=dataset_version if spec.reads_dataset else None,
            upstream_key=upstream_key,
            run_id=run_id,
        )
    except BaseException:
        # Includes KeyboardInterrupt on purpose: an interrupted run must leave no artifact
        # either, and "interrupted" is the case a user is most likely to meet.
        shutil.rmtree(work, ignore_errors=True)
        raise
    duration = time.perf_counter() - started

    artifacts = cache_module.copy_into_run(entry, run_dir)
    return StageOutcome(
        name=spec.name,
        outcome=OUTCOME_PRODUCED,
        key=key,
        artifacts=artifacts,
        upstream_key=upstream_key,
        produced_by_run=run_id,
        duration_s=duration,
        fresh=fresh,
    )
