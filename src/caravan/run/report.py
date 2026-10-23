"""The run report: the machine-readable record of one invocation.

Principle III requires every artifact to carry a provenance record, and names the dataset and the
template identifiers in it. Both are therefore fields of their own here, not something a reader
has to dig out of a gate's detail string.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from caravan import __version__
from caravan.manifest.errors import Finding, Gate, Unresolved
from caravan.run.paths import REPORT_NAME

OUTCOME_VALID = "valid"
OUTCOME_INVALID = "invalid"
OUTCOME_ERROR = "error"

#: The splits a quality metric may be measured on. ``train`` is absent on purpose (FR-006a): a
#: number from data the model fitted is not evidence, and printing it beside the others invites
#: exactly the comparison it cannot support.
MEASURABLE_SPLITS = ("val", "test")


class IncompleteMetric(ValueError):
    """A metric that does not say what it was measured against. Never written, always a defect."""


@dataclass(frozen=True)
class QualityMetric:
    """A number about the model, inseparable from what produced it (FR-007).

    The checks are in ``__post_init__`` rather than in the writer, so an incomplete metric cannot
    be constructed at all — there is no path from a computation to the report that skips them.
    That is the whole mechanism behind SC-003: not a convention the writer follows, but a value
    that cannot exist without its provenance.
    """

    name: str
    value: float | dict[str, float]
    split: str
    dataset_version: str
    samples: int

    def __post_init__(self) -> None:
        if not self.name:
            raise IncompleteMetric("a metric must have a name")
        if self.split not in MEASURABLE_SPLITS:
            raise IncompleteMetric(
                f"{self.name}: split must be one of {', '.join(MEASURABLE_SPLITS)}, "
                f"not {self.split!r} — a metric measured on the training split is not evidence"
            )
        if not self.dataset_version:
            raise IncompleteMetric(
                f"{self.name}: a metric must name the dataset version it was measured against"
            )
        if self.samples <= 0:
            raise IncompleteMetric(
                f"{self.name}: a metric must say how many samples it is over, and over zero "
                "samples there is no metric"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "split": self.split,
            "dataset_version": self.dataset_version,
            "samples": self.samples,
        }


@dataclass(frozen=True)
class ConfusionMatrix:
    """The matrix every other classification metric is derived from."""

    labels: tuple[str, ...]
    rows: tuple[tuple[int, ...], ...]
    split: str
    dataset_version: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "labels": list(self.labels),
            "split": self.split,
            "dataset_version": self.dataset_version,
            "rows": [list(row) for row in self.rows],
        }


@dataclass
class StageOutcome:
    """What one stage did, and on what key it decided (FR-016)."""

    name: str
    outcome: str
    key: str
    artifacts: tuple[str, ...] = ()
    upstream_key: str | None = None
    produced_by_run: str | None = None
    duration_s: float | None = None
    fresh: bool = False

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "outcome": self.outcome, "key": self.key}
        if self.upstream_key:
            out["upstream_key"] = self.upstream_key
        if self.produced_by_run:
            out["produced_by_run"] = self.produced_by_run
        if self.duration_s is not None:
            out["duration_s"] = round(self.duration_s, 3)
        out["fresh"] = self.fresh
        out["artifacts"] = list(self.artifacts)
        return out


@dataclass
class Report:
    """One invocation, as it will be written to ``report.json``."""

    command: str
    manifest_path: str
    manifest_sha256: str
    outcome: str
    #: The ``apiVersion`` the manifest declares, as written. Nothing is migrated before 1.0.0
    #: (constitution 4.0.0, Principle IX), so the declared version is the one that was read.
    schema_version: str | None = None
    dataset: str | None = None
    template: str | None = None
    gates: Sequence[Gate] = field(default_factory=tuple)
    findings: Sequence[Finding] = field(default_factory=tuple)
    unresolved: Sequence[Unresolved] = field(default_factory=tuple)
    artifacts: dict[str, str] = field(default_factory=dict)
    seed: int | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    # --- added by feature 002; absent from a validate or render report -----------------------
    stages: Sequence[StageOutcome] = field(default_factory=tuple)
    dataset_resolved: dict[str, Any] | None = None
    training: dict[str, Any] | None = None
    metrics: Sequence[QualityMetric] = field(default_factory=tuple)
    confusion_matrix: ConfusionMatrix | None = None
    # --- added by feature 003 -----------------------------------------------------------------
    #: The whole quantization record, as the stage's own artifact carries it — so a reused result
    #: reports the same numbers as the run that produced it, and a failed gate reports them too.
    quantization: dict[str, Any] | None = None
    # --- added by feature 006 -----------------------------------------------------------------
    #: What the data stage found: the input's columns, the labels, and where each came from.
    data: dict[str, Any] | None = None
    #: The fit check before training: estimated lower bounds against every target board.
    fit: dict[str, Any] | None = None
    #: The interface contract the export wrote.
    interface: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        """The contract's field order, which is also the order a reader wants it in."""
        out: dict[str, Any] = {
            "caravan_version": __version__,
            "command": self.command,
            "started_at": self.started_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "dataset": self.dataset,
            "template": self.template,
            "schema_version": self.schema_version,
            "outcome": self.outcome,
            "gates": [gate.as_dict() for gate in self.gates],
            "findings": [finding.as_dict() for finding in self.findings],
            "unresolved": [item.as_dict() for item in self.unresolved],
            "artifacts": dict(self.artifacts),
            "seed": self.seed,
        }
        # Sections of feature 002. A validate or render report does not carry them at all, rather
        # than carrying them empty: an absent section says "this command has no stages", where an
        # empty one would say "it ran none".
        if self.stages:
            out["stages"] = [stage.as_dict() for stage in self.stages]
        if self.dataset_resolved is not None:
            out["dataset_resolved"] = self.dataset_resolved
        if self.training is not None:
            out["training"] = self.training
        if self.metrics:
            out["metrics"] = [metric.as_dict() for metric in self.metrics]
        if self.confusion_matrix is not None:
            out["confusion_matrix"] = self.confusion_matrix.as_dict()
        if self.quantization is not None:
            out["quantization"] = self.quantization
        if self.data is not None:
            out["data"] = self.data
        if self.fit is not None:
            out["fit"] = self.fit
        if self.interface is not None:
            out["interface"] = self.interface
        return out

    def as_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, ensure_ascii=False) + "\n"


def write_report(run_dir: Path, report: Report) -> Path:
    path = run_dir / REPORT_NAME
    path.write_text(report.as_json(), encoding="utf-8")
    return path
