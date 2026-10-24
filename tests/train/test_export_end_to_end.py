"""The acceptance criterion: the pilot manifest exports end to end on the committed fixture."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.export import c_array
from caravan.stages.export import (
    ARRAY_HEADER,
    ARRAY_SOURCE,
    MODEL,
    RECORD,
    RESOLVER,
    runner_path,
)
from caravan.stages.quantize import QUANTIZED_MODEL
from tests.train.conftest import latest_run

BUDGET_SECONDS = 30

#: The boards the fixture manifest names.
TARGETS = ("s32k144", "stm32h743", "esp32")

#: What the typed features add in front of every template (feature 008): a number's QUANTIZE, SUB
#: and MUL, a category's EQUAL, CAST, RELU, SUM, SUB and CONCATENATION, and a DEQUANTIZE at the
#: output. Measured 2026-10-24.
OPERATORS = [
    "QUANTIZE", "SUB", "MUL", "RESHAPE", "EQUAL", "CAST", "RELU", "SUM", "CONCATENATION",
    "FULLY_CONNECTED", "SOFTMAX", "DEQUANTIZE",
]  # fmt: skip


def export(manifest, runs, cache, *extra):
    return main(
        ["export", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache), *extra]
    )


@pytest.fixture
def exported(fixture_manifest, workspace):
    runs, cache = workspace
    started = time.perf_counter()
    assert export(fixture_manifest, runs, cache) == EXIT_OK
    elapsed = time.perf_counter() - started
    run = latest_run(runs)
    return run, json.loads((run / RECORD).read_text(encoding="utf-8")), elapsed, (runs, cache)


def test_every_promised_artifact_is_written(exported) -> None:
    run, _record, _elapsed, _workspace = exported
    promised = [MODEL, ARRAY_SOURCE, ARRAY_HEADER, RESOLVER, RECORD]
    promised += [runner_path(target) for target in TARGETS]
    missing = [name for name in promised if not (run / name).is_file()]
    assert not missing, f"the export did not write: {missing}"


def test_the_exported_model_is_the_model_the_gate_measured(exported) -> None:
    # The claim the whole feature rests on: one graph, measured and shipped.
    run, record, _elapsed, _workspace = exported
    assert (run / MODEL).read_bytes() == (run / QUANTIZED_MODEL).read_bytes()
    assert record["source_model"]["same_bytes_as"] == MODEL


def test_the_c_array_round_trips_to_the_model(exported) -> None:
    run, _record, _elapsed, _workspace = exported
    source = (run / ARRAY_SOURCE).read_text(encoding="utf-8")
    assert c_array.read_back(source) == (run / MODEL).read_bytes()
    length = len((run / MODEL).read_bytes())
    assert f"g_model_data_size = {length};" in (run / ARRAY_HEADER).read_text(encoding="utf-8")


def test_the_graph_is_the_fixed_batch_one(exported) -> None:
    # Twelve operators in 32 nodes — the template's three and the typed features' own — and none
    # of the shape plumbing a dynamic batch produces.
    _run, record, _elapsed, _workspace = exported
    graph = record["graph"]
    names = [operator["name"] for operator in graph["operators"]]
    assert names == OPERATORS
    assert graph["distinct_operators"] == 12
    assert graph["nodes"] == 32
    assert graph["input_shape"][0] == 1
    for plumbing in ("SHAPE", "STRIDED_SLICE", "PACK"):
        assert plumbing not in names


def test_the_resolver_names_exactly_those_operators(exported) -> None:
    run, record, _elapsed, _workspace = exported
    header = (run / RESOLVER).read_text(encoding="utf-8")
    assert "MicroMutableOpResolver<12>" in header
    for method in ("AddReshape", "AddFullyConnected", "AddSoftmax", "AddEqual", "AddQuantize"):
        assert header.count(f"resolver.{method}();") == 1
    assert len(re.findall(r"resolver\.Add\w+\(", header)) == 12
    assert record["graph"]["distinct_operators"] == 12


def test_coverage_is_recorded_for_every_operator_and_every_target(exported) -> None:
    _run, record, _elapsed, _workspace = exported
    verdicts = record["coverage"]
    assert len(verdicts) == 12 * len(TARGETS)
    for verdict in verdicts:
        assert verdict["source"] and verdict["read_on"]
    falling_back = {v["operator"] for v in verdicts if not v["accelerated"]}
    assert falling_back == {
        "CAST", "CONCATENATION", "DEQUANTIZE", "EQUAL", "QUANTIZE", "RELU", "RESHAPE", "SUB", "SUM",
    }  # fmt: skip


def test_every_artifact_carries_its_size_and_digest(exported) -> None:
    import hashlib

    run, record, _elapsed, _workspace = exported
    for artifact in record["artifacts"]:
        path = run / artifact["path"]
        assert path.is_file()
        assert artifact["bytes"] == path.stat().st_size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert artifact["digest"] == f"sha256:{digest}"


def test_the_requirements_say_what_the_author_must_supply(exported) -> None:
    _run, record, _elapsed, _workspace = exported
    for target in TARGETS:
        requirement = record["requirements"][target]
        assert requirement["runtime"] == "tflm"
        assert requirement["operators"] == OPERATORS
        assert requirement["working_memory_floor_bytes"] > 0
        assert "peak simultaneously live" in requirement["floor_method"]
        assert "not the figure" in requirement["floor_is_not_the_requirement"]


def test_it_exports_within_the_budget(exported) -> None:
    _run, _record, elapsed, _workspace = exported
    assert elapsed < BUDGET_SECONDS, f"{elapsed:.1f}s is over the {BUDGET_SECONDS}s budget"


def test_two_exports_of_one_model_are_identical(fixture_manifest, workspace) -> None:
    # With --fresh, so this proves determinism rather than that the cache works.
    runs, cache = workspace
    assert export(fixture_manifest, runs, cache) == EXIT_OK
    first = latest_run(runs)
    assert export(fixture_manifest, runs, cache, "--fresh") == EXIT_OK
    second = latest_run(runs)
    assert first != second
    for name in (ARRAY_SOURCE, ARRAY_HEADER, RESOLVER, *(runner_path(t) for t in TARGETS)):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


@pytest.mark.skipif(
    subprocess.run(["which", "g++"], capture_output=True, check=False).returncode != 0,
    reason="no host C++ compiler",
)
def test_the_exported_array_compiles(exported, tmp_path) -> None:
    # The generated pair, from a real export rather than from a synthetic blob.
    run, _record, _elapsed, _workspace = exported
    work = tmp_path / "compile"
    work.mkdir()
    for name in (ARRAY_SOURCE, ARRAY_HEADER):
        (work / Path(name).name).write_bytes((run / name).read_bytes())
    result = subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Werror", "-c", "model_data.cc", "-o", "model_data.o"],
        cwd=work,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
