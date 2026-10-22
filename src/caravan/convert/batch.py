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

    Idempotent: a model already fixed to one is returned unchanged, so a second conversion of the
    same model is not a second clone.

    A model fixed to some *other* batch is refused rather than reshaped. No template produces one,
    and quietly turning somebody's batch of 32 into a batch of 1 would change what their model is.
    """
    shape = tuple(model.inputs[0].shape)
    batch = shape[0]
    if batch == DEPLOYED_BATCH:
        return model
    if batch is not None:
        raise ValueError(
            f"the model's input batch is fixed to {batch}, and converting for a target needs a "
            f"batch of {DEPLOYED_BATCH}; build the model with an undetermined batch and let the "
            "conversion fix it"
        )

    fixed = keras.models.clone_model(
        model,
        input_tensors=keras.layers.Input(
            batch_shape=(DEPLOYED_BATCH, *shape[1:]),
            dtype=model.inputs[0].dtype,
            name=model.inputs[0].name,
        ),
    )
    # ``clone_model`` copies the architecture, not the values. Without this the exported model
    # would be an untrained one with the right shape, which is the kind of mistake that passes
    # every structural test and fails the accuracy gate for a reason nobody can find.
    fixed.set_weights(model.get_weights())
    return fixed
