"""The build stage: the manifest's model, constructed and reported.

Core module. Every framework import happens inside a function, and the builder half of the
template is loaded by name — so ``import caravan.stages.build`` pulls in no framework, which the
layering tests assert.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from caravan.env import EnvironmentIncomplete, missing_extra_message, training_framework_available
from caravan.stages._framework import framework_record, layer_table
from caravan.stages.base import StageContext, StageFunction, StageInputs, StageSpec

BUILT_MODEL = "model/built.keras"
BUILT_REPORT = "model/built.json"

SPEC = StageSpec(
    name="build",
    # Exactly what building depends on — including the seed, which the plan did not have here.
    # Keras initialises weights when the model is constructed, so ``built.keras`` already contains
    # them: the seed that produced them is an input to *this* stage, and a cache that reused a
    # built model across seeds would hand back weights the manifest did not ask for. Not here:
    # dataset.source, because the content is an input and the path is not.
    reads=(
        "model.template",
        "model.params",
        "dataset.window",
        "dataset.labels",
        "train.seed",
    ),
    # The feature width comes from the data (FR-004), so the data is an input to the built shape.
    reads_dataset=True,
    upstream=None,
    artifacts=(BUILT_MODEL, BUILT_REPORT),
)


def input_shape_for(window: int | None, features: int) -> tuple[int, ...]:
    """``(window, features)`` with a window, ``(features,)`` without one."""
    return (window, features) if window else (features,)


def require_framework(command: str) -> None:
    if not training_framework_available():
        raise EnvironmentIncomplete(missing_extra_message(command))


def describe(model: Any, template: str, window: int | None, labels: tuple[str, ...]) -> dict:
    """The contents of ``built.json``: the shape report FR-002 requires."""
    # ``math.prod`` over the shapes rather than a count attribute: Keras 3 variables expose a
    # shape, and a count attribute that exists in one version and not another is how a report
    # starts lying after an upgrade.
    trainable = sum(math.prod(weight.shape) for weight in model.trainable_weights)
    non_trainable = sum(math.prod(weight.shape) for weight in model.non_trainable_weights)
    return {
        "template": template,
        "input_shape": list(input_shape_for(window, int(model.input_shape[-1]))),
        "output_units": len(labels),
        "parameter_count": trainable + non_trainable,
        "trainable_parameters": trainable,
        "non_trainable_parameters": non_trainable,
        "labels": list(labels),
        "layers": layer_table(model),
        **framework_record(),
    }


def construct(inputs: StageInputs, context: StageContext) -> Any:
    """Build the model the manifest describes, and return it with its description."""
    import keras

    from caravan.templates.builders import load_builder

    # Before construction, because construction is where the weights are drawn.
    keras.utils.set_random_seed(int(inputs["train.seed"]))

    records = context.records()
    window = inputs["dataset.window"]
    labels = tuple(inputs["dataset.labels"])
    shape = input_shape_for(window, records.schema.feature_count)

    builder = load_builder(inputs["model.template"])
    model = builder(inputs["model.params"], shape, labels)
    return model, describe(model, inputs["model.template"], window, labels)


def stage(context: StageContext) -> StageFunction:
    """The stage function, bound to this run's dataset."""

    def run(inputs: StageInputs, out_dir: Path) -> None:
        require_framework("build")
        model, description = construct(inputs, context)

        (out_dir / "model").mkdir(parents=True, exist_ok=True)
        model.save(out_dir / BUILT_MODEL)
        (out_dir / BUILT_REPORT).write_text(
            json.dumps(description, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return run


def load_built_model(run_dir: Path) -> Any:
    """Load the artifact the build stage wrote. Used by the train stage, never by the core."""
    import keras

    return keras.saving.load_model(run_dir / BUILT_MODEL)
