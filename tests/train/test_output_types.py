"""``binary`` and ``number`` outputs end to end, each with its own int8 budget (T032, SC-007).

Feature 008, user story 1, scenario 6. The datasets are derived at test time from the committed
fixture (``tests/support.py``), so no dataset is committed: ``is_attack`` is a binary answer to the
same question, and ``payload_mean`` is a number each window's records agree on.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from caravan.cli.main import EXIT_OK, EXIT_RULE, main
from caravan.manifest.errors import RULE_ACCURACY_GATE
from caravan.stages.quantize import ERROR_TABLE
from tests.support import write_binary_dataset, write_number_dataset
from tests.train.conftest import latest_run
from tests.train.test_gate_failure import degrade_the_quantized_model

FEATURES = """input_features:
  - {name: can_id, type: category}
  - {name: dlc, type: number}
  - {name: b0, type: number}
  - {name: b1, type: number}
  - {name: b2, type: number}
"""

COMMON = """
dataset: data/
trainer: {epochs: 40, batch_size: 16, learning_rate: 0.003}
random_seed: 42
export:
  targets: [stm32h743]
  representative_samples: 100
"""

BINARY = (
    """apiVersion: caravan/v0.2
model: {name: picket-binary, version: 0.2.0, template: mlp, params: {hidden: [16]}}
"""
    + FEATURES
    + """output_features:
  - {name: is_attack, type: binary, accuracy_drop_max: 0.05}
preprocessing:
  window_size: 64
  split: {type: stratify}
"""
    + COMMON
)

NUMBER = (
    """apiVersion: caravan/v0.2
model: {name: picket-number, version: 0.2.0, template: mlp, params: {hidden: [16]}}
"""
    + FEATURES
    + """output_features:
  - name: payload_mean
    type: number
    preprocessing: {normalization: zscore}
    loss: {type: mean_squared_error}
    clip: [0, 255]
    mae_increase_max: MAE_BUDGET
preprocessing:
  window_size: 64
"""
    + COMMON
)


def export(manifest: Path, root: Path) -> int:
    return main(
        [
            "export",
            str(manifest),
            "--runs-dir",
            str(root / "runs"),
            "--cache-dir",
            str(root / "cache"),
        ]
    )


@pytest.fixture(scope="module")
def binary_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("binary")
    write_binary_dataset(root / "data")
    (root / "binary.yaml").write_text(BINARY, encoding="utf-8")
    assert export(root / "binary.yaml", root) == EXIT_OK
    return latest_run(root / "runs")


def number_manifest(root: Path, budget: float) -> Path:
    write_number_dataset(root / "data")
    path = root / "number.yaml"
    path.write_text(NUMBER.replace("MAE_BUDGET", str(budget)), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def number_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("number")
    assert export(number_manifest(root, 5.0), root) == EXIT_OK
    return latest_run(root / "runs")


def load(run: Path, name: str) -> dict:
    return json.loads((run / name).read_text(encoding="utf-8"))


# --- binary --------------------------------------------------------------------------------------


def test_a_binary_output_trains_and_its_gate_uses_accuracy(binary_run) -> None:
    report = load(binary_run, "report.json")
    gate = report["quantization"]["gate"]
    assert gate["metric"] == "accuracy" and gate["verdict"] == "pass"
    assert gate["budget"] == 0.05
    assert report["data"]["output"]["fitted"]["true_spelling"] == "yes"
    # The committed fixture's own answer is in the data and read by nothing: visibly ignored.
    assert report["data"]["ignored_columns"] == ["label"]
    accuracy = {m["split"]: m["value"] for m in report["metrics"] if m["name"] == "accuracy"}
    assert accuracy["test"] >= 0.75


def test_a_binary_export_says_threshold_in_the_contract_and_the_header(binary_run) -> None:
    contract = load(binary_run, "model/interface.json")
    (output,) = contract["outputs"]
    assert output["decision"] == "threshold" and output["threshold"] == 0.5
    assert output["dtype"] == "float32" and output["shape"] == [1, 1]
    header = (binary_run / "model" / "model_data.h").read_text(encoding="utf-8")
    assert "constexpr float g_model_data_output_is_attack_threshold = 0.5f;" in header


# --- number --------------------------------------------------------------------------------------


def test_a_number_output_trains_and_its_gate_uses_the_mae_in_the_columns_unit(number_run) -> None:
    report = load(number_run, "report.json")
    gate = report["quantization"]["gate"]
    assert gate["metric"] == "mae" and gate["verdict"] == "pass"
    assert gate["budget"] == 5.0
    record = load(number_run, "quantization.json")
    assert set(record["mae"]) >= {"trained", "converted", "quantized", "mae_increase", "threshold"}
    names = {metric["name"] for metric in report["metrics"] if metric["split"] == "test"}
    assert names == {"mae", "mse", "rmse", "r2"}
    gates = {entry["name"]: entry for entry in report["gates"]}
    assert gates["mae"]["result"] == "pass"


def test_the_exported_number_is_float32_in_the_columns_unit_and_clipped(number_run) -> None:
    from ai_edge_litert.interpreter import Interpreter

    contract = load(number_run, "model/interface.json")
    (output,) = contract["outputs"]
    assert output["decision"] == "value" and output["dtype"] == "float32"
    assert output["clip"] == [0.0, 255.0]

    runner = Interpreter(
        model_path=str(number_run / "model" / "model.tflite")
    ).get_signature_runner()
    window = contract["window_size"]
    ordinary = {
        "can_id": np.full((1, window), 291, np.int32),
        "dlc": np.full((1, window), 8.0, np.float32),
        **{name: np.full((1, window), 60.0, np.float32) for name in ("b0", "b1", "b2")},
    }
    value = float(runner(**ordinary)["payload_mean"][0, 0])
    assert 20.0 < value < 120.0  # in the column's unit, near the mean it was trained on
    extreme = {**ordinary, **{name: np.full((1, window), -1e4, np.float32) for name in ("b0",)}}
    clipped = float(runner(**extreme)["payload_mean"][0, 0])
    assert 0.0 <= clipped <= 255.0


def test_a_failed_number_gate_writes_the_per_layer_table(tmp_path, monkeypatch) -> None:
    degrade_the_quantized_model(monkeypatch)
    manifest = number_manifest(tmp_path, 5.0)
    assert export(manifest, tmp_path) == EXIT_RULE
    run = latest_run(tmp_path / "runs")
    report = load(run, "report.json")
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_ACCURACY_GATE)
    assert finding["path"] == "output_features[0].mae_increase_max"
    assert "mean absolute error" in finding["problem"]
    assert (run / ERROR_TABLE).is_file()
    assert load(run, "quantization.json")["layer_errors"]
