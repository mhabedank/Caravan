"""The data stage: windows, split, and each feature's preprocessing fitted on the training part.

Core module — the reader that parses the dataset is imported inside the stage function, so
importing this module pulls in no array library. The fitting itself is core (``data/fit.py``).

Feature 008 (research R6). The stage reads the typed columns, cuts the windows, splits them, and
fits every feature's preprocessing on the **training part only**: shift and scale, the vocabulary,
the binary spellings, the output's label order. It writes what it found to
``data/preprocessing.json``, which the pipeline merges into the run's resolved manifest under each
feature's ``preprocessing.fitted`` — so every later stage reads the fitted values through its
projection and its cache key covers them, and a reused result reads no data at all.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from caravan.data.windows import plan_windows, split_for
from caravan.manifest.resolve import DERIVED
from caravan.stages.base import StageContext, StageFunction, StageInputs, StageSpec

SCHEMA = "data/schema.json"
PREPROCESSING = "data/preprocessing.json"

SPEC = StageSpec(
    name="data",
    # As the author wrote them, never with the fitted values merged in, so this stage's key never
    # depends on its own output (data model, *Stages*). The window, the split and the seed decide
    # which records are the training part, so they are part of this stage's key.
    reads=(
        "input_features",
        "output_features[0].name",
        "output_features[0].type",
        "output_features[0].preprocessing",
        "preprocessing.window_size",
        "preprocessing.split",
        "random_seed",
    ),
    reads_dataset=True,
    upstream=None,
    artifacts=(SCHEMA, PREPROCESSING),
)


def training_rows(plan: Any, split: Any) -> list[int]:
    """The record indices of the training part's windows, in sequence order."""
    length = plan.window or 1
    rows: list[int] = []
    for position in split.train:
        start = plan.kept[position]
        rows.extend(range(start, start + length))
    return rows


def split_labels(output_type: str, plan_labels: Sequence[str]) -> tuple[str, ...]:
    """What a stratified split draws per, and what its counts are reported by.

    A ``number`` output has no classes, so its split is drawn as one pool and counted as one.
    """
    if output_type == "number":
        return ()
    return tuple(sorted(set(plan_labels)))


def fit_features(
    records: Any,
    rows: Sequence[int],
    features: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Each input feature's preprocessing, fitted on the given rows only."""
    from caravan.data.fit import fit_binary, fit_category, fit_number

    out: dict[str, dict[str, Any]] = {}
    for index, feature in enumerate(features):
        column = records.columns[feature["name"]][rows]
        stated = feature["preprocessing"]
        if feature["type"] == "number":
            out[feature["name"]] = fit_number(
                column.tolist(),
                normalization=stated["normalization"],
                strategy=stated["missing_value_strategy"],
                fill_value=float(stated["fill_value"]),
            )
        elif feature["type"] == "category":
            vocab = stated["vocab"]
            out[feature["name"]] = fit_category(
                column.tolist(),
                most_common=int(stated["most_common"]),
                fill_value=stated["fill_value"],
                pinned=None if vocab == DERIVED else vocab,
            )
        else:
            out[feature["name"]] = fit_binary(
                column.tolist(),
                fallback_true_label=stated["fallback_true_label"],
                path=f"input_features[{index}].preprocessing",
                fill_value=stated["fill_value"],
            )
    return out


def fit_output(
    output_type: str,
    preprocessing: Mapping[str, Any],
    plan_labels: Sequence[str],
    train: Sequence[int],
) -> dict[str, Any]:
    """The output's fitted values: its label order, its spellings, or its shift and scale."""
    from caravan.data.fit import fit_output_binary, fit_output_category, fit_output_number

    trained = [plan_labels[position] for position in train]
    path = "output_features[0]"
    if output_type == "category":
        vocab = preprocessing["vocab"]
        return fit_output_category(
            trained, plan_labels, pinned=None if vocab == DERIVED else vocab, path=path
        )
    if output_type == "binary":
        return fit_output_binary(
            trained,
            plan_labels,
            fallback_true_label=preprocessing["fallback_true_label"],
            path=path,
        )
    return fit_output_number(
        [float(label) for label in trained], normalization=preprocessing["normalization"]
    )


def run_data(records: Any, inputs: StageInputs) -> tuple[dict[str, Any], dict[str, Any]]:
    """``data/schema.json`` and ``data/preprocessing.json`` for these records."""
    features = inputs["input_features"]
    output_type = inputs["output_features[0].type"]
    split_spec = inputs["preprocessing.split"]
    plan = plan_windows(records.labels, inputs["preprocessing.window_size"], parts=records.parts)
    labels = split_labels(output_type, plan.labels)
    split = split_for(plan, split_spec, seed=int(inputs["random_seed"]), labels=labels)

    fitted = {
        "input_features": fit_features(records, training_rows(plan, split), features),
        "output": fit_output(
            output_type, inputs["output_features[0].preprocessing"], plan.labels, split.train
        ),
    }
    schema = {
        "features": [
            {
                "name": feature["name"],
                "type": feature["type"],
                "fitted": fitted["input_features"][feature["name"]],
            }
            for feature in features
        ],
        "output": {
            "name": inputs["output_features[0].name"],
            "type": output_type,
            "fitted": fitted["output"],
        },
        "ignored_columns": list(records.schema.ignored_names),
        "split_column": split_spec.get("column") if split_spec["type"] == "fixed" else None,
        "records": records.schema.record_count,
        "windows_kept": plan.samples,
        "windows_discarded_mixed": plan.discarded_mixed,
        "windows_discarded_mixed_split": plan.discarded_mixed_split,
        "records_dropped_remainder": plan.dropped_remainder,
        "split": split.counts,
        "split_source": split.source,
        "fitted_on": "train",
    }
    return schema, fitted


def stage(context: StageContext) -> StageFunction:
    """The stage function, bound to this run's dataset."""

    def run(inputs: StageInputs, out_dir: Path) -> None:
        schema, fitted = run_data(context.records(), inputs)
        (out_dir / "data").mkdir(parents=True, exist_ok=True)
        for name, payload in ((SCHEMA, schema), (PREPROCESSING, fitted)):
            (out_dir / name).write_text(
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    return run


def load_schema(run_dir: Path) -> dict[str, Any]:
    """What the data stage found, from the artifact in the run directory — produced or reused."""
    return json.loads((run_dir / SCHEMA).read_text(encoding="utf-8"))


def load_fitted(run_dir: Path) -> dict[str, Any]:
    """The fitted preprocessing, from the artifact in the run directory."""
    return json.loads((run_dir / PREPROCESSING).read_text(encoding="utf-8"))
