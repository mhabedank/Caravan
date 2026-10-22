"""Which operators an accelerated kernel library supplies, as data with a source and a date.

A board description saying ``accel: cmsis-nn`` is a claim about the build, not about the model:
acceleration is chosen per operator, and an operator with no accelerated kernel falls back to the
reference implementation without announcing it (Principle VII). So the export records, per operator
and per target, which side of that line it falls on.

What a verdict claims is deliberately the weaker of two readings: *the library supplies a kernel for
this operator*. Not *this kernel will be selected* — that can depend on operand shapes and build
flags, and settling it needs the toolchain this stage does not have. And not *this will be faster*,
which is a measurement and not a lookup.

The libraries are data beside the board descriptions because they are the same kind of thing: a
claim about hardware that somebody had to read a source for.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from caravan.manifest._yaml import read_mapping

#: What a board's ``accel`` field says when there is nothing to accelerate with.
NO_LIBRARY = "none"


@dataclass(frozen=True)
class KernelLibrary:
    """One accelerated library: the operators it covers, and where that was read."""

    library: str
    runtime: str
    operators: dict[str, str]
    source: str
    read_on: str
    unmapped: tuple[str, ...]

    def evidence_for(self, operator: str) -> str | None:
        """The source file that supplies this operator's kernel, or ``None``."""
        return self.operators.get(operator)


@dataclass(frozen=True)
class CoverageVerdict:
    """One operator against one target: accelerated or falling back, and on whose word."""

    target: str
    operator: str
    library: str | None
    accelerated: bool
    evidence: str
    source: str
    read_on: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "operator": self.operator,
            "library": self.library,
            "accelerated": self.accelerated,
            "evidence": self.evidence,
            "source": self.source,
            "read_on": self.read_on,
        }


def load_library(path: Path) -> KernelLibrary:
    data = read_mapping(path)
    operators = {str(name): str(file) for name, file in (data.get("operators") or {}).items()}
    return KernelLibrary(
        library=str(data["library"]),
        runtime=str(data["runtime"]),
        operators=operators,
        source=str(data["source"]),
        read_on=str(data["read_on"]),
        unmapped=tuple(str(name) for name in (data.get("unmapped") or ())),
    )


def load_directory(directory: Path) -> dict[str, KernelLibrary]:
    libraries: dict[str, KernelLibrary] = {}
    for path in sorted(directory.glob("*.yaml")):
        library = load_library(path)
        if library.library != path.stem:
            raise ValueError(
                f"{path}: the library identifier {library.library!r} must equal the file name"
            )
        libraries[library.library] = library
    return libraries


@lru_cache(maxsize=1)
def default_libraries() -> dict[str, KernelLibrary]:
    """The accelerated libraries this build ships data for."""
    resource = files("caravan.targets").joinpath("kernels")
    with as_file(resource) as directory:
        return load_directory(Path(directory))


def coverage(
    operators: Sequence[Any],
    board: Any,
    libraries: dict[str, KernelLibrary] | None = None,
) -> tuple[CoverageVerdict, ...]:
    """One verdict per operator for one board. Three outcomes, and they are three.

    A board declaring no accelerated library produces a *stated* verdict for every operator —
    nothing is accelerated there — rather than an absent one. "We do not know" printed beside an
    operator is the silence Principle IV exists against, and here there is nothing unknown about it.

    A board declaring a library caravan has no data for cannot happen: the board schema admits
    ``accel`` only from a closed list, and every board file is validated when it is loaded. A test
    pairs that list with the data files, so a library added without reading a source for it fails in
    continuous integration rather than in somebody's run. Rule X-5 was written for this case and
    withdrawn when it turned out to be unreachable.
    """
    known = default_libraries() if libraries is None else libraries
    declared = board.accel
    if declared == NO_LIBRARY:
        return tuple(
            CoverageVerdict(
                target=board.board,
                operator=operator.name,
                library=None,
                accelerated=False,
                evidence="this board declares no accelerated kernel library",
                source=f"board description {board.board}",
                read_on=board.sources.get("accel", ""),
            )
            for operator in operators
        )

    library = known[declared]
    verdicts = []
    for operator in operators:
        evidence = library.evidence_for(operator.name)
        verdicts.append(
            CoverageVerdict(
                target=board.board,
                operator=operator.name,
                library=library.library,
                accelerated=evidence is not None,
                evidence=(
                    evidence
                    if evidence is not None
                    else (
                        f"{library.library} supplies no kernel for {operator.name}; the runtime's "
                        "reference implementation is used"
                    )
                ),
                source=library.source,
                read_on=library.read_on,
            )
        )
    return tuple(verdicts)
