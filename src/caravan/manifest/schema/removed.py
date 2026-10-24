"""The fields schema versions ``caravan/v0.1`` and ``caravan/v0.2`` removed or moved, and why.

Read by the loader, for the message a manifest that still carries one of these fields is refused
with, and mirrored by the change note in ``docs/manifest-changes.md``. Nothing migrates them: before
Caravan 1.0.0 an older form is refused, not converted (constitution 4.0.0, Principle IX).

The messages come from ``specs/006-declared-io/contracts/manifest.md`` and
``specs/008-typed-features/contracts/manifest.md`` (Removed). A removed field gets its own message
rather than the generic "unknown field" (FR-001), so an author learns that the field is gone, and
not that it is misspelt.
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
    #: The schema version that removed or moved it.
    version: str = "caravan/v0.1"

    def message(self) -> str:
        """The sentence a new-form manifest that still carries this field is refused with."""
        verb = "moved" if self.action == "moved" else "removed"
        where = f" to {self.to}" if self.to else ""
        return f"{verb} in {self.version}{where}: {self.reason}"


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
        "export.accuracy_drop_max",
        "moved",
        "output_features[0].accuracy_drop_max",
        "the budget is per output (Principle V)",
    ),
)

_V02 = "caravan/v0.2"

#: What ``caravan/v0.2`` moved, in the order of ``specs/008-typed-features/contracts/manifest.md``.
#: Each is refused at its own path, with the key that replaces it named (research R1).
MOVED_IN_V02: tuple[RemovedField, ...] = (
    RemovedField(
        "inputs",
        "moved",
        "input_features",
        "one feature per column, each with its name (the column) and its type; "
        "inputs[0].window is preprocessing.window_size",
        _V02,
    ),
    RemovedField(
        "outputs",
        "moved",
        "output_features",
        "the output's name is its column; outputs[0].labels is "
        "output_features[0].preprocessing.vocab, and the budget stays on the output",
        _V02,
    ),
    RemovedField(
        "train",
        "moved",
        "trainer",
        "with Ludwig's names: batch is batch_size, optimizer is optimizer.type, early_stopping "
        "and patience are early_stop (-1 never stops), and seed is the top-level random_seed",
        _V02,
    ),
    RemovedField("dataset.source", "moved", "dataset", "dataset is now the path itself", _V02),
    RemovedField(
        "dataset.split",
        "moved",
        "preprocessing.split",
        "with Ludwig's names: type random, stratify or fixed, probabilities, column",
        _V02,
    ),
    RemovedField(
        "dataset.representative_samples",
        "moved",
        "export.representative_samples",
        "it calibrates the quantization",
        _V02,
    ),
)

BY_PATH: dict[str, RemovedField] = {field.path: field for field in REMOVED_FIELDS}
MOVED_BY_PATH: dict[str, RemovedField] = {field.path: field for field in MOVED_IN_V02}

#: The key that replaces a moved top-level section: when the old one is present, a missing new one
#: is not reported a second time.
REPLACES: dict[str, str] = {"inputs": "input_features", "outputs": "output_features"}
