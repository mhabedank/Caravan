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
RULE_CALIBRATION_SAMPLES = "CF-4"
RULE_WINDOW_MATCHES_TEMPLATE = "CF-6"
#: A declaration name breaks the form ``[a-z][a-z0-9_]{0,31}``, or two declarations share one: the
#: name is what a runner binds by, in C as much as in the model's signature (feature 006).
RULE_DECLARATION_NAME = "CF-9"
#: More than one input or output, or a kind this build does not implement. Several inputs and
#: outputs wait for the first named model or documented application that needs them (Principle X).
RULE_DECLARATIONS_IMPLEMENTED = "CF-10"
#: A column named by the input is the output's column: a model would be trained on its own answer.
RULE_COLUMN_BOTH_WAYS = "CF-11"

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
        RULE_CALIBRATION_SAMPLES,
        RULE_WINDOW_MATCHES_TEMPLATE,
        RULE_DECLARATION_NAME,
        RULE_DECLARATIONS_IMPLEMENTED,
        RULE_COLUMN_BOTH_WAYS,
    }
)

# --- Rules that reject a run, never a manifest ------------------------------------------------
# The manifest can be perfectly valid and the data still disagree with it. These fire when a stage
# resolves the dataset, so they cannot have an invalid-manifest fixture; they build their bad data
# in a temporary directory instead (FR-013 — only one dataset is ever committed).
RULE_DATASET_UNREADABLE = "DS-1"
RULE_DATASET_COLUMNS = "DS-2"
RULE_DATASET_HEADERS_DIFFER = "DS-3"
RULE_DATASET_CELL = "DS-4"
RULE_DATASET_LABELS = "DS-5"
RULE_DATASET_NO_SAMPLES = "DS-6"
RULE_DATASET_FEATURE_WIDTH = "DS-7"
RULE_SPLIT_EMPTY = "DS-8"
RULE_TRAINING_DIVERGED = "DS-10"
#: The output column holds fewer than two distinct values: there is nothing to classify.
RULE_TOO_FEW_CLASSES = "DS-11"
#: The input names a column the data does not have.
RULE_UNKNOWN_INPUT_COLUMN = "DS-12"

#: Run rules. Every one of these must have a test that provokes it, and
#: ``tests/unit/test_run_rules_coverage.py`` fails when one does not. DS-7 is deliberately absent:
#: see ``ENTAILED_RULES`` below.
RUN_RULES: frozenset[str] = frozenset(
    {
        RULE_DATASET_UNREADABLE,
        RULE_DATASET_COLUMNS,
        RULE_DATASET_HEADERS_DIFFER,
        RULE_DATASET_CELL,
        RULE_DATASET_LABELS,
        RULE_DATASET_NO_SAMPLES,
        RULE_SPLIT_EMPTY,
        RULE_TRAINING_DIVERGED,
        RULE_TOO_FEW_CLASSES,
        RULE_UNKNOWN_INPUT_COLUMN,
    }
)

# --- Rules that are entailed by the schema itself, and can therefore never fire ---------------
#: DS-7 ("the feature width disagrees with what the manifest's window implies") was withdrawn
#: during the analysis pass of feature 002, for the same reason as CF-5: it is unreachable. The
#: manifest declares no feature width — the width comes from the data (FR-004) — so there is
#: nothing for the data to disagree with. Two files that disagree with *each other* are DS-3, and
#: too few records for one window is DS-6. The identifier stays reserved rather than renumbering
#: DS-8 and DS-9, and lives here so the coverage test does not demand a test for it.
#: Defined here rather than with the other X identifiers because it is used here, and a forward
#: reference would be a worse trade than a comment: this is the export rule that refuses nothing.
RULE_KERNEL_COVERAGE_UNKNOWN = "X-5"

#: X-5 joins them for the same kind of reason, found while implementing feature 004 rather than
#: while planning it. It was meant to refuse a board naming an accelerated library caravan has no
#: sourced coverage data for — but the board schema admits ``accel`` only from a closed list, and
#: ``load_directory`` validates every file it reads, so no board description can ever carry a
#: library that is not in that list. The protection is better placed anyway: a test pairs the
#: schema's list with the data files, so adding a library without reading a source for it fails in
#: continuous integration rather than in somebody's run. The identifier stays reserved rather than
#: renumbering the rules that are reachable.
ENTAILED_RULES: frozenset[str] = frozenset(
    {RULE_DATASET_FEATURE_WIDTH, RULE_KERNEL_COVERAGE_UNKNOWN}
)

# --- Rules that reject a board description, never a manifest ----------------------------------
RULE_EMULATOR_STATED = "E-1"
RULE_SOURCES_COVERAGE = "S-1"

#: Board-file rules. They cannot appear in the manifest fixture library, which is why they have
#: their own fixtures under ``tests/fixtures/boards`` and their own test.
BOARD_RULES: frozenset[str] = frozenset({RULE_EMULATOR_STATED, RULE_SOURCES_COVERAGE})

