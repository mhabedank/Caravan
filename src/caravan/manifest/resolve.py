"""The resolved manifest: every default expanded, nothing left implicit.

Key order comes from the schema, never from the input file, and no timestamp, absolute path or
machine-specific value appears anywhere in it — so two runs of the same input are byte-comparable
(research R9, SC-005). Determinism belongs to this artifact; the run report carries the date.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from caravan.manifest._yaml import dump_mapping
from caravan.manifest.schema import Manifest
from caravan.templates.registry import TemplateRegistry
from caravan.templates.registry import default_registry as default_templates

#: What the resolved manifest says where the value comes from the data and no run has read it yet
#: (``caravan render``). A run's resolved manifest replaces it with what the ``data`` stage found
#: (FR-013, contracts/manifest.md).
DERIVED = "derived"


def resolve(manifest: Manifest, *, templates: TemplateRegistry | None = None) -> dict[str, Any]:
    """Expand the manifest into the form the pipeline will actually read."""
    registry = templates or default_templates()
    spec = registry.get(manifest.model.template)
    params = (
        spec.parameters.model_validate(manifest.model.params).model_dump()
        if spec is not None
        else dict(manifest.model.params)
    )

    return {
        "apiVersion": manifest.apiVersion,
        "model": {
            "name": manifest.model.name,
            "version": manifest.model.version,
            "template": manifest.model.template,
            "params": params,
        },
        "inputs": [
            {
                "name": declared.name,
                "kind": declared.kind,
                "columns": DERIVED if declared.columns is None else list(declared.columns),
                "window": declared.window,
            }
            for declared in manifest.inputs
        ],
        "outputs": [
            {
                "name": declared.name,
                "kind": declared.kind,
                "column": declared.column,
                "labels": DERIVED if declared.labels is None else list(declared.labels),
                "accuracy_drop_max": declared.accuracy_drop_max,
            }
            for declared in manifest.outputs
        ],
        "dataset": {
            "source": manifest.dataset.source,
            "split": {
                "train": manifest.dataset.split.train,
                "val": manifest.dataset.split.val,
                "test": manifest.dataset.split.test,
                "stratified": manifest.dataset.split.stratified,
            },
            "representative_samples": manifest.dataset.representative_samples,
        },
        "train": {
            "epochs": manifest.train.epochs,
            "batch": manifest.train.batch,
            "optimizer": manifest.train.optimizer,
            "learning_rate": manifest.train.learning_rate,
            "early_stopping": manifest.train.early_stopping,
            "patience": manifest.train.patience,
            "seed": manifest.train.seed,
        },
        "export": {
            "quantization": manifest.export.quantization,
            "formats": list(manifest.export.formats),
            "targets": list(manifest.export.targets),
        },
    }


def merge_derived(
    resolved: Mapping[str, Any], *, input_columns: Sequence[str], labels: Sequence[str]
) -> dict[str, Any]:
    """The resolved manifest with what the data said in place of the ``derived`` markers.

    A copy: the declared form stays what the ``data`` stage's own key is computed from, so that key
    never depends on the stage's own output (data model, *Stages*).
    """
    merged = copy.deepcopy(dict(resolved))
    merged["inputs"][0]["columns"] = list(input_columns)
    merged["outputs"][0]["labels"] = list(labels)
    return merged


def render(manifest: Manifest, *, templates: TemplateRegistry | None = None) -> str:
    """The resolved manifest as YAML text, byte-identical across runs."""
    return dump_mapping(resolve(manifest, templates=templates))
