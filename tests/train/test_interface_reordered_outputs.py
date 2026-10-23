"""The case the interface contract exists for: the converter reorders outputs (research R4).

Measured on 2026-10-23: a functional model with two outputs comes out of the converter with them in
reversed order in the subgraph. Feature 006 builds one output, so no manifest reaches this — but the
binding reader must already map each name to the position the file uses, or the first model with
two outputs would bind them crosswise without a word.
"""

from __future__ import annotations

import keras
import numpy as np

from caravan.convert.tflite import convert
from caravan.runtime.flatbuffer import read_bindings


def test_each_name_maps_to_the_position_the_subgraph_actually_uses(tmp_path) -> None:
    from ai_edge_litert import schema_py_generated as schema

    keras.utils.set_random_seed(3)
    inputs = keras.Input(shape=(8, 3), name="frames")
    hidden = keras.layers.Dense(6, activation="relu")(keras.layers.Flatten()(inputs))
    first = keras.layers.Dense(4, activation="softmax")(hidden)
    second = keras.layers.Dense(2, activation="softmax")(hidden)
    model = keras.Model(inputs, {"attack": first, "severity": second})

    generator = np.random.default_rng(0)
    path = tmp_path / "two.tflite"
    path.write_bytes(
        convert(
            model,
            "int8",
            lambda: ([generator.random((1, 8, 3), dtype=np.float32)] for _ in range(16)),
        )
    )

    attack, severity = read_bindings(path, inputs=[], outputs=["attack", "severity"])

    graph = schema.ModelT.InitFromObj(schema.Model.GetRootAs(path.read_bytes(), 0)).subgraphs[0]
    # Each binding's position holds exactly its own tensor, whatever order the converter chose.
    assert int(graph.outputs[attack.position]) == attack.tensor_index
    assert int(graph.outputs[severity.position]) == severity.tensor_index
    assert list(attack.shape) == [1, 4] and list(severity.shape) == [1, 2]
