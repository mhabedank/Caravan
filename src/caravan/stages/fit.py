"""The fit stage: the built model's lower bounds against every target board, before training.

Core module — Keras is imported inside the function. The arithmetic is ``caravan.targets.fit``;
this module only reduces the built model's layers to the records it needs.

Its upstream is ``build`` and nothing reads its key: ``train`` keeps ``build`` as its upstream, so
adding or removing a target board re-runs this stage and the export and never a training
(Principle III, research R6 of feature 006).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from caravan.stages.base import StageContext, StageFunction, StageInputs, StageSpec
from caravan.stages.build import load_built_model, require_framework
from caravan.targets.fit import IMAGE_ELEMENT_BYTES, LayerRecord, check
from caravan.targets.registry import default_registry

FIT_RECORD = "model/fit.json"

SPEC = StageSpec(
    name="fit",
    # Feature 010: the input features' types too, because an image input is 1 byte per element on
    # the device and 4 in the Keras model; the built model alone cannot say which input is one.
    reads=("export.targets", "export.quantization", "input_features"),
    # Everything else the floors depend on is in the built model, the upstream's result.
    reads_dataset=False,
    upstream="build",
    artifacts=(FIT_RECORD,),
)


def _elements(shape: Any) -> int:
    """Elements of one sample: the shape without its batch dimension."""
    return int(math.prod(int(dimension) for dimension in tuple(shape)[1:]))


def _tensor_elements(tensors: Any) -> int:
    """Elements of one or several tensors, as a layer with several inputs has."""
    if isinstance(tensors, list | tuple):
        return sum(_elements(tensor.shape) for tensor in tensors)
    return _elements(tensors.shape)


def layer_records(model: Any, images: frozenset[str] = frozenset()) -> tuple[LayerRecord, ...]:
    """The built model's layers, as the records the floors are computed from.

    Feature 008 adds three kinds: every model input (``input``, at 4 bytes per element), every
    category's vocabulary (``constant``, int32 in flash), and the concatenation of the features
    (``concat``). The embedding of a category is a ``Dense`` and counts as one.
    """
    import keras

    from caravan.templates.builders.preprocessing import VocabularyOneHot

    dense = (keras.layers.Dense,)
    # A depthwise convolution is not a ``Conv2D`` in Keras 3, and would otherwise be counted as
    # excluded — its weights and its activations lost from both floors (feature 010, R4).
    conv = (keras.layers.Conv1D, keras.layers.Conv2D, keras.layers.DepthwiseConv2D)
    pooling = (
        keras.layers.MaxPooling1D,
        keras.layers.MaxPooling2D,
        keras.layers.AveragePooling1D,
        keras.layers.AveragePooling2D,
        keras.layers.GlobalAveragePooling1D,
        keras.layers.GlobalAveragePooling2D,
        keras.layers.GlobalMaxPooling1D,
        keras.layers.GlobalMaxPooling2D,
    )
    records: list[LayerRecord] = []
    for layer in model.layers:
        if isinstance(layer, keras.layers.InputLayer):
            records.append(
                LayerRecord(
                    kind="input",
                    name=layer.name,
                    output_elements=_tensor_elements(layer.output),
                    **({"element_bytes": IMAGE_ELEMENT_BYTES} if layer.name in images else {}),
                )
            )
            continue
        if isinstance(layer, VocabularyOneHot):
            kind, kernel, bias = "constant", len(layer.codes), 0
        elif isinstance(layer, keras.layers.Concatenate):
            kind, kernel, bias = "concat", 0, 0
        elif isinstance(layer, dense + conv):
            kind = "dense" if isinstance(layer, dense) else "conv"
            kernel = int(math.prod(layer.kernel.shape))
            bias = int(math.prod(layer.bias.shape)) if layer.use_bias else 0
        elif isinstance(layer, pooling):
            kind, kernel, bias = "pooling", 0, 0
        else:
            # Normalisation, activation, reshaping, dropout: may vanish, be fused or run in place.
            kind, kernel, bias = "excluded", 0, 0
        records.append(
            LayerRecord(
                kind=kind,
                name=layer.name,
                kernel_elements=kernel,
                bias_elements=bias,
                input_elements=_tensor_elements(layer.input),
                output_elements=_tensor_elements(layer.output),
            )
        )
    return tuple(records)


def stage(context: StageContext) -> StageFunction:
    """The stage function, bound to this run."""

    def run(inputs: StageInputs, out_dir: Path) -> None:
        require_framework("build")
        registry = default_registry()
        boards = [registry.get(identifier) for identifier in inputs["export.targets"]]
        model = load_built_model(context.run_dir)
        images = frozenset(
            feature["name"] for feature in inputs["input_features"] if feature["type"] == "image"
        )
        record = check(layer_records(model, images), inputs["export.quantization"], boards)
        (out_dir / "model").mkdir(parents=True, exist_ok=True)
        (out_dir / FIT_RECORD).write_text(
            json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return run
