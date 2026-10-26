"""What the export wrote, and what a firmware author still has to supply.

Every artifact carries its size and its digest, so a report is enough to tell whether the file
beside it is the file the run produced. Every figure carries where it came from — and the one
figure that is a *computed* bound carries, in words, what it leaves out. That last field is a
sentence and not a flag because what has to reach the reader is the sentence; a boolean would make
them look it up, and nobody looks it up.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: The sentence that travels with the working-memory floor wherever it is recorded.
FLOOR_CAVEAT = (
    "a floor, not the figure this model needs on a target: the runtime also needs scratch "
    "buffers and its own bookkeeping, and it plans the whole arena with its own allocator on "
    "the device. The figure a board requires is established by emulated verification, or by the "
    "runner's own report of the arena the runtime used, measured on the board (feature 009)."
)


@dataclass(frozen=True)
class Artifact:
    """One written file."""

    path: str
    bytes: int
    digest: str
    format: str
    target: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "path": self.path,
            "bytes": self.bytes,
            "digest": self.digest,
            "format": self.format,
        }
        if self.target is not None:
            out["target"] = self.target
        return out


def record_artifact(
    root: Path, relative: str, *, format: str, target: str | None = None
) -> Artifact:
    """Measure and digest a file that has just been written."""
    path = root / relative
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return Artifact(
        path=relative,
        bytes=path.stat().st_size,
        digest=f"sha256:{digest}",
        format=format,
        target=target,
    )


@dataclass(frozen=True)
class RunnerRequirements:
    """The answer to "what do I need to run this?", with the provenance of each part."""

    runtime: str
    operators: tuple[str, ...]
    working_memory_floor: int
    floor_method: str
    floor_is_not_the_requirement: str = FLOOR_CAVEAT

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime": self.runtime,
            "operators": list(self.operators),
            "working_memory_floor_bytes": self.working_memory_floor,
            "floor_method": self.floor_method,
            "floor_is_not_the_requirement": self.floor_is_not_the_requirement,
        }


@dataclass
class ExportSet:
    """Everything one export produced, as the report records it."""

    artifacts: list[Artifact] = field(default_factory=list)
    formats: tuple[str, ...] = ()
    graph: Any = None
    coverage: tuple[Any, ...] = ()
    requirements: dict[str, RunnerRequirements] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "formats": list(self.formats),
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "graph": self.graph.as_dict() if self.graph is not None else {},
            "coverage": [verdict.as_dict() for verdict in self.coverage],
            "requirements": {
                target: requirement.as_dict() for target, requirement in self.requirements.items()
            },
        }
