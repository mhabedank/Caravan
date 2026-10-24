"""Fix a trained model's input batch to one, before it is converted.

On a microcontroller the batch is one. Always: a board reads one window from its sensors and asks
for one answer. A graph converted from a model whose batch is undetermined does not know that, so
the converter emits operators to compute the flatten shape at run time from the batch dimension —
``SHAPE``, ``STRIDED_SLICE``, ``PACK``, ``RESHAPE``. Four kernels in flash and four entries in the
resolver, for arithmetic whose answer was known before the firmware was built. Measured on the mlp
template (2026-10-22): six distinct operators and 8,656 bytes become three and 7,856.

Why here and not in the template: training wants a batch, and fixing it in the input layer would
make training run one window at a time, changing both its speed and its dynamics. The batch belongs
to deployment, so it is fixed in the conversion — once, so that the model the accuracy gate
measures and the model that ships are the same graph. Converting twice would give two models and
two accuracies, and the one that shipped would be the one nobody gated.

Imports Keras at module level, which makes this an extra-only module by design.
"""

from __future__ import annotations

from typing import Any

import keras

#: The only batch a board ever uses, and therefore the only one this converts to.
DEPLOYED_BATCH = 1


def fix_batch(model: Any) -> Any:
    """Return the same function on a batch of one: a clone with the trained weights.

    Every input is rebuilt at batch one with its own name and its own element type — a model of
    feature 008 has one input per feature, float32 for numbers and int32 for codes, and an input
    rebuilt as float would compare codes in floating point.

    Idempotent: a model whose every input is already fixed to one is returned unchanged.

    A model fixed to some *other* batch is refused rather than reshaped, and so is a model with a
    ``Lambda`` layer: its function is Python code that a clone cannot be shown to rebuild, which is
    why every preprocessing layer of Caravan's is a registered layer with its constants as
    arguments (research R9).
    """
    if any(isinstance(layer, keras.layers.Lambda) for layer in model.layers):
        raise ValueError(
            "the model contains a Lambda layer, which the batch fix cannot rebuild faithfully; "
            "use a registered layer whose constants are constructor arguments"
        )
    batches = {tuple(tensor.shape)[0] for tensor in model.inputs}
    if batches == {DEPLOYED_BATCH}:
        return model
    fixed_to = sorted(batch for batch in batches if batch is not None)
    if fixed_to:
        raise ValueError(
            f"the model's input batch is fixed to {fixed_to[0]}, and converting for a target needs "
            f"a batch of {DEPLOYED_BATCH}; build the model with an undetermined batch and let the "
            "conversion fix it"
        )

    inputs = [
        keras.layers.Input(
            batch_shape=(DEPLOYED_BATCH, *tuple(tensor.shape)[1:]),
            dtype=tensor.dtype,
            name=tensor.name.split(":")[0],
        )
        for tensor in model.inputs
    ]
    fixed = keras.models.clone_model(
        model, input_tensors=inputs if len(inputs) > 1 else inputs[0]
    )
    # ``clone_model`` copies the architecture, not the values. Without this the exported model
    # would be an untrained one with the right shape, which is the kind of mistake that passes
    # every structural test and fails the accuracy gate for a reason nobody can find.
    fixed.set_weights(model.get_weights())
    return fixed
