"""Anomaly detection from normal data, from manifest to export (feature 010, User Story 1)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_RULE, main
from caravan.manifest.errors import (
    RULE_ACCURACY_GATE,
    RULE_GATE_UNMEASURABLE,
    RULE_NOTHING_NORMAL,
)
from caravan.stages.quantize import QUANTIZED_MODEL
from tests.train.conftest import latest_run

REPOSITORY = Path(__file__).resolve().parents[2]
EXAMPLE = REPOSITORY / "examples" / "anomaly-autoencoder.yaml"
DATASET = REPOSITORY / "tests" / "fixtures" / "datasets" / "anomaly" / "records.csv"


def run(command: str, manifest: Path, workspace) -> int:
    runs, cache = workspace
    return main([command, str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])


def findings(workspace) -> list[dict]:
    runs, _ = workspace
    return json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))["findings"]


def number(name: str) -> dict:
    return {
        "name": name,
        "type": "number",
        "preprocessing": {"fitted": {"shift": 0.0, "scale": 1.0, "fill": 0.0}},
    }


def test_hum_fans_architecture_has_its_parameter_count() -> None:
    # The zoo's hand-built hum-fan: 5 x 40 log-mel frames, encoder 64, 64, code 8, decoder 64, 64
    # (configs/condition-monitoring/sound-anomaly/hum-fan.yaml in the zoo). 35,280 parameters:
    # 200*64+64, 64*64+64, 64*8+8, 8*64+64, 64*64+64, 64*200+200 (SC-003).
    from caravan.templates.builders import load_builder
    from caravan.templates.builders.frontend import build_model

    output = {
        "name": "condition",
        "type": "anomaly",
        "preprocessing": {"fitted": {"normal_label": "normal"}},
    }
    model = build_model(
        load_builder("autoencoder"),
        {"encoder": [64, 64], "code": 8},
        [number(f"mel{index}") for index in range(40)],
        output,
        5,
    )
    assert model.count_params() == 35_280
    assert tuple(model.outputs[0].shape) == (None, 1)


@pytest.fixture(scope="module")
def exported(tmp_path_factory) -> Path:
    """One export of the example, shared: training is the slow part, and every check reads it."""
    import os

    root = tmp_path_factory.mktemp("anomaly")
    previous = Path.cwd()
    os.chdir(root)
    try:
        assert run("export", EXAMPLE, (root / "runs", root / "cache")) == 0
    finally:
        os.chdir(previous)
    return latest_run(root / "runs")


def test_training_learned_from_normal_windows_only(exported) -> None:
    metrics = json.loads((exported / "metrics.json").read_text(encoding="utf-8"))
    dataset = metrics["dataset"]
    normal_in_train = dataset["split_per_label"]["normal"]["train"]
    assert dataset["training_windows"] == normal_in_train < dataset["split"]["train"]
    by_name = {(m["name"], m["split"]): m["value"] for m in metrics["metrics"]}
    assert by_name[("auc", "test")] >= 0.9
    assert by_name[("abnormal_windows", "test")] > 0


def test_the_gate_judges_the_auc_and_the_threshold_comes_from_int8_normals(exported) -> None:
    record = json.loads((exported / "quantization.json").read_text(encoding="utf-8"))
    gate = record["gate"]
    assert (gate["metric"], gate["verdict"]) == ("auc", "pass")
    # SC-004: both separations and the drop between them are stated.
    assert {"converted", "quantized", "quantization_drop"} <= set(record["auc"])
    assert record["auc"]["normal"] > 0 and record["auc"]["abnormal"] > 0
    threshold = record["threshold"]
    assert threshold["rule"] == "percentile" and threshold["percentile"] == 95.0
    assert threshold["computed_on"].startswith("int8 scores")
    assert 0.0 <= record["detection"]["false_alarm_rate"] <= 1.0


def test_the_contract_gives_the_decision_from_one_comparison(exported) -> None:
    # SC-005: the score is the output, and the contract says what to compare it with.
    contract = json.loads((exported / "model" / "interface.json").read_text(encoding="utf-8"))
    assert contract["contract_version"] == 3
    (output,) = contract["outputs"]
    record = json.loads((exported / "quantization.json").read_text(encoding="utf-8"))
    assert output["type"] == "anomaly"
    assert output["decision"] == "threshold"
    assert output["abnormal_when"] == "score >= threshold"
    assert output["threshold"] == record["threshold"]["value"]
    assert output["shape"] == [1, 1]
    header = (exported / "model" / "model_data.h").read_text(encoding="utf-8")
    assert "_output_condition_threshold" in header
    windows = (exported / "model" / "test_windows.h").read_text(encoding="utf-8")
    assert "kOutputType = kAnomaly" in windows


def test_every_operator_is_resolvable_and_covered(exported) -> None:
    from caravan.export.methods import method_for

    record = json.loads((exported / "export.json").read_text(encoding="utf-8"))
    operators = [operator["name"] for operator in record["graph"]["operators"]]
    assert "SQUARED_DIFFERENCE" in operators
    assert all(method_for(name) for name in operators)
    # SC-007: a coverage verdict for every operator on every board.
    covered = {(verdict["target"], verdict["operator"]) for verdict in record["coverage"]}
    assert covered == {
        (board, name) for board in ("s32k144", "stm32h743", "esp32") for name in operators
    }


def degrade_the_ranking(monkeypatch) -> None:
    """Turn the quantized model's scores upside down: the AUC of the int8 model becomes 1 - AUC."""
    from caravan.runtime import measure as measure_module

    real = measure_module.run_model

    def reversed_for_the_quantized_model(path, *args, **kwargs):
        result = real(path, *args, **kwargs)
        return -result if "quantized" in path.name else result

    monkeypatch.setattr(measure_module, "run_model", reversed_for_the_quantized_model)


