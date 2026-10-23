"""The fields schema version ``caravan/v0.1`` removed or moved, and why.

Read by the loader, for the message a manifest that still carries one of these fields is refused
with, and mirrored by the change note in ``docs/manifest-changes.md``. Nothing migrates them: before
Caravan 1.0.0 an older form is refused, not converted (constitution 4.0.0, Principle IX).

The messages come from ``specs/006-declared-io/contracts/manifest.md`` (Removed fields). A removed
field gets its own message rather than the generic "unknown field" (FR-001), so an author learns
that the field is gone, and not that it is misspelt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Action = Literal["dropped", "moved"]


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

#: In the order the change note lists them.
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
