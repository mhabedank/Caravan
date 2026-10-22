"""The quantized model of a run is the fixed-batch graph.

Feature 003 measured a model; feature 004 changed what that model is. The change belongs in the
conversion rather than after it, so that one graph is measured and shipped — and that makes this a
test of the *quantize* stage, where the conversion lives, not of the export.
"""

from __future__ import annotations

import json

from caravan.cli.main import EXIT_OK, main
from caravan.runtime.flatbuffer import inspect_graph
from caravan.stages.quantize import QUANTIZED_MODEL, RECORD
from tests.train.conftest import latest_run

#: What a dynamic batch costs: four operators to compute a shape that never varies.
PLUMBING = ("SHAPE", "STRIDED_SLICE", "PACK")


def test_the_quantized_model_has_a_batch_of_one(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    assert (
        main(
            ["quantize", str(fixture_manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)]
        )
        == EXIT_OK
    )
    graph = inspect_graph(latest_run(runs) / QUANTIZED_MODEL)
    assert graph.input_shape[0] == 1


def test_the_shape_plumbing_is_gone(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    assert (
        main(
            ["quantize", str(fixture_manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)]
        )
        == EXIT_OK
    )
    graph = inspect_graph(latest_run(runs) / QUANTIZED_MODEL)
    names = [operator.name for operator in graph.operators]
    assert names == ["RESHAPE", "FULLY_CONNECTED", "SOFTMAX"]
    for operator in PLUMBING:
        assert operator not in names, (
            f"{operator} is a dynamic-batch artefact; the conversion fixes the batch to one"
        )


def test_the_record_still_describes_what_was_measured(fixture_manifest, workspace) -> None:
    # The point of fixing the batch inside the conversion: the gate's numbers and the exported
    # model are about the same graph, so the record's size is the fixed-batch model's size.
    runs, cache = workspace
    assert (
        main(
            ["quantize", str(fixture_manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)]
        )
        == EXIT_OK
    )
    run = latest_run(runs)
    record = json.loads((run / RECORD).read_text(encoding="utf-8"))
    assert record["model"]["size_bytes"] == (run / QUANTIZED_MODEL).stat().st_size
    assert record["accuracy"]["verdict"] == "pass"
