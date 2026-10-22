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


@dataclass
class Report:
    """One invocation, as it will be written to ``report.json``."""

    command: str
    manifest_path: str
    manifest_sha256: str
    outcome: str
    schema_version_declared: str | None = None
    schema_version_effective: str | None = None
    migrations_applied: tuple[str, ...] = ()
    dataset: str | None = None
    template: str | None = None
    gates: Sequence[Gate] = field(default_factory=tuple)
    findings: Sequence[Finding] = field(default_factory=tuple)
    unresolved: Sequence[Unresolved] = field(default_factory=tuple)
    artifacts: dict[str, str] = field(default_factory=dict)
    seed: int | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, Any]:
        """The contract's field order, which is also the order a reader wants it in."""
        return {
            "caravan_version": __version__,
            "command": self.command,
            "started_at": self.started_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "dataset": self.dataset,
            "template": self.template,
            "schema_version_declared": self.schema_version_declared,
            "schema_version_effective": self.schema_version_effective,
            "migrations_applied": list(self.migrations_applied),
            "outcome": self.outcome,
            "gates": [gate.as_dict() for gate in self.gates],
            "findings": [finding.as_dict() for finding in self.findings],
            "unresolved": [item.as_dict() for item in self.unresolved],
            "artifacts": dict(self.artifacts),
            "seed": self.seed,
        }

    def as_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, ensure_ascii=False) + "\n"


def write_report(run_dir: Path, report: Report) -> Path:
    path = run_dir / REPORT_NAME
    path.write_text(report.as_json(), encoding="utf-8")
    return path
