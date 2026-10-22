"""The resolved manifest: every default expanded, nothing left implicit.

Key order comes from the schema, never from the input file, and no timestamp, absolute path or
machine-specific value appears anywhere in it — so two runs of the same input are byte-comparable
(research R9, SC-005). Determinism belongs to this artifact; the run report carries the date.
"""

from __future__ import annotations

from typing import Any

from caravan.manifest._yaml import dump_mapping
from caravan.manifest.schema import Manifest
from caravan.templates.registry import TemplateRegistry
from caravan.templates.registry import default_registry as default_templates


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
            "topic": manifest.model.topic,
            "task": manifest.model.task,
            "template": manifest.model.template,
            "params": params,
        },
        "dataset": {
            "source": manifest.dataset.source,
            "split": {
                "train": manifest.dataset.split.train,
                "val": manifest.dataset.split.val,
                "test": manifest.dataset.split.test,
                "stratified": manifest.dataset.split.stratified,
            },
            "window": manifest.dataset.window,
            "labels": list(manifest.dataset.labels),
            "representative_samples": manifest.dataset.representative_samples,
            "license": manifest.dataset.license,
            "permitted_use": manifest.dataset.permitted_use,
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
            "accuracy_drop_max": manifest.export.accuracy_drop_max,
        },
        "verify": {"emulator": manifest.verify.emulator},
        "bench": {"metrics": list(manifest.bench.metrics)},
        # Explicitly null rather than absent: "this model is not published" is a concrete value,
        # and SC-007 asks for no implicit ones.
        "publish": (
            None
            if manifest.publish is None
            else {
                "hf_repo": manifest.publish.hf_repo,
                "license": manifest.publish.license,
            }
        ),
        "compliance": {
            "eu_ai_act_class": manifest.compliance.eu_ai_act_class,
            "privacy": manifest.compliance.privacy,
            "intended_use": manifest.compliance.intended_use,
            "known_limits": list(manifest.compliance.known_limits),
        },
    }


def render(manifest: Manifest, *, templates: TemplateRegistry | None = None) -> str:
    """The resolved manifest as YAML text, byte-identical across runs."""
    return dump_mapping(resolve(manifest, templates=templates))
