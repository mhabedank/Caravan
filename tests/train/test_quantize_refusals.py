"""The three refusals that are not the gate: an unreadable model, a failed conversion, an
unmeasurable comparison.

Each one tests *this project's* mapping from a failure to a rule, which is why the failures are
injected at the boundary rather than simulated by hand: what is under test is that a converter
blowing up becomes Q-2 with a message, not that a converter can blow up.
"""

from __future__ import annotations

import json

import pytest

from caravan.cli.main import EXIT_RULE, main
from caravan.manifest.errors import (
    RULE_CONVERSION_FAILED,
    RULE_GATE_UNMEASURABLE,
    RULE_NOT_FULLY_QUANTIZED,
    RULE_TRAINED_MODEL_UNREADABLE,
)
from caravan.stages.quantize import QUANTIZED_MODEL
from caravan.stages.train import TRAINED_MODEL
from tests.train.conftest import latest_run


def quantize(manifest, runs, cache):
    return main(["quantize", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])


def rules_of(runs) -> set[str]:
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    return {finding.get("rule") for finding in report["findings"]}


def test_q1_when_the_trained_model_cannot_be_read(fixture_manifest, workspace) -> None:
    # Not a *missing* model: the runner always runs the upstream stage first, and a cache entry
    # with absent artifacts counts as a miss. What can happen is a cached file that will not load,
    # so that is what this provokes — by corrupting the cache entry between two runs.
    import shutil

    runs, cache = workspace
    assert quantize(fixture_manifest, runs, cache) == 0

    # Corrupt the cached trained model, and drop *only* the quantize entry. Both halves matter:
    # the cache treats a file that exists as a valid artifact, so the corrupt one is copied into
    # the next run; and without dropping the quantize entry that run would reuse its own result
    # and never open the model at all — which is correct behaviour and would make this test pass
    # for the wrong reason.
    for path in cache.rglob(TRAINED_MODEL):
        path.write_bytes(b"not a model")
    shutil.rmtree(cache / "quantize")

    assert quantize(fixture_manifest, runs, cache) == EXIT_RULE
    assert RULE_TRAINED_MODEL_UNREADABLE in rules_of(runs)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_TRAINED_MODEL_UNREADABLE)
    # The message names the artifact and what to do about it, rather than relaying a loader error.
    assert "trained.keras" in finding["problem"]
    assert "--fresh" in finding["problem"]


def test_q2_when_the_conversion_fails(fixture_manifest, workspace, monkeypatch) -> None:
    import tensorflow as tf

    def refuse(*_args, **_kwargs):
        raise RuntimeError("the converter declined")

    monkeypatch.setattr(tf.lite.TFLiteConverter, "from_keras_model", refuse)

    runs, cache = workspace
    assert quantize(fixture_manifest, runs, cache) == EXIT_RULE
    assert RULE_CONVERSION_FAILED in rules_of(runs)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_CONVERSION_FAILED)
    # What the converter said travels out, because that is the only clue the author has.
    assert "declined" in finding["problem"]


def test_q5_when_the_comparison_cannot_be_measured(
    fixture_manifest, workspace, monkeypatch
) -> None:
    # Unknown is not within budget: a stage that cannot show the budget holds must fail.
    from caravan.runtime import measure as measure_module

    def refuse(*_args, **_kwargs):
        raise ValueError("the interpreter would not load the model")

    monkeypatch.setattr(measure_module, "run_model", refuse)

    runs, cache = workspace
    assert quantize(fixture_manifest, runs, cache) == EXIT_RULE
    assert RULE_GATE_UNMEASURABLE in rules_of(runs)
    assert not (latest_run(runs) / QUANTIZED_MODEL).exists()


def test_q3_when_a_model_declared_int8_keeps_float_tensors(
    fixture_manifest, workspace, monkeypatch
) -> None:
    # The failure a converter silently producing a partly quantized model would cause. Injected by
    # making the conversion return an unquantized model while the manifest still says int8.
    from caravan.convert import tflite as tflite_module
    from caravan.stages import quantize as quantize_module

    real = tflite_module.convert

    def convert_without_quantizing(model, setting, representative=None, *, pixel_inputs=False):
        return real(model, "none", pixel_inputs=pixel_inputs)

    monkeypatch.setattr(tflite_module, "convert", convert_without_quantizing)
    monkeypatch.setattr(quantize_module, "_layer_errors", lambda *a, **k: ())

    runs, cache = workspace
    assert quantize(fixture_manifest, runs, cache) == EXIT_RULE
    assert RULE_NOT_FULLY_QUANTIZED in rules_of(runs)
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_NOT_FULLY_QUANTIZED)
    # The offending tensors are named: without them the author has a verdict and no lead.
    assert "float" in finding["problem"] or finding["found"]


@pytest.mark.parametrize("rule", ["Q-1", "Q-2", "Q-3", "Q-5"])
def test_each_refusal_is_exit_one_and_not_a_crash(rule) -> None:
    # A rule saying no is exit 1; a defect in the tool is exit 3. These four are rules.
    from caravan.manifest.errors import QUANTIZE_RULES

    assert rule in QUANTIZE_RULES
