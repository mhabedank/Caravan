"""What ran, so a report can say so. Every framework import is inside a function.

The module is therefore safe to import from the core — and it has to be, because
``caravan.stages.build`` imports it and the layering tests import that.
"""

from __future__ import annotations

import platform
from typing import Any


def framework_record() -> dict[str, Any]:
    """The provenance FR-022 requires: what produced the artifact, and on which interpreter."""
    import keras
    import tensorflow as tf

    return {
        "framework": {"name": "tensorflow", "version": tf.__version__},
        "keras_version": keras.__version__,
        "python": platform.python_version(),
    }


def layer_table(model: Any) -> list[dict[str, Any]]:
    """Name, kind, output shape and parameter count, per layer.

    FR-003 asks for the shape and the parameter count to be *reported*, which means readable by a
    person and by the next stage — so it is an artifact, not a printed line.
    """
    table: list[dict[str, Any]] = []
    for layer in model.layers:
        shape = getattr(layer, "output", None)
        table.append(
            {
                "name": layer.name,
                "kind": type(layer).__name__,
                "output_shape": [
                    None if size is None else int(size)
                    for size in (tuple(shape.shape) if shape is not None else ())
                ],
                "parameters": int(layer.count_params()),
            }
        )
    return table
