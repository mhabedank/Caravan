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
        "train.seed",
        # Field by field, never the whole declaration: the budget inside ``outputs[0]`` is read by
        # ``quantize`` alone, so changing it must not rebuild (Principle III, feature 006 FR-031).
        "inputs[0].name",
        "inputs[0].columns",
        "inputs[0].window",
        "outputs[0].name",
        "outputs[0].labels",
    ),
    # The feature width is the number of the input's columns, which the projection carries since
    # feature 006. The data stays part of the key all the same: building is cheap, and a dataset
    # that changed is retrained on anyway.
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


def rewire(model: Any, input_name: str, output_name: str) -> Any:
    """The builder's model, unchanged, under the declared names (feature 006, research R4).

    The converter keeps an input's name but drops an output layer's name unless the model returns a
    dict, and with two outputs it reorders them; only the signature then still says which is
    which. So: an ``Input`` named after the declared input, the builder's own layers applied in
    order — the same layer objects, so the same weights — and a dict output keyed by the declared
    output. Measured on both templates: no weight and no converted operator changes.

    Builders keep their signature; the names are the pipeline's concern, not a template's, and a
    third-party template registered by entry point works unchanged.
    """
    import keras

    inputs = keras.Input(shape=tuple(model.input_shape[1:]), name=input_name)
    tensor = inputs
    for layer in model.layers:
        tensor = layer(tensor)
    return keras.Model(inputs, {output_name: tensor}, name=model.name)


def describe(
    model: Any,
    template: str,
    window: int | None,
    labels: tuple[str, ...],
    names: tuple[str, str] = ("input", "output"),
) -> dict:
    """The contents of ``built.json``: the shape report FR-002 requires."""
    # ``math.prod`` over the shapes rather than a count attribute: Keras 3 variables expose a
    # shape, and a count attribute that exists in one version and not another is how a report
    # starts lying after an upgrade.
    trainable = sum(math.prod(weight.shape) for weight in model.trainable_weights)
    non_trainable = sum(math.prod(weight.shape) for weight in model.non_trainable_weights)
    return {
        "template": template,
        "input_name": names[0],
        "output_name": names[1],
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

    window = inputs["inputs[0].window"]
    labels = tuple(inputs["outputs[0].labels"])
    # The columns are the merged, derived-or-stated list (data stage): their number is the width.
    shape = input_shape_for(window, len(inputs["inputs[0].columns"]))

    builder = load_builder(inputs["model.template"])
    names = (inputs["inputs[0].name"], inputs["outputs[0].name"])
    model = rewire(builder(inputs["model.params"], shape, labels), *names)
    return model, describe(model, inputs["model.template"], window, labels, names)


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
