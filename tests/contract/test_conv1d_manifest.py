"""The conv1d manifest: accepted, rendered, and refused for the two reasons it can be refused.

Manifest-level, so it runs on every Python in the matrix and in an installation with no training
framework — which is the point: validating a manifest never builds anything.
"""

from __future__ import annotations

from pathlib import Path

from caravan.cli.main import EXIT_OK, EXIT_RULE, main
from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import resolve

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
CONV1D = FIXTURES / "manifests" / "valid" / "picket-conv1d-fixture.yaml"


def test_the_fixture_manifest_is_valid(tmp_path) -> None:
    assert main(["validate", str(CONV1D), "--runs-dir", str(tmp_path)]) == EXIT_OK


def test_the_resolved_manifest_shows_the_defaults(tmp_path) -> None:
    outcome = load_manifest(CONV1D)
    assert outcome.manifest is not None
    resolved = resolve(outcome.manifest)
    blocks = resolved["model"]["params"]["blocks"]
    assert len(blocks) == 2
    # The second block writes no padding, stride or normalise; the resolved form shows what the
    # run will actually use, which is the whole purpose of `caravan render`.
    assert blocks[1]["stride"] == 1
    assert blocks[1]["padding"] == "valid"
    assert blocks[1]["normalise"] is False
    assert blocks[1]["pool"] is None
    assert resolved["model"]["params"]["head"] == "average"


def test_it_renders(tmp_path) -> None:
    assert main(["render", str(CONV1D), "--runs-dir", str(tmp_path)]) == EXIT_OK


def _variant(tmp_path, **replacements) -> Path:
    text = CONV1D.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    # The dataset path is relative to the manifest, so a copy needs an absolute one.
    text = text.replace("../../datasets/synthetic", str(FIXTURES / "datasets" / "synthetic"))
    path = tmp_path / "variant.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_bad_block_parameter_is_refused_with_its_position(tmp_path, capsys) -> None:
    # T-2, and the part that matters is the path: blocks[0], not "blocks".
    manifest = _variant(tmp_path, **{"filters: 16": "filters: 0"})
    assert main(["validate", str(manifest), "--runs-dir", str(tmp_path / "runs")]) == EXIT_RULE
    message = capsys.readouterr().err
    assert "model.params.blocks[0].filters" in message
    assert "greater than 0" in message


def test_a_window_too_short_for_the_blocks_is_refused_with_the_arithmetic(tmp_path, capsys) -> None:
    # CF-6, extended by this feature: a window can be present and still not carry the blocks.
    manifest = _variant(
        tmp_path,
        **{
            "window_size: 64": "window_size: 16",
            "kernel: 3, dropout: 0.1": "kernel: 5, dropout: 0.1",
        },
    )
    assert main(["validate", str(manifest), "--runs-dir", str(tmp_path / "runs")]) == EXIT_RULE
    message = capsys.readouterr().err
    assert "preprocessing.window_size" in message
    assert "block 2" in message
    assert "3 samples left" in message
    # The offered window is computed by walking the blocks, not estimated.
    assert "a window of 23 or more" in message


def test_a_missing_window_is_still_refused(tmp_path, capsys) -> None:
    # The older half of CF-6: this template consumes a window, so one has to be there.
    manifest = _variant(tmp_path, **{"  window_size: 64\n": ""})
    assert main(["validate", str(manifest), "--runs-dir", str(tmp_path / "runs")]) == EXIT_RULE
    assert "preprocessing.window_size" in capsys.readouterr().err


def test_a_fitting_configuration_is_not_refused_for_its_window(tmp_path) -> None:
    # The check must not fire on a configuration that fits: a false refusal is worse than none.
    manifest = _variant(tmp_path, **{"window_size: 64": "window_size: 128"})
    assert main(["validate", str(manifest), "--runs-dir", str(tmp_path / "runs")]) == EXIT_OK
