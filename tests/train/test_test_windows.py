"""Test windows for a board: selection, host reference, record, cache (feature 009, T007).

On the committed fixture. The claim tested throughout: the windows come from the test part the
quantize stage measured, and the host's answers are the quantized model's, run by the measurement
runtime — so a board that agrees with them agrees with what the accuracy gate passed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.stages.export import MODEL, RECORD, TEST_WINDOWS
from tests.support import PILOT_FIXTURE, SYNTHETIC_DATASET, write_number_dataset
from tests.train.conftest import latest_run

pytest.importorskip("ai_edge_litert")


def manifest_with(directory: Path, count: int | None, *, text: str | None = None) -> Path:
    """The pilot fixture with ``export.test_windows`` set, pointed at the committed data."""
    source = text if text is not None else PILOT_FIXTURE.read_text(encoding="utf-8")
    source = re.sub(r"^dataset: .*$", f"dataset: {SYNTHETIC_DATASET}", source, flags=re.MULTILINE)
    source = re.sub(r"^  test_windows: .*\n", "", source, flags=re.MULTILINE)
    if count is not None:
        source = source.rstrip("\n") + f"\n  test_windows: {count}\n"
    path = directory / "windows.yaml"
    path.write_text(source, encoding="utf-8")
    return path


def export(manifest: Path, runs: Path, cache: Path) -> tuple[int, Path]:
    code = main(["export", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])
    return code, latest_run(runs)


def record_of(run: Path) -> dict:
    return json.loads((run / RECORD).read_text(encoding="utf-8"))


def report_of(run: Path) -> dict:
    return json.loads((run / "report.json").read_text(encoding="utf-8"))


def outcomes(run: Path) -> dict[str, str]:
    return {stage["name"]: stage["outcome"] for stage in report_of(run)["stages"]}


def header_array(text: str, name: str) -> list[float]:
    body = re.search(rf"{name}\[kCount\] = \{{(.*?)\}};", text, re.DOTALL)
    assert body, f"no {name} in the header"
    return [float(value.rstrip("f")) for value in body.group(1).replace("\n", " ").split(",")]


@pytest.fixture
def eight(workspace, tmp_path):
    runs, cache = workspace
    code, run = export(manifest_with(tmp_path, 8), runs, cache)
    assert code == EXIT_OK
    return run, (runs, cache)


def test_the_header_is_written_and_recorded(eight) -> None:
    run, _ = eight
    assert (run / TEST_WINDOWS).is_file()
    record = record_of(run)
    listed = [artifact["path"] for artifact in record["artifacts"]]
    assert TEST_WINDOWS in listed
    windows = record["test_windows"]
    assert windows["asked"] == 8
    assert windows["written"] == 8
    assert windows["available"] >= 8
    assert windows["split"] == "test"
    assert windows["selection"] == "round-robin by class"
    assert windows["score_step"] > 0
    assert set(windows["per_class"]) == {"dos", "fuzzy", "normal", "replay"}
    assert sum(windows["per_class"].values()) == 8


def test_the_available_windows_are_the_gates_test_part(eight) -> None:
    run, _ = eight
    quantization = json.loads((run / "quantization.json").read_text(encoding="utf-8"))
    assert record_of(run)["test_windows"]["available"] == quantization["gate"]["samples"]


def test_every_class_comes_before_any_comes_twice(eight) -> None:
    run, _ = eight
    expected = header_array((run / TEST_WINDOWS).read_text(encoding="utf-8"), "kExpected")
    assert len(set(expected[:4])) == 4


def test_the_host_reference_is_the_quantized_model(eight) -> None:
    from caravan.runtime.measure import run_model

    run, _ = eight
    text = (run / TEST_WINDOWS).read_text(encoding="utf-8")
    decisions = header_array(text, "kHostDecision")
    rows = re.search(r"kHostScores\[kCount\]\[kOutputCount\] = \{(.*?)\n\};", text, re.DOTALL)
    assert rows
    scores = np.array(
        [
            [float(v.rstrip("f")) for v in row.strip(" {},").split(",")]
            for row in rows.group(1).strip().splitlines()
        ],
        dtype=np.float32,
    )
    assert decisions == [float(index) for index in np.argmax(scores, axis=1)]

    # Run the windows of the header through the exported model on the host: the same scores.
    inputs = {}
    for name, c_type in (("can_id", "int32_t"), ("dlc", "float"), ("b0", "float")):
        table = re.search(rf"{c_type} kInput_{name}\[kCount\]\[64\] = \{{(.*?)\n\}};", text, re.S)
        assert table, name
        rows_text = table.group(1).strip().splitlines()
        values = [[float(v.rstrip("f")) for v in r.strip(" {},").split(",")] for r in rows_text]
        inputs[name] = np.array(values, dtype=np.int32 if c_type == "int32_t" else np.float32)
    for name in ("b1", "b2"):
        table = re.search(rf"float kInput_{name}\[kCount\]\[64\] = \{{(.*?)\n\}};", text, re.S)
        assert table, name
        rows_text = table.group(1).strip().splitlines()
        values = [[float(v.rstrip("f")) for v in r.strip(" {},").split(",")] for r in rows_text]
        inputs[name] = np.array(values, dtype=np.float32)
    again = run_model(run / MODEL, inputs, "label")
    assert np.array_equal(again, scores)


def test_no_windows_asked_writes_no_header(workspace, tmp_path) -> None:
    runs, cache = workspace
    code, run = export(manifest_with(tmp_path, None), runs, cache)
    assert code == EXIT_OK
    assert not (run / TEST_WINDOWS).exists()
    assert "test_windows" not in record_of(run)


def test_asking_for_more_than_there_are_writes_all_and_says_so(workspace, tmp_path) -> None:
    runs, cache = workspace
    code, run = export(manifest_with(tmp_path, 64), runs, cache)
    assert code == EXIT_OK
    windows = record_of(run)["test_windows"]
    assert windows["asked"] == 64
    assert windows["written"] == windows["available"] < 64


def test_changing_only_the_count_reruns_only_the_export(eight, tmp_path) -> None:
    _, (runs, cache) = eight
    code, run = export(manifest_with(tmp_path, 4), runs, cache)
    assert code == EXIT_OK
    stages = outcomes(run)
    assert stages["export"] == "produced"
    assert all(stages[name] == "reused" for name in ("build", "train", "quantize"))
    assert record_of(run)["test_windows"]["written"] == 4

    code, run = export(manifest_with(tmp_path, 4), runs, cache)
    assert code == EXIT_OK
    assert outcomes(run)["export"] == "reused"


def test_a_number_output_takes_test_order_and_float_expectations(workspace, tmp_path) -> None:
    runs, cache = workspace
    write_number_dataset(tmp_path / "data")
    text = (
        "apiVersion: caravan/v0.2\n"
        "model: {name: picket-number, version: 0.2.0, template: mlp, params: {hidden: [16]}}\n"
        "input_features:\n"
        "  - {name: can_id, type: category}\n"
        "  - {name: dlc, type: number}\n"
        "  - {name: b0, type: number}\n"
        "  - {name: b1, type: number}\n"
        "  - {name: b2, type: number}\n"
        "output_features:\n"
        "  - name: payload_mean\n"
        "    type: number\n"
        "    preprocessing: {normalization: zscore}\n"
        "    mae_increase_max: 50\n"
        "preprocessing:\n"
        "  window_size: 64\n"
        f"dataset: {tmp_path / 'data'}\n"
        "trainer: {epochs: 5, batch_size: 16, learning_rate: 0.003}\n"
        "random_seed: 42\n"
        "export:\n"
        "  targets: [esp32]\n"
        "  representative_samples: 100\n"
        "  test_windows: 3\n"
    )
    manifest = tmp_path / "number.yaml"
    manifest.write_text(text, encoding="utf-8")
    code, run = export(manifest, runs, cache)
    assert code == EXIT_OK
    windows = record_of(run)["test_windows"]
    assert windows["selection"] == "test order"
    assert windows["per_class"] == {}
    header = (run / TEST_WINDOWS).read_text(encoding="utf-8")
    assert "kOutputType = kNumber" in header
    expected = header_array(header, "kExpected")
    assert len(expected) == 3
    assert any(value != int(value) for value in expected)