# --- Rules that reject a run at the quantization stage ------------------------------------------
# Q-4 is the project's first *budget* refusing a run rather than a schema rule: the manifest's
# accuracy threshold said no. It travels as a finding like any other rule, and as a Gate entry in
# the report, because it is one event seen by a person and by a machine.
RULE_TRAINED_MODEL_UNREADABLE = "Q-1"
RULE_CONVERSION_FAILED = "Q-2"
RULE_NOT_FULLY_QUANTIZED = "Q-3"
RULE_ACCURACY_GATE = "Q-4"
RULE_GATE_UNMEASURABLE = "Q-5"

#: Quantization rules. Like the DS rules they refuse a *run*, so they have no invalid-manifest
#: fixture and their own coverage test instead.
QUANTIZE_RULES: frozenset[str] = frozenset(
    {
        RULE_TRAINED_MODEL_UNREADABLE,
        RULE_CONVERSION_FAILED,
        RULE_NOT_FULLY_QUANTIZED,
        RULE_ACCURACY_GATE,
        RULE_GATE_UNMEASURABLE,
    }
)

# --- Rules that reject a run at the export stage -------------------------------------------------
# X rather than E, because E already belongs to the board emulator rules. X-4 and X-5 are the two
# that exist to stop a *silence*: an operator the target's runtime cannot resolve, and a board
# whose accelerated library nobody has read a source for. Both would otherwise turn into text that
# looks like an answer.
RULE_FORMAT_NOT_IMPLEMENTED = "X-1"
RULE_NOTHING_TO_EXPORT = "X-2"
RULE_MULTIPLE_SUBGRAPHS = "X-3"
RULE_OPERATOR_UNRESOLVABLE = "X-4"
# X-5 is defined above, with the other identifiers that reject nothing.
#: A declared input or output name is missing from the converted model's signature. A defect
#: between the build's rewiring and the conversion, refused by name rather than guessed at, because
#: the interface contract binds by that name (feature 006).
RULE_DECLARED_NAME_NOT_IN_MODEL = "X-6"

#: Export rules. Like the DS and Q rules they refuse a *run*, so none of them has an
#: invalid-manifest fixture and all of them are covered by their own coverage test instead. X-5 is
#: deliberately absent: see ``ENTAILED_RULES`` below.
EXPORT_RULES: frozenset[str] = frozenset(
    {
        RULE_FORMAT_NOT_IMPLEMENTED,
        RULE_NOTHING_TO_EXPORT,
        RULE_MULTIPLE_SUBGRAPHS,
        RULE_OPERATOR_UNRESOLVABLE,
        RULE_DECLARED_NAME_NOT_IN_MODEL,
    }
)

# --- Rules that reject a run at the fit check before training -----------------------------------
#: F-1: a computed lower bound on flash or working memory exceeds what a target board offers. A
#: floor is a lower bound, so no training can make that model fit that board (Principle V).
RULE_FLOOR_EXCEEDS_BOARD = "F-1"

#: Fit rules. They refuse a run, before any training, and are covered by their own coverage test.
FIT_RULES: frozenset[str] = frozenset({RULE_FLOOR_EXCEEDS_BOARD})

# --- Identifiers that never reject anything ---------------------------------------------------
RULE_NO_SCHEMA_VERSION = "V-2"
RULE_DATASET_UNRESOLVED = "D-1"

#: Informational identifiers: V-2 accepts a manifest that declares no version, D-1 records a
#: reference that was deliberately not resolved. Neither may have an invalid fixture.
INFORMATIONAL_RULES: frozenset[str] = frozenset({RULE_NO_SCHEMA_VERSION, RULE_DATASET_UNRESOLVED})

ALL_RULES: frozenset[str] = (
    MANIFEST_REJECTION_RULES
    | BOARD_RULES
    | RUN_RULES
    | QUANTIZE_RULES
    | EXPORT_RULES
    | FIT_RULES
    | INFORMATIONAL_RULES
    | ENTAILED_RULES
)


#: Identifiers that belonged to the compliance layer or to a section of a stage that does not exist
#: yet, and were removed in feature 006 (constitution 3.0.0, Principles I and VI). They are
#: reserved, never reused, and appear in no group above: CF-3 personal data against risk class,
#: CF-5 publication needs compliance, CF-7 an emulator exists for every target, CF-8 benchmark-only
#: data not published, DS-9 training not permitted.
RETIRED_RULES: frozenset[str] = frozenset({"CF-3", "CF-5", "CF-7", "CF-8", "DS-9"})


class RunRuleFailure(Exception):
    """A run refused by a rule, carrying the finding rather than a formatted string.

    Raised by a stage, not by a validator, which is why it is an exception of its own: a run rule
    fires when the data and the manifest disagree, long after the manifest itself was accepted.
    The command line turns it into the three-part message and exit code 1 — never a traceback.
    """

    def __init__(self, finding: Finding) -> None:
        super().__init__(finding.problem)
        self.finding = finding


def run_rule_error(
    rule: str,
    path: str,
    problem: str,
    *,
    found: Any = None,
    accepted: Sequence[str] = (),
) -> NoReturn:
    """Refuse a run with a finding that keeps its rule identifier and its field path."""
    raise RunRuleFailure(
        Finding(path=path, problem=problem, found=found, accepted=tuple(accepted), rule=rule)
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
