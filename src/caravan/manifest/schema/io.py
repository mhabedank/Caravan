"""The declared input and output (feature 006, constitution 3.0.0 Principle I).

A manifest says what goes into the model and what comes out, each with a kind; the output's kind is
what says what the model does. Both are lists in the manifest, so a second input or output later is
an additive change, and this build accepts exactly one of each (rule CF-10, Principle X).

The form of a name and the set of implemented kinds are checked by the manifest, not here: only the
manifest knows the position of a declaration, and a rule's finding carries its full path,
``inputs[0].name`` rather than ``name``.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: What a declaration name must look like. The intersection of a C identifier, which the exported
#: header uses (``g_model_data_input_<name>``), and a name a converted model's signature keeps
#: intact (research R2, R4 of feature 006). No hyphen, because a hyphen is not C.
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
NAME_FORM = (
    "a lower-case letter followed by up to 31 lower-case letters, digits or underscores, "
    "for example frames or attack_type"
)

#: The kinds this build implements, justified by the pilot models (Principle X).
INPUT_KINDS: tuple[str, ...] = ("series",)
OUTPUT_KINDS: tuple[str, ...] = ("class",)

#: The column a class output reads when it names none: the one the data contract of feature 002
#: fixed, so a dataset that worked before needs no new statement.
DEFAULT_OUTPUT_COLUMN = "label"


def _distinct_names(values: list[str], what: str) -> list[str]:
    if any(not value.strip() for value in values):
        raise ValueError(f"every {what} must be a non-empty name")
    if len(set(values)) != len(values):
        raise ValueError(f"{what}s must be distinct")
    return values


class InputDeclaration(BaseModel):
    """What goes into the model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: str
    #: The data columns this input reads, in the order they go into the tensor. Left out, they are
    #: every column the output does not read, in file order, derived by the run.
    columns: list[str] | None = Field(default=None, min_length=1)
    #: How many consecutive records form one sample. Required exactly when the template consumes a
    #: window (rule CF-6).
    window: int | None = Field(default=None, gt=0)

    @field_validator("columns")
    @classmethod
    def _columns_are_distinct(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _distinct_names(value, "column")


class OutputDeclaration(BaseModel):
    """What comes out of the model, and the budget its quantization is held to."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: str
    #: The data column holding the class names.
    column: str = Field(default=DEFAULT_OUTPUT_COLUMN, min_length=1)
    #: Pins the order of the output units. Left out, the labels are the distinct values of
    #: ``column`` across the whole dataset, sorted, derived by the run (FR-011).
    labels: list[str] | None = Field(default=None, min_length=2)
    #: The largest accuracy drop from quantization this output accepts. Required, with no default:
    #: Principle V requires every manifest to state its budgets (FR-029).
    accuracy_drop_max: float = Field(ge=0.0, le=1.0)

    @field_validator("labels")
    @classmethod
    def _labels_are_distinct(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _distinct_names(value, "label")


def name_problem(name: str) -> str | None:
    """Why a declaration name is not acceptable, or ``None`` when it is."""
    if NAME_PATTERN.match(name):
        return None
    return f"a declaration name must be {NAME_FORM}"
