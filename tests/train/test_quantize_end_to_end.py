"""The acceptance criterion: the pilot manifest quantizes end to end on the committed fixture."""

from __future__ import annotations

import json
import time

from caravan.cli.main import EXIT_OK, main
from caravan.stages.quantize import QUANTIZED_MODEL, RECORD
from caravan.stages.train import TRAINED_MODEL
from tests.train.conftest import latest_run

BUDGET_SECONDS = 60

PROMISED = (QUANTIZED_MODEL, RECORD, TRAINED_MODEL, "report.json", "resolved-manifest.yaml")


def quantize(manifest, runs, cache, *extra):
    return main(
        ["quantize", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache), *extra]
    )


def test_it_quantizes_within_the_budget(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    started = time.perf_counter()
    assert quantize(fixture_manifest, runs, cache) == EXIT_OK
    elapsed = time.perf_counter() - started
    assert elapsed < BUDGET_SECONDS, f"{elapsed:.1f}s is over the {BUDGET_SECONDS}s budget"


def test_every_promised_artifact_is_there(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    run_dir = latest_run(runs)
    missing = [name for name in PROMISED if not (run_dir / name).is_file()]
    assert not missing, f"missing artifacts: {missing}"


def test_the_report_carries_the_three_accuracies_and_the_verdict(
    fixture_manifest, workspace
) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    accuracy = report["quantization"]["accuracy"]

    for key in (
        "trained",
        "converted",
        "quantized",
        "conversion_drop",
        "quantization_drop",
        "threshold",
        "verdict",
        "samples",
        "resolution",
    ):
        assert key in accuracy, key
    assert accuracy["verdict"] in {"pass", "fail"}
    # The gate judges conversion → quantized, so the two differences must be separable.
    assert accuracy["quantization_drop"] == accuracy["converted"] - accuracy["quantized"]
    assert accuracy["conversion_drop"] == accuracy["trained"] - accuracy["converted"]


def test_the_verdict_can_be_recomputed_from_the_recorded_numbers(
    fixture_manifest, workspace
) -> None:
    # The reason the comparison is made at the recorded precision: a reader who recomputes the
    # verdict from the report must get the verdict the report states.
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    accuracy = json.loads((latest_run(runs) / RECORD).read_text(encoding="utf-8"))["accuracy"]
    recomputed = "pass" if accuracy["quantization_drop"] <= accuracy["threshold"] else "fail"
    assert recomputed == accuracy["verdict"]


def test_the_gate_appears_in_the_reports_gate_list(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    gates = {gate["name"]: gate for gate in report["gates"]}
    assert "accuracy" in gates
    assert gates["accuracy"]["result"] in {"pass", "fail"}
    assert "accepted" in gates["accuracy"]["detail"]


def test_the_calibration_record_says_what_was_asked_and_what_was_used(
    fixture_manifest, workspace
) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    calibration = json.loads((latest_run(runs) / RECORD).read_text(encoding="utf-8"))["calibration"]
    # The fixture's own case: the pilot manifest asks for 500 and the training split holds 56.
    assert calibration["requested"] == 500
    assert calibration["available"] == calibration["used"]
    assert calibration["used"] < calibration["requested"]
    assert calibration["split"] == "train"


def test_the_record_names_both_tools_and_the_interpreter(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    tools = json.loads((latest_run(runs) / RECORD).read_text(encoding="utf-8"))["tools"]
    assert tools["framework"]["name"] == "tensorflow"
    assert tools["runtime"]["name"] == "ai-edge-litert"
    assert tools["runtime"]["version"] and tools["python"]
