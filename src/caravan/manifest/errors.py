"""Findings, rule identifiers and the one place that turns them into text.

Every rule in ``specs/001-manifest-schema/data-model.md`` has an identifier here, and the
identifier travels all the way out: into the finding, into the JSON output, into the run report
and into the name of the fixture that pins it. A test can then assert *which* rule fired instead
of matching prose.
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, NoReturn

from pydantic_core import PydanticCustomError

# --- Rules that reject a manifest -------------------------------------------------------------
RULE_UNKNOWN_SCHEMA_VERSION = "V-1"
RULE_UNKNOWN_TEMPLATE = "T-1"
RULE_TEMPLATE_PARAMETERS = "T-2"
RULE_UNKNOWN_BOARD = "B-1"
RULE_SPLIT_SUM = "CF-1"
RULE_DUPLICATE_TARGETS = "CF-2"
RULE_PERSONAL_DATA_RISK_CLASS = "CF-3"
RULE_CALIBRATION_SAMPLES = "CF-4"
RULE_WINDOW_MATCHES_TEMPLATE = "CF-6"
RULE_EMULATOR_EXISTS = "CF-7"
RULE_PUBLISH_BENCHMARK_ONLY = "CF-8"

#: Rules that can refuse a manifest. Every one of these must have an invalid manifest fixture,
#: and ``tests/unit/test_fixture_coverage.py`` fails when one does not.
MANIFEST_REJECTION_RULES: frozenset[str] = frozenset(
    {
        RULE_UNKNOWN_SCHEMA_VERSION,
        RULE_UNKNOWN_TEMPLATE,
        RULE_TEMPLATE_PARAMETERS,
        RULE_UNKNOWN_BOARD,
        RULE_SPLIT_SUM,
        RULE_DUPLICATE_TARGETS,
        RULE_PERSONAL_DATA_RISK_CLASS,
        RULE_CALIBRATION_SAMPLES,
        RULE_WINDOW_MATCHES_TEMPLATE,
        RULE_EMULATOR_EXISTS,
        RULE_PUBLISH_BENCHMARK_ONLY,
    }
)

# --- Rules that are entailed by the schema itself, and can therefore never fire ---------------
RULE_PUBLISH_NEEDS_COMPLIANCE = "CF-5"

#: CF-5 ("publication requires a complete compliance block") turned out to be *entailed* once the
#: schema was written: ``compliance`` is required for every manifest, whether or not ``publish`` is
#: present, and each of its fields already rejects an empty value. There is no state in which a
#: manifest passes the compliance section and still fails CF-5, so it is not a runtime rule and
#: can have no fixture. FR-016 is satisfied structurally, by FR-015 plus the field constraints —
#: which is a stronger guarantee than a cross-field check, not a weaker one.
ENTAILED_RULES: frozenset[str] = frozenset({RULE_PUBLISH_NEEDS_COMPLIANCE})

# --- Rules that reject a board description, never a manifest ----------------------------------
RULE_EMULATOR_STATED = "E-1"
RULE_SOURCES_COVERAGE = "S-1"

#: Board-file rules. They cannot appear in the manifest fixture library, which is why they have
#: their own fixtures under ``tests/fixtures/boards`` and their own test.
BOARD_RULES: frozenset[str] = frozenset({RULE_EMULATOR_STATED, RULE_SOURCES_COVERAGE})

# --- Identifiers that never reject anything ---------------------------------------------------
RULE_NO_SCHEMA_VERSION = "V-2"
RULE_DATASET_UNRESOLVED = "D-1"

#: Informational identifiers: V-2 accepts a manifest that declares no version, D-1 records a
#: reference that was deliberately not resolved. Neither may have an invalid fixture.
INFORMATIONAL_RULES: frozenset[str] = frozenset({RULE_NO_SCHEMA_VERSION, RULE_DATASET_UNRESOLVED})

ALL_RULES: frozenset[str] = (
    MANIFEST_REJECTION_RULES | BOARD_RULES | INFORMATIONAL_RULES | ENTAILED_RULES
)


def rule_error(
    rule: str,
    path: str,
    problem: str,
    *,
    found: Any = None,
    accepted: Sequence[str] = (),
) -> NoReturn:
    """Fail validation with a finding that keeps its rule identifier and its field path.

    Raising from inside a validator is how a rule identifier travels out of the schema untouched,
    so the command line, the JSON output and the run report can all name the rule that fired
    rather than describe it in prose.
    """
    raise PydanticCustomError(
        rule,
        "{problem}",
        {"problem": problem, "path": path, "found": found, "accepted": list(accepted)},
    )


@dataclass(frozen=True)
class Finding:
    """One thing that is wrong, in the form FR-002 requires."""

    path: str
    problem: str
    found: Any = None
    accepted: tuple[str, ...] = ()
    rule: str | None = None
    belongs_at: str | None = None
    #: The name to measure a did-you-mean suggestion against, when it is not the found value —
    #: an unknown field's own name, for instance, which the path already shows.
    near: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"path": self.path, "problem": self.problem}
        if self.found is not None:
            out["found"] = self.found
        if self.accepted:
            out["accepted"] = list(self.accepted)
        if self.belongs_at:
            out["belongs_at"] = self.belongs_at
        if self.rule:
            out["rule"] = self.rule
        return out


@dataclass
class Unresolved:
    """Something deliberately not checked, recorded so silence is visible as silence."""

    kind: str
    value: Any
    reason: str
    rule: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out = {"kind": self.kind, "value": self.value, "reason": self.reason}
        if self.rule:
            out["rule"] = self.rule
        return out


@dataclass
class Gate:
    """One rule group that was reached, with its outcome."""

    name: str
    result: str
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out = {"name": self.name, "result": self.result}
        if self.detail:
            out["detail"] = self.detail
        return out


def dotted_path(location: Sequence[Any]) -> str:
    """Format a validation location the way every message and finding shows it."""
    out = ""
    for part in location:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out = f"{out}.{part}" if out else str(part)
    return out or "(document)"


def suggest(name: str, candidates: tuple[str, ...]) -> str | None:
    """The nearest accepted name, when it is near enough to be worth printing."""
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=0.7)
    return matches[0] if matches else None


def render_finding(document: str, finding: Finding) -> str:
    """Render one finding in the three-part form of ``contracts/cli.md``.

    Field path first, then what was wrong, then what is accepted. Never a library type name, a
    module path or a traceback — those belong to exit code 3 alone.
    """
    found = "" if finding.found is None else f", found {finding.found!r}"
    lines = [f"{document}: {finding.path} — {finding.problem}{found}"]
    if finding.accepted:
        label = "accepted here" if finding.rule is None else "accepted"
        lines.append(f"    {label}: {', '.join(finding.accepted)}")
        subject = finding.near if finding.near is not None else finding.found
        hint = suggest(str(subject), finding.accepted) if subject is not None else None
        if hint:
            lines.append(f"    did you mean: {hint}")
    if finding.belongs_at:
        lines.append(f"    this field belongs at: {finding.belongs_at}")
    return "\n".join(lines)


def render_document_error(document: str, problem: str, location: str | None = None) -> str:
    where = f" ({location})" if location else ""
    return f"{document}: {problem}{where}"


@dataclass
class Findings:
    """A collection that keeps the order rules fired in."""

    items: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.items.append(finding)

    def __bool__(self) -> bool:
        return bool(self.items)

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)
