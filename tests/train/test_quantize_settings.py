"""All three settings the schema accepts, including the two no model asks for."""

from __future__ import annotations

import json

from caravan.cli.main import EXIT_OK, main
from caravan.stages.quantize import RECORD
from tests.train.conftest import latest_run


def manifest_with(fixture_manifest, tmp_path, setting: str, keep_samples: bool = True):
    """The fixture manifest with one field changed, and its dataset path made absolute."""
    from tests.support import SYNTHETIC_DATASET

    text = fixture_manifest.read_text(encoding="utf-8").replace(
        "source: ../../datasets/synthetic", f"source: {SYNTHETIC_DATASET}"
    )
    text = text.replace("quantization: int8", f"quantization: {setting}")
    if "quantization:" not in text:
        text = text.replace("export:\n", f"export:\n  quantization: {setting}\n")
    if not keep_samples:
        text = "\n".join(line for line in text.splitlines() if "representative_samples" not in line)
    path = tmp_path / f"{setting}.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def quantize(manifest, runs, cache):
    return main(["quantize", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])


def record_of(runs):
    return json.loads((latest_run(runs) / RECORD).read_text(encoding="utf-8"))


def test_int8_is_described_as_int8(fixture_manifest, workspace) -> None:
    runs, cache = workspace
    assert quantize(fixture_manifest, runs, cache) == EXIT_OK
    model = record_of(runs)["model"]
    assert model["setting"] == "int8"
    assert model["fully_integer"] is True


def test_float16_converts_and_is_not_called_int8(fixture_manifest, workspace, tmp_path) -> None:
    runs, cache = workspace
    manifest = manifest_with(fixture_manifest, tmp_path, "float16", keep_samples=False)
    assert quantize(manifest, runs, cache) == EXIT_OK

    model = record_of(runs)["model"]
    assert model["setting"] == "float16"
    # The stage reports what the file contains and never claims int8 on this path.
    assert model["fully_integer"] is False
    assert record_of(runs)["calibration"]["requested"] is None


def test_none_still_converts_and_measures(fixture_manifest, workspace, tmp_path) -> None:
    # A stage asked for no quantization does not become a stage that does nothing: the conversion
    # happens, the comparison is measured, and the gated difference is zero by construction.
    runs, cache = workspace
    manifest = manifest_with(fixture_manifest, tmp_path, "none", keep_samples=False)
    assert quantize(manifest, runs, cache) == EXIT_OK

    record = record_of(runs)
    assert record["model"]["setting"] == "none"
    assert record["accuracy"]["quantization_drop"] == 0.0
    assert record["accuracy"]["verdict"] == "pass"
    assert record["calibration"]["used"] == 0


def test_a_setting_without_calibration_does_not_crash(
    fixture_manifest, workspace, tmp_path
) -> None:
    # The state the analysis pass found: representative_samples is optional and only int8 needs
    # it, so min(None, available) would have raised on valid input.
    runs, cache = workspace
    manifest = manifest_with(fixture_manifest, tmp_path, "none", keep_samples=False)
    assert quantize(manifest, runs, cache) == EXIT_OK
