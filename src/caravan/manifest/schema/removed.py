"""The fields schema version ``caravan/v0.1`` removed or moved, and why.

One table, read in three places: the migration that turns a ``caravan/v0`` manifest into the new
form, the validation message for a removed field written in a new-form manifest, and the migration
note in ``docs/migrations/caravan-v0.1.md``. Three copies would drift; one table cannot.

The messages come from ``specs/006-declared-io/contracts/manifest.md`` (Removed fields). A removed
field gets its own message rather than the generic "unknown field" (FR-001), so an author learns
that the field is gone, and not that it is misspelt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Action = Literal["dropped", "moved", "added"]


@dataclass(frozen=True)
class RemovedField:
    """What happened to one field of the previous form."""

    path: str
    action: Action
    #: The new path, for a moved field.
    to: str | None
    reason: str

    def message(self) -> str:
        """The sentence a new-form manifest that still carries this field is refused with."""
        verb = "moved" if self.action == "moved" else "removed"
        where = f" to {self.to}" if self.to else ""
        return f"{verb} in caravan/v0.1{where}: {self.reason}"


_NO_COMPLIANCE = (
    "Caravan carries no compliance layer (constitution 3.0.0, Principle VI); a project that needs "
    "one adds it on top"
)
_NO_STAGE_READ_IT = "no stage read it; the output's kind says what the model does"
_NO_DATA_RIGHTS = "Caravan does not check data rights and does not claim to (Principle VI)"
_NO_STAGE_YET = "no stage reads it yet; it returns with its stage (Principle I)"

#: In the order the migration applies them and reports them.
REMOVED_FIELDS: tuple[RemovedField, ...] = (
    RemovedField("model.topic", "dropped", None, _NO_STAGE_READ_IT),
    RemovedField("model.task", "dropped", None, _NO_STAGE_READ_IT),
    RemovedField("dataset.license", "dropped", None, _NO_DATA_RIGHTS),
    RemovedField("dataset.permitted_use", "dropped", None, _NO_DATA_RIGHTS),
    RemovedField("compliance", "dropped", None, _NO_COMPLIANCE),
    RemovedField("verify", "dropped", None, _NO_STAGE_YET),
    RemovedField("bench", "dropped", None, _NO_STAGE_YET),
    RemovedField("publish", "dropped", None, _NO_STAGE_YET),
    RemovedField(
        "dataset.window",
        "moved",
        "inputs[0].window",
        "a window describes how the input is cut, so it belongs to the input",
    ),
    RemovedField(
        "dataset.labels",
        "moved",
        "outputs[0].labels",
        "labels are derived from the data; a stated list only pins their order",
    ),
    RemovedField(
        "export.accuracy_drop_max",
        "moved",
        "outputs[0].accuracy_drop_max",
        "the budget is per output (Principle V)",
    ),
)

BY_PATH: dict[str, RemovedField] = {field.path: field for field in REMOVED_FIELDS}

#: The notice for a previous-form manifest that stated ``permitted_use: benchmark-only`` and asked
#: for publication: rule CF-8 used to refuse it, and dropping the statement silently would hide
#: that the author's own restriction is no longer enforced (migration contract, step 2).
BENCHMARK_ONLY_PUBLISH_NOTICE = (
    "the manifest stated that this dataset is not permitted for training and asked for "
    "publication; Caravan no longer enforces that statement (Principle VI), so it is now the "
    "author's to keep"
)

#: The notice for a previous-form manifest that left the quantization budget to its default.
#: ``caravan/v0.1`` requires the budget to be stated (Principle V, FR-029), so the migration states
#: the old default rather than inventing a stricter or looser one.
PREVIOUS_DEFAULT_BUDGET = 0.02
BUDGET_ADDED_NOTICE = (
    "the previous form defaulted the quantization budget to 0.02; caravan/v0.1 requires it to be "
    "stated (Principle V), so the migration states it"
)
