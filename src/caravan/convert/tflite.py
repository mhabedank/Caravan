"""The converter's options, one set per quantization setting.

Imports the training framework at module level, which makes this an extra-only module by design:
importing it is already a statement that the conversion half is installed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import tensorflow as tf

from caravan.manifest.errors import RULE_CONVERSION_FAILED, run_rule_error

#: A callable yielding one calibration sample at a time, as the converter wants it, or ``None``
#: for the settings that calibrate against nothing.
Representative = Callable[[], Iterator[list[Any]]] | None


def convert(model: Any, setting: str, representative: Representative = None) -> bytes:
    """Convert a trained model, and return the serialised result.

    ``from_keras_model`` rather than an explicit export: both paths were measured and produce
    byte-identical output (research R1), and this one leaves no temporary directory of ours behind.

    ``representative`` is ``None`` for ``float16`` and ``none``. That is valid input, not an
    oversight: the schema makes ``dataset.representative_samples`` optional and rule CF-4 demands it
    only for ``int8``, so a manifest asking for float16 legitimately has no calibration count.
    """
    # The whole conversion is inside the guard below, construction included: a converter that
    # refuses the *model* fails here rather than at ``convert()``, and letting that escape would
    # report a defect in caravan for something the author needs to see about their model.
    try:
        return _convert(model, setting, representative)
    except Exception as error:  # the converter raises its own hierarchy; the text is what matters
        run_rule_error(
            RULE_CONVERSION_FAILED,
            "export.quantization",
            f"converting the trained model to {setting} failed: {error}",
            found=setting,
        )


def _convert(model: Any, setting: str, representative: Representative) -> bytes:
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    if setting == "int8":
        if representative is None:
            raise ValueError("int8 conversion needs a representative dataset to calibrate against")
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.representative_dataset = representative
        # Restricting the operator set is what makes this a *full* integer conversion rather than
        # a mixed one: without it the converter may leave an operator in float and still report
        # success, and the model would then not run on a runtime built for integers only.
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.int8
        converter.inference_output_type = tf.int8
    elif setting == "float16":
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]
    elif setting != "none":  # pragma: no cover - the schema admits exactly three
        raise ValueError(f"unknown quantization setting: {setting!r}")

    return converter.convert()
