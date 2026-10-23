"""The data stage: what the data says, said once (feature 006, research R3).

Core module — the reader that parses the dataset is imported inside the stage function, so
importing this module pulls in no array library.

Two values of a manifest may be left to the data: the input's columns, which are then every column
the output does not read, in file order; and the output's labels, which are then the distinct
values of its column, sorted. This stage derives both, checks a pinned label list against the data
in both directions (rule DS-5), and writes what it found. The pipeline merges that into the run's
resolved manifest, so every later stage reads the derived values through its projection and its
cache key covers them — and a reused result reads no data at all, as before.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from caravan.manifest.errors import RULE_DATASET_LABELS, RULE_TOO_FEW_CLASSES, run_rule_error
from caravan.manifest.resolve import DERIVED
from caravan.stages.base import StageContext, StageFunction, StageInputs, StageSpec

SCHEMA = "data/schema.json"

SPEC = StageSpec(
    name="data",
    # As the author wrote them — a list, or the marker ``derived`` — so this stage's key never
    # depends on its own output (data model, *Stages*).
    reads=("inputs[0].columns", "outputs[0].column", "outputs[0].labels"),
    reads_dataset=True,
    upstream=None,
    artifacts=(SCHEMA,),
)


def derive_labels(seen: tuple[str, ...], pinned: list[str] | None) -> tuple[list[str], str]:
    """The labels and where they came from: ``stated`` or ``derived``.

    Derived labels are sorted as text, so ``10`` sorts before ``2``; the run's resolved manifest
    shows the order, and an author who wants another one pins it.
    """
    distinct = set(seen)
    if pinned is None:
        labels = sorted(distinct)
        if len(labels) < 2:
            run_rule_error(
                RULE_TOO_FEW_CLASSES,
                "outputs[0].column",
                (
                    f"the output column holds {len(labels)} distinct value(s), so there is nothing "
                    "to classify; a class output needs at least two"
                ),
                found=labels,
            )
        return labels, "derived"

    # Both directions, because both are a disagreement (DS-5). A value in the data the list does not
    # name has no output unit; a listed value the data never shows can be neither split nor scored.
    unlisted = sorted(distinct - set(pinned))
    if unlisted:
        run_rule_error(
            RULE_DATASET_LABELS,
            "outputs[0].labels",
            (
                f"the data contains {len(unlisted)} label(s) the manifest does not list: "
                f"{', '.join(unlisted)}"
            ),
            found=unlisted,
            accepted=tuple(pinned),
        )
    unseen = sorted(set(pinned) - distinct)
    if unseen:
        run_rule_error(
            RULE_DATASET_LABELS,
            "outputs[0].labels",
            (
                f"the manifest lists {len(unseen)} label(s) the data never shows: "
                f"{', '.join(unseen)}"
            ),
            found=sorted(distinct),
            accepted=tuple(pinned),
        )
    return list(pinned), "stated"


def describe(records: Any, inputs: StageInputs) -> dict[str, Any]:
    """The contents of ``data/schema.json``."""
    pinned = inputs["outputs[0].labels"]
    labels, labels_source = derive_labels(records.labels, None if pinned == DERIVED else pinned)
    return {
        "input_columns": list(records.schema.feature_names),
        "columns_source": "derived" if inputs["inputs[0].columns"] == DERIVED else "stated",
        "output_column": inputs["outputs[0].column"],
        "labels": labels,
        "labels_source": labels_source,
        "ignored_columns": list(records.schema.ignored_names),
        "records": records.schema.record_count,
    }


def stage(context: StageContext) -> StageFunction:
    """The stage function, bound to this run's dataset."""

    def run(inputs: StageInputs, out_dir: Path) -> None:
        schema = describe(context.records(), inputs)
        (out_dir / "data").mkdir(parents=True, exist_ok=True)
        (out_dir / SCHEMA).write_text(
            json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return run


def load_schema(run_dir: Path) -> dict[str, Any]:
    """What the data stage found, from the artifact in the run directory — produced or reused."""
    return json.loads((run_dir / SCHEMA).read_text(encoding="utf-8"))
