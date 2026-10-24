"""SC-004: the report's claim about the model matches an independent reading of the file.

This is the test the feature was designed around. The converter prints ``fully_quantize: 0`` for a
model whose every tensor is an integer, so the only trustworthy source is the file — and the only
way to know the report agrees with the file is to read the file here, separately, and compare.
"""

from __future__ import annotations

import json

from caravan.cli.main import EXIT_OK, main
from caravan.stages.quantize import QUANTIZED_MODEL, RECORD
from tests.train.conftest import latest_run


def quantize(manifest, runs, cache, *extra):
    return main(
        ["quantize", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache), *extra]
    )


def test_the_produced_model_is_fully_integer_according_to_the_file(
    fixture_manifest, workspace
) -> None:
    runs, cache = workspace
    assert quantize(fixture_manifest, runs, cache) == EXIT_OK

    from ai_edge_litert.interpreter import Interpreter

    path = latest_run(runs) / QUANTIZED_MODEL
    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    details = interpreter.get_tensor_details()
    boundary = {d["index"] for d in interpreter.get_input_details()} | {
        d["index"] for d in interpreter.get_output_details()
    }
    inside = {d["dtype"].__name__ for d in details if d["index"] not in boundary}

    # Feature 008 (research R5): raw float32 and int32 in, float32 out after a DEQUANTIZE, and
    # integers inside — with one float32 tensor per category, the CAST of its one-hot, on its way
    # into a QUANTIZE (research R3).
    assert inside <= {"int8", "int32", "bool", "float32"}
    floats_inside = [
        d["name"]
        for d in details
        if d["index"] not in boundary and d["dtype"].__name__ == "float32"
    ]
    assert floats_inside and all("Cast" in name for name in floats_inside), floats_inside
    assert {d["dtype"].__name__ for d in interpreter.get_input_details()} == {"float32", "int32"}
    assert interpreter.get_output_details()[0]["dtype"].__name__ == "float32"


def test_the_report_agrees_with_the_file(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    run_dir = latest_run(runs)

    from ai_edge_litert.interpreter import Interpreter

    interpreter = Interpreter(model_path=str(run_dir / QUANTIZED_MODEL))
    interpreter.allocate_tensors()
    from collections import Counter

    counts = Counter(d["dtype"].__name__ for d in interpreter.get_tensor_details())

    claimed = json.loads((run_dir / RECORD).read_text(encoding="utf-8"))["model"]
    assert claimed["dtype_counts"] == dict(sorted(counts.items()))
    assert claimed["fully_integer"] is True
    assert claimed["size_bytes"] == (run_dir / QUANTIZED_MODEL).stat().st_size
    assert [tensor["dtype"] for tensor in claimed["inputs"]] == [
        detail["dtype"].__name__ for detail in interpreter.get_input_details()
    ]


def test_the_quantized_model_is_smaller_than_the_trained_one(fixture_manifest, workspace) -> None:
    # Both numbers, measured. No ratio: a ratio reads as a footprint claim, and the flash a board
    # needs is the analysis stage's figure, not this one's.
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    model = json.loads((latest_run(runs) / RECORD).read_text(encoding="utf-8"))["model"]
    assert model["size_bytes"] < model["trained_size_bytes"]
    assert "ratio" not in json.dumps(model)
