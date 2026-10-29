"""Q-6: an image input must take raw pixels, and the file is read to prove it (feature 010, R6)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from caravan.manifest.errors import RULE_IMAGE_INPUT_NOT_RAW, RunRuleFailure
from caravan.runtime.inspect import TensorRecord
from caravan.stages.quantize import check_raw_pixels

IMAGES = [{"name": "image", "type": "image"}]


@dataclass
class Inspection:
    inputs: tuple[TensorRecord, ...]


def tensor(dtype: str, scale: float | None, zero_point: int | None) -> TensorRecord:
    return TensorRecord(
        name="serving_default_image:0",
        dtype=dtype,
        shape=(1, 16, 16, 3),
        scale=scale,
        zero_point=zero_point,
    )


def test_raw_pixels_pass() -> None:
    check_raw_pixels(Inspection((tensor("uint8", 1.0, 0),)), IMAGES)


@pytest.mark.parametrize(
    ("dtype", "scale", "zero_point"),
    [
        # What calibration without the black and white frames produced (research R6).
        ("uint8", 0.9411764740943909, 0),
        ("int8", 1.0, -128),
        ("float32", None, None),
    ],
)
def test_anything_else_is_refused(dtype, scale, zero_point) -> None:
    with pytest.raises(RunRuleFailure) as caught:
        check_raw_pixels(Inspection((tensor(dtype, scale, zero_point),)), IMAGES)
    finding = caught.value.finding
    assert finding.rule == RULE_IMAGE_INPUT_NOT_RAW
    assert finding.path == "export.quantization"
    assert "'image'" in finding.problem


def test_an_input_that_is_not_an_image_is_not_checked() -> None:
    check_raw_pixels(Inspection((tensor("float32", None, None),)), [])
