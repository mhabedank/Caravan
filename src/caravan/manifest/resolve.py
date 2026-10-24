"""The resolved manifest: every default expanded, nothing left implicit.

Key order comes from the schema, never from the input file, and no timestamp, absolute path or
machine-specific value appears anywhere in it — so two runs of the same input are byte-comparable
(research R9 of feature 001). Determinism belongs to this artifact; the run report carries the date.

Feature 008: every feature is shown fully resolved, in this order of precedence — the feature's own
value, then ``defaults`` for its type, then the type's default (contracts/manifest.md). What only
the training part can say — a vocabulary, a shift and a scale, the embedding size — is shown as
``derived`` until a run has fitted it; a run's resolved manifest carries the fitted values under
each feature's ``preprocessing.fitted`` (``merge_fitted``).
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from caravan.manifest._yaml import dump_mapping
from caravan.manifest.schema import Manifest, TypeDefaults
from caravan.manifest.schema.features import InputFeature, OutputFeature
from caravan.templates.registry import TemplateRegistry
from caravan.templates.registry import default_registry as default_templates

#: What the resolved manifest says where the value comes from the training part and no run has
#: fitted it yet (``caravan render``).
DERIVED = "derived"

#: Each input type's defaults, Ludwig's where Ludwig has one (contracts/manifest.md).
INPUT_DEFAULTS: dict[str, dict[str, Any]] = {
    "number": {
        "normalization": "zscore",
        "missing_value_strategy": "fill_with_const",
        "fill_value": 0.0,
    },
    "binary": {
        "missing_value_strategy": "fill_with_const",
        "fill_value": False,
        "fallback_true_label": None,
    },
    "category": {
        "missing_value_strategy": "fill_with_const",
        "fill_value": "<UNK>",
        "most_common": 32,
        "vocab": DERIVED,
    },
}
ENCODER_DEFAULTS: dict[str, Any] = {"type": "dense", "embedding_size": DERIVED}

#: The cap on the embedding's width when the author states none (spec, Assumptions; research R4).
EMBEDDING_SIZE_CAP = 4


def resolve(manifest: Manifest, *, templates: TemplateRegistry | None = None) -> dict[str, Any]:
    """Expand the manifest into the form the pipeline will actually read."""
    registry = templates or default_templates()
    spec = registry.get(manifest.model.template)
    params = (
        spec.parameters.model_validate(manifest.model.params).model_dump()
        if spec is not None
        else dict(manifest.model.params)
    )
    output = manifest.output_features[0]
    split = manifest.preprocessing.split

    return {
        "apiVersion": manifest.apiVersion,
        "model": {
            "name": manifest.model.name,
            "version": manifest.model.version,
            "template": manifest.model.template,
            "params": params,
        },
        "input_features": [
            resolve_input(feature, manifest.defaults.get(feature.type))
            for feature in manifest.input_features
        ],
        "output_features": [resolve_output(output)],
        "preprocessing": {
            "window_size": manifest.preprocessing.window_size,
            "split": (
                {"type": "fixed", "column": split.column}
                if split.type == "fixed"
                else {
                    "type": split.type,
                    "probabilities": list(split.probabilities or ()),
                    "column": output.name if split.type == "stratify" else None,
                }
            ),
        },
        "defaults": {
            key: _stated_defaults(entry) for key, entry in sorted(manifest.defaults.items())
        },
        "dataset": manifest.dataset,
        "trainer": {
            "epochs": manifest.trainer.epochs,
            "batch_size": manifest.trainer.batch_size,
            "learning_rate": manifest.trainer.learning_rate,
            "optimizer": {"type": manifest.trainer.optimizer.type},
            "early_stop": manifest.trainer.early_stop,
        },
        "random_seed": manifest.random_seed,
        "export": {
            "quantization": manifest.export.quantization,
            "formats": list(manifest.export.formats),
            "targets": list(manifest.export.targets),
            "representative_samples": manifest.export.representative_samples,
        },
    }


def _pick(key: str, own: Any, default: Any, fallback: Any) -> Any:
    """The feature's own value, then the type's ``defaults``, then the type default."""
    if own is not None and key in own.model_fields_set:
        return getattr(own, key)
    if default is not None and key in default.model_fields_set:
        return getattr(default, key)
    return fallback


def resolve_input(feature: InputFeature, defaults: TypeDefaults | None) -> dict[str, Any]:
    """One input feature, every key present."""
    stated = defaults.preprocessing if defaults is not None else None
    preprocessing = {
        key: _pick(key, feature.preprocessing, stated, fallback)
        for key, fallback in INPUT_DEFAULTS[feature.type].items()
    }
    if isinstance(preprocessing.get("vocab"), list):
        preprocessing["vocab"] = list(preprocessing["vocab"])
    out: dict[str, Any] = {
        "name": feature.name,
        "type": feature.type,
        "preprocessing": preprocessing,
    }
    if feature.type == "category":
        default_encoder = defaults.encoder if defaults is not None else None
        kind = _pick("type", feature.encoder, default_encoder, ENCODER_DEFAULTS["type"])
        encoder: dict[str, Any] = {"type": kind}
        if kind == "dense":
            encoder["embedding_size"] = _pick(
                "embedding_size", feature.encoder, default_encoder, DERIVED
            )
        out["encoder"] = encoder
    return out


def resolve_output(output: OutputFeature) -> dict[str, Any]:
    """The output feature, with the keys of its type and no other."""
    if output.type == "category":
        vocab = output.preprocessing.vocab
        return {
            "name": output.name,
            "type": output.type,
            "preprocessing": {"vocab": DERIVED if vocab is None else list(vocab)},
            "loss": {"class_weights": output.loss.class_weights},
            "accuracy_drop_max": output.accuracy_drop_max,
        }
    if output.type == "binary":
        return {
            "name": output.name,
            "type": output.type,
            "preprocessing": {"fallback_true_label": output.preprocessing.fallback_true_label},
            "loss": {"positive_class_weight": output.loss.positive_class_weight},
            "threshold": 0.5 if output.threshold is None else output.threshold,
            "accuracy_drop_max": output.accuracy_drop_max,
        }
    return {
        "name": output.name,
        "type": output.type,
        "preprocessing": {"normalization": output.preprocessing.normalization},
        "loss": {"type": output.loss.type or "mean_squared_error"},
        "clip": None if output.clip is None else list(output.clip),
        "mae_increase_max": output.mae_increase_max,
    }


def _stated_defaults(entry: TypeDefaults) -> dict[str, Any]:
    """A ``defaults`` entry as written: it is applied to the features above, and shown for that."""
    out: dict[str, Any] = {
        "preprocessing": {
            key: getattr(entry.preprocessing, key) for key in sorted(entry.preprocessing.model_fields_set)
        }
    }
    if entry.encoder is not None:
        out["encoder"] = {
            key: getattr(entry.encoder, key) for key in sorted(entry.encoder.model_fields_set)
        }
    return out


def merge_fitted(resolved: Mapping[str, Any], fitted: Mapping[str, Any]) -> dict[str, Any]:
    """The resolved manifest with what fitting on the training part found (``data/preprocessing.json``).

    Each feature gains ``preprocessing.fitted``, and the ``derived`` markers are replaced: a
    category's vocabulary, the dense encoder's ``embedding_size`` and the output's label order. A
    copy: the declared form stays what the ``data`` stage's own key is computed from, so that key
    never depends on the stage's own output (data model, *Stages*).
    """
    merged = copy.deepcopy(dict(resolved))
    by_name = fitted["input_features"]
    for feature in merged["input_features"]:
        values = by_name[feature["name"]]
        feature["preprocessing"]["fitted"] = copy.deepcopy(values)
        if feature["type"] == "category":
            feature["preprocessing"]["vocab"] = list(values["vocab"])
            encoder = feature["encoder"]
            if encoder.get("embedding_size") == DERIVED:
                encoder["embedding_size"] = min(len(values["vocab"]), EMBEDDING_SIZE_CAP)
    output = merged["output_features"][0]
    values = fitted["output"]
    output["preprocessing"]["fitted"] = copy.deepcopy(values)
    if output["type"] == "category":
        output["preprocessing"]["vocab"] = list(values["labels"])
    return merged


def render(manifest: Manifest, *, templates: TemplateRegistry | None = None) -> str:
    """The resolved manifest as YAML text, byte-identical across runs."""
    return dump_mapping(resolve(manifest, templates=templates))