def test_a_lost_separation_fails_the_gate_and_leaves_no_model(workspace, monkeypatch) -> None:
    degrade_the_ranking(monkeypatch)
    assert run("quantize", EXAMPLE, workspace) == EXIT_RULE
    finding = next(f for f in findings(workspace) if f.get("rule") == RULE_ACCURACY_GATE)
    assert finding["path"] == "output_features[0].auc_drop_max"
    runs, _ = workspace
    assert not (latest_run(runs) / QUANTIZED_MODEL).exists()


def copy_dataset(destination: Path, transform) -> Path:
    """The anomaly fixture with each row passed through ``transform(index, row)``."""
    destination.mkdir(parents=True, exist_ok=True)
    with DATASET.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    header, body = rows[0], rows[1:]
    out = [transform(index, header, row) for index, row in enumerate(body)]
    with (destination / "records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(out[0][0])
        writer.writerows(row for _, row in out)
    return destination


def manifest_for(tmp_path: Path, data: Path, split: str | None = None) -> Path:
    text = EXAMPLE.read_text(encoding="utf-8").replace(
        "dataset: ../tests/fixtures/datasets/anomaly", f"dataset: {data}"
    )
    if split is not None:
        text = text.replace(
            "split: {type: stratify, column: condition, probabilities: [0.7, 0.15, 0.15]}", split
        )
    path = tmp_path / "anomaly.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_no_normal_value_in_the_data_is_refused(tmp_path, workspace) -> None:
    def rename(index, header, row):
        return header, ["ok" if row[0] == "normal" else row[0], *row[1:]]

    data = copy_dataset(tmp_path / "data", rename)
    assert run("train", manifest_for(tmp_path, data), workspace) == EXIT_RULE
    finding = next(f for f in findings(workspace) if f.get("rule") == RULE_NOTHING_NORMAL)
    assert finding["path"] == "output_features[0].preprocessing.normal_label"
    assert "ok" in finding["problem"]


def test_a_test_part_without_abnormal_windows_cannot_be_judged(tmp_path, workspace) -> None:
    # A fixed split puts every fault window into training: the test part's AUC has one side.
    def assign(index, header, row):
        window = index // 5
        if row[0] == "fault":
            part = "train"
        else:
            part = ("train", "train", "train", "validation", "test")[window % 5]
        return [*header, "part"], [*row, part]

    data = copy_dataset(tmp_path / "data", assign)
    manifest = manifest_for(tmp_path, data, split="split: {type: fixed, column: part}")
    assert run("quantize", manifest, workspace) == EXIT_RULE
    finding = next(f for f in findings(workspace) if f.get("rule") == RULE_GATE_UNMEASURABLE)
    assert finding["path"] == "output_features[0].auc_drop_max"
