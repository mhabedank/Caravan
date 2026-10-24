"""Quickstart scenario 3: the resolved manifest shows everything, and twice the same."""

from __future__ import annotations

from caravan.cli.main import EXIT_OK, EXIT_RULE, main
from caravan.manifest._yaml import read_mapping
from caravan.manifest.schema import Manifest
from tests.support import INVALID, MINIMAL, PILOT


def test_the_resolved_manifest_has_no_implicit_values(tmp_path, capsys) -> None:
    assert main(["render", str(MINIMAL), "--stdout"]) == EXIT_OK
    resolved = capsys.readouterr().out
    path = tmp_path / "resolved.yaml"
    path.write_text(resolved, encoding="utf-8")
    data = read_mapping(path)

    # Every field of the schema appears, at every level (SC-007).
    assert set(data) == set(Manifest.model_fields)
    assert data["random_seed"] == 42
    assert data["preprocessing"]["split"] == {
        "type": "random",
        "probabilities": [0.7, 0.15, 0.15],
        "column": None,
    }
    assert data["export"]["formats"] == ["flatbuffer", "c_array"]
    assert data["export"]["quantization"] == "int8"
    # The template's own default is expanded too, not left to the training stage to guess.
    assert data["model"]["params"] == {"hidden": [8], "dropout": 0.0}
    # What the training part will say is marked, not left empty (features 006, 008).
    assert data["output_features"][0]["preprocessing"]["vocab"] == "derived"
    assert data["input_features"][0]["preprocessing"]["normalization"] == "zscore"


def test_resolving_twice_is_byte_identical(capsys) -> None:
    main(["render", str(PILOT), "--stdout"])
    first = capsys.readouterr().out
    main(["render", str(PILOT), "--stdout"])
    second = capsys.readouterr().out
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_the_file_form_matches_the_stdout_form(tmp_path, capsys) -> None:
    main(["render", str(PILOT), "--stdout"])
    from_stdout = capsys.readouterr().out

    assert main(["render", str(PILOT), "--runs-dir", str(tmp_path / "runs")]) == EXIT_OK
    written = next((tmp_path / "runs").glob("*/resolved-manifest.yaml")).read_text(encoding="utf-8")
    assert written == from_stdout


def test_an_invalid_manifest_writes_no_resolved_manifest(tmp_path, capsys) -> None:
    runs = tmp_path / "runs"
    code = main(["render", str(INVALID / "cf-1-split-sum.yaml"), "--runs-dir", str(runs)])
    assert code == EXIT_RULE
    assert not list(runs.glob("*/resolved-manifest.yaml")), "a failed gate left an artifact behind"
    assert list(runs.glob("*/report.json")), "a failed run must still write its report"


def test_render_with_stdout_writes_nothing_to_disk(tmp_path, capsys) -> None:
    runs = tmp_path / "runs"
    assert main(["render", str(PILOT), "--stdout", "--runs-dir", str(runs)]) == EXIT_OK
    capsys.readouterr()
    assert not runs.exists()
