"""A failed gate: exit 1, no model, and a table that says where the accuracy went.

The failure cannot be provoked from the manifest. On the fixture, quantization changes no
prediction, so the drop is 0.000 and even a threshold of 0.0 passes — `0.000 <= 0.000`. Tightening
a threshold and hoping would be a test that passes for the wrong reason, so the drop is injected
at the measurement seam, and the arithmetic is covered separately in
``tests/unit/test_gate_arithmetic.py``.
"""

from __future__ import annotations

import json

import pytest

from caravan.cli.main import EXIT_RULE, main
from caravan.manifest.errors import RULE_ACCURACY_GATE
from caravan.stages.quantize import ERROR_TABLE, QUANTIZED_MODEL, RECORD
from tests.train.conftest import latest_run


@pytest.fixture
def quantization_costs_accuracy(monkeypatch):
    """Make the quantized model score one point lower than the converted one.

    Patched at ``caravan.runtime.measure.measure``, which the stage imports inside its function —
    so this replaces what the stage actually calls, and everything between the conversion and the
    verdict runs for real.
    """
    from caravan.runtime import measure as measure_module

    real = measure_module.measure

    def lower_for_the_quantized_model(path, *args, **kwargs):
        result = real(path, *args, **kwargs)
        if "quantized" in path.name:
            return type(result)(
                accuracy=max(result.accuracy - 0.25, 0.0),
                confusion=result.confusion,
                samples=result.samples,
                split=result.split,
                dataset_version=result.dataset_version,
            )
        return result

    monkeypatch.setattr(measure_module, "measure", lower_for_the_quantized_model)


def quantize(manifest, runs, cache):
    return main(["quantize", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])


def test_the_run_fails_with_the_rule_that_names_the_threshold(
    fixture_manifest, workspace, quantization_costs_accuracy
) -> None:
    runs, cache = workspace
    assert quantize(fixture_manifest, runs, cache) == EXIT_RULE

    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    rules = {finding.get("rule") for finding in report["findings"]}
    assert RULE_ACCURACY_GATE in rules
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_ACCURACY_GATE)
    assert finding["path"] == "outputs[0].accuracy_drop_max"


def test_no_quantized_model_survives_a_failed_gate(
    fixture_manifest, workspace, quantization_costs_accuracy
) -> None:
    # A failed gate must leave no publishable artifact, and the way to guarantee that is to never
    # have moved one into place: the stage writes into a working directory the runner deletes.
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    run_dir = latest_run(runs)
    assert not (run_dir / QUANTIZED_MODEL).exists()


def test_nothing_is_cached_for_a_failed_gate(
    fixture_manifest, workspace, quantization_costs_accuracy
) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    entries = [path for path in cache.rglob("result.json") if "quantize" in str(path)]
    assert not entries, f"a failed gate left a cache entry: {entries}"


def test_the_record_and_the_table_reach_the_run_directory(
    fixture_manifest, workspace, quantization_costs_accuracy
) -> None:
    # They are written straight into the run directory, because the working directory with the
    # model in it is about to be deleted by the mechanism above.
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    run_dir = latest_run(runs)

    assert (run_dir / RECORD).is_file()
    assert (run_dir / ERROR_TABLE).is_file()
    record = json.loads((run_dir / RECORD).read_text(encoding="utf-8"))
    assert record["accuracy"]["verdict"] == "fail"
    assert record["accuracy"]["quantization_drop"] > record["accuracy"]["threshold"]


def test_the_gate_entry_in_the_report_says_fail(
    fixture_manifest, workspace, quantization_costs_accuracy
) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    gates = {gate["name"]: gate for gate in report["gates"]}
    assert gates["accuracy"]["result"] == "fail"
    assert "resolution" in gates["accuracy"]["detail"]


def test_the_table_is_ordered_worst_first_and_names_real_layers(
    fixture_manifest, workspace, quantization_costs_accuracy
) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    run_dir = latest_run(runs)

    rows = json.loads((run_dir / RECORD).read_text(encoding="utf-8"))["layer_errors"]
    assert rows, "a failed gate owes the author a per-layer table"
    ranked = [row["rmse_over_scale"] for row in rows if row["rmse_over_scale"] is not None]
    assert ranked == sorted(ranked, reverse=True)
    assert any("FULLY_CONNECTED" in row["op_name"] for row in rows)

    text = (run_dir / ERROR_TABLE).read_text(encoding="utf-8")
    assert "0.289" in text  # the reference travels with the table
    assert "rmse_over_scale" in text


def test_the_summary_shows_the_worst_layers(
    fixture_manifest, workspace, quantization_costs_accuracy, capsys
) -> None:
    runs, cache = workspace
    quantize(fixture_manifest, runs, cache)
    err = capsys.readouterr().err
    assert "worst layers by rmse/scale" in err
    assert "reference 0.289" in err
    assert "the run did not finish" in err


def test_a_passing_run_has_no_table(fixture_manifest, workspace) -> None:
    # The asymmetry the constitution asks for: a failed gate must emit what is needed to act on
    # it, and a passing run has nothing to act on — so it does not pay for the second conversion.
    runs, cache = workspace
    assert quantize(fixture_manifest, runs, cache) == 0
    run_dir = latest_run(runs)
    assert not (run_dir / ERROR_TABLE).exists()
    assert "layer_errors" not in json.loads((run_dir / RECORD).read_text(encoding="utf-8"))
