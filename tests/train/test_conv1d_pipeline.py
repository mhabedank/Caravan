"""The acceptance criterion: the conv1d fixture runs the whole pipeline end to end.

Build, train, quantize, export — on the committed synthetic dataset, with the accuracy gate
judging. No real data, no published model: this proves the template works inside the pipeline, and
nothing about what a model built this way would achieve on anybody's real signals.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.stages.export import MODEL, RECORD, RESOLVER
from caravan.stages.quantize import QUANTIZED_MODEL
from caravan.stages.quantize import RECORD as QUANTIZE_RECORD
from tests.train.conftest import latest_run

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
CONV1D = FIXTURES / "manifests" / "valid" / "picket-conv1d-fixture.yaml"

#: Measured on the first real run of this fixture, 2026-10-22: the reducing head's operator set.
EXPECTED_OPERATORS = ["RESHAPE", "CONV_2D", "MAX_POOL_2D", "MEAN", "FULLY_CONNECTED", "SOFTMAX"]


@pytest.fixture
def exported(workspace):
    runs, cache = workspace
    code = main(["export", str(CONV1D), "--runs-dir", str(runs), "--cache-dir", str(cache)])
    assert code == EXIT_OK
    run = latest_run(runs)
    return run, json.loads((run / RECORD).read_text(encoding="utf-8"))


def test_the_whole_pipeline_runs(exported) -> None:
    run, _record = exported
    for artifact in ("model/built.keras", "model/trained.keras", QUANTIZED_MODEL, MODEL, RESOLVER):
        assert (run / artifact).is_file(), artifact


def test_the_accuracy_gate_judged_and_passed(exported) -> None:
    run, _record = exported
    record = json.loads((run / QUANTIZE_RECORD).read_text(encoding="utf-8"))
    assert record["accuracy"]["verdict"] == "pass"
    # Three accuracies and two differences, as for the other template: the gate is shared code.
    for key in ("trained", "converted", "quantized", "conversion_drop", "quantization_drop"):
        assert key in record["accuracy"]


def test_the_operator_set_is_the_convolutional_one(exported) -> None:
    _run, record = exported
    assert [o["name"] for o in record["graph"]["operators"]] == EXPECTED_OPERATORS
    assert record["graph"]["distinct_operators"] == 6


def test_the_resolver_names_each_operator_once_in_the_runtimes_spelling(exported) -> None:
    run, _record = exported
    header = (run / RESOLVER).read_text(encoding="utf-8")
    for method in (
        "AddReshape",
        "AddConv2D",
        "AddMaxPool2D",
        "AddMean",
        "AddFullyConnected",
        "AddSoftmax",
    ):
        assert header.count(f"resolver.{method}();") == 1, method
    assert len(re.findall(r"resolver\.Add\w+\(", header)) == 6
    assert "MicroMutableOpResolver<6>" in header


def test_the_reduction_is_recorded_as_a_fallback_on_every_board(exported) -> None:
    _run, record = exported
    falling_back = {
        (v["target"], v["operator"]) for v in record["coverage"] if not v["accelerated"]
    }
    for target in ("s32k144", "stm32h743", "esp32"):
        assert (target, "MEAN") in falling_back
        assert (target, "RESHAPE") in falling_back
    for verdict in record["coverage"]:
        assert verdict["source"] and verdict["read_on"]


def test_no_stage_needed_a_special_case(exported) -> None:
    # The whole run went through the same stages the dense template uses. Asserted structurally
    # elsewhere (no identifier literal in any stage); here it is asserted by the run existing.
    run, record = exported
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    assert [stage["name"] for stage in report["stages"]] == ["build", "train", "quantize", "export"]
    assert record["graph"]["nodes"] == 8
