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
    # Exactly what building depends on — including the seed: Keras initialises weights when the
    # model is constructed, so ``built.keras`` already contains them, and a cache that reused a
    # built model across seeds would hand back weights the manifest did not ask for.
    #
    # The input features are read whole, with their fitted values merged in by the pipeline: the
    # vocabulary, the shift and the scale are constants of the model (feature 008). The output is
    # read field by field, never its budget: changing the budget must not rebuild (Principle III,
    # feature 006 FR-031). ``clip`` belongs to a number output only, so it is optional.
    reads=(
        "model.template",
        "model.params",
        "random_seed",
        "input_features",
        "output_features[0].name",
        "output_features[0].type",
        "output_features[0].preprocessing",
        "output_features[0].clip?",
        "preprocessing.window_size",
    ),
    # The fitted values come from the data, and the data stays part of the key all the same:
    # building is cheap, and a dataset that changed is retrained on anyway.
    reads_dataset=True,
    upstream=None,
    artifacts=(BUILT_MODEL, BUILT_REPORT),
)


def require_framework(command: str) -> None:
    if not training_framework_available():
        raise EnvironmentIncomplete(missing_extra_message(command))


def describe(model: Any, template: str, inputs: StageInputs) -> dict:
    """The contents of ``built.json``: the shape report FR-002 requires, per input."""
    # ``math.prod`` over the shapes rather than a count attribute: Keras 3 variables expose a
    # shape, and a count attribute that exists in one version and not another is how a report
    # starts lying after an upgrade.
    trainable = sum(math.prod(weight.shape) for weight in model.trainable_weights)
    non_trainable = sum(math.prod(weight.shape) for weight in model.non_trainable_weights)
    output = inputs["output_features[0].name"]
    return {
        "template": template,
        "inputs": [
            {
                "name": tensor.name.split(":")[0],
                "dtype": str(tensor.dtype),
                "shape": [None if size is None else int(size) for size in tensor.shape[1:]],
            }
            for tensor in model.inputs
        ],
        "output_name": output,
        "output_type": inputs["output_features[0].type"],
        "output_shape": [int(size) for size in model.outputs[0].shape[1:]],
        "parameter_count": trainable + non_trainable,
        "trainable_parameters": trainable,
        "non_trainable_parameters": non_trainable,
        "layers": layer_table(model),
        **framework_record(),
    }


def output_feature(inputs: StageInputs) -> dict[str, Any]:
    """The output feature as the front-end and the stages read it, from the projection."""
    return {
        "name": inputs["output_features[0].name"],
        "type": inputs["output_features[0].type"],
        "preprocessing": inputs["output_features[0].preprocessing"],
        "clip": inputs.get("output_features[0].clip"),
    }


def construct(inputs: StageInputs, context: StageContext) -> Any:
    """Build the model the manifest describes, and return it with its description."""
    import keras

    from caravan.templates.builders import load_builder
    from caravan.templates.builders.frontend import build_model

    # Before construction, because construction is where the weights are drawn.
    keras.utils.set_random_seed(int(inputs["random_seed"]))

    builder = load_builder(inputs["model.template"])
    model = build_model(
        builder,
        inputs["model.params"],
        inputs["input_features"],
        output_feature(inputs),
        inputs["preprocessing.window_size"],
    )
    return model, describe(model, inputs["model.template"], inputs)


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

    # The preprocessing layers are registered on import; a model that carries them loads only then.
    import caravan.templates.builders.preprocessing  # noqa: F401

    return keras.saving.load_model(run_dir / BUILT_MODEL)
