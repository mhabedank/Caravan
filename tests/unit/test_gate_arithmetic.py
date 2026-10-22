"""The accuracy gate's arithmetic, where every resolution can be constructed.

The fixture cannot exercise this: on 80 synthetic windows quantization changes no prediction, so
the drop is zero and every threshold passes. The arithmetic is the part that must be right in all
directions, so it is tested here — with numbers chosen rather than hoped for.
"""

from __future__ import annotations

import math

import pytest

from caravan.stages.quantize import GateOutcome


def gate(converted: float, quantized: float, threshold: float, samples: int = 100) -> GateOutcome:
    return GateOutcome(
        trained=converted,
        converted=converted,
        quantized=quantized,
        threshold=threshold,
        samples=samples,
    )


def test_a_drop_under_the_threshold_passes() -> None:
    assert gate(0.90, 0.89, 0.02).passed


def test_a_drop_exactly_equal_to_the_threshold_passes() -> None:
    # ``<=``. The author wrote the number they accept, and a number you accept is one you accept.
    outcome = gate(0.90, 0.88, 0.02)
    assert outcome.quantization_drop == pytest.approx(0.02)
    assert outcome.passed


def test_a_drop_one_step_over_the_threshold_fails() -> None:
    assert not gate(0.90, 0.87, 0.02).passed


def test_a_negative_drop_passes_and_stays_negative() -> None:
    # The quantized model scoring higher is a measurement worth seeing, not a zero to clamp to.
    outcome = gate(0.88, 0.90, 0.02)
    assert outcome.quantization_drop < 0
    assert outcome.passed
    assert outcome.as_dict()["quantization_drop"] == pytest.approx(-0.02)


def test_the_threshold_is_absolute_and_never_a_percentage() -> None:
    # 0.02 means two points of accuracy. Read as two percent of 0.90 it would be 0.018, and this
    # case would flip — which is the whole reason to pin it.
    assert gate(0.90, 0.882, 0.02).passed
    assert not gate(0.90, 0.87, 0.02).passed


def test_the_gate_judges_conversion_to_quantized_and_not_trained_to_quantized() -> None:
    # The design decision of this feature. Conversion costs 0.05 here and quantization costs
    # nothing; a gate on the sum would fail this run for something quantization did not do.
    outcome = GateOutcome(trained=0.95, converted=0.90, quantized=0.90, threshold=0.02, samples=100)
    assert outcome.conversion_drop == pytest.approx(0.05)
    assert outcome.quantization_drop == pytest.approx(0.0)
    assert outcome.passed


def test_both_differences_are_recorded_either_way() -> None:
    record = GateOutcome(
        trained=0.95, converted=0.90, quantized=0.80, threshold=0.02, samples=50
    ).as_dict()
    assert record["conversion_drop"] == pytest.approx(0.05)
    assert record["quantization_drop"] == pytest.approx(0.10)
    assert record["verdict"] == "fail"
    assert record["trained"] == 0.95 and record["converted"] == 0.90


def test_the_resolution_is_one_over_the_sample_count() -> None:
    assert gate(0.9, 0.9, 0.02, samples=12).resolution == pytest.approx(1 / 12)
    assert gate(0.9, 0.9, 0.02, samples=1000).resolution == pytest.approx(0.001)


def test_a_resolution_coarser_than_the_threshold_still_yields_a_verdict() -> None:
    # Twelve samples cannot express 0.02, and the author's number still decides. What the report
    # owes the reader is the resolution beside the verdict, not a refusal to judge.
    outcome = gate(0.75, 0.6667, 0.02, samples=12)
    assert outcome.resolution > outcome.threshold
    assert not outcome.passed
    assert outcome.as_dict()["resolution"] == pytest.approx(1 / 12, abs=1e-6)


def test_no_samples_gives_an_infinite_resolution_rather_than_a_division_error() -> None:
    assert math.isinf(gate(0.0, 0.0, 0.02, samples=0).resolution)


def test_the_summary_names_both_numbers() -> None:
    text = gate(0.90, 0.80, 0.02).summary()
    assert "0.100" in text and "0.020" in text
