"""Every combination ``caravan init`` offers writes a manifest that validates (SC-002, SC-006),
and the same answers write the same bytes in every mode (FR-020)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_OK, main
from caravan.init.session import Session
from caravan.manifest.load import load_manifest

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
FIXTURES = ("synthetic", "frames", "anomaly", "recordings", "bursts")


def offers(name: str) -> list[tuple[str, str]]:
    session = Session({"dataset": str(DATA / name), "boards": ["esp32"]})
    out = []
    for kind in [c.value for c in session.choices("output_type")]:
        session.accept("output_type", kind)
        for template in session.choices("template"):
            if not template.disabled:
                out.append((kind, template.value))
    return out


CASES = [(name, kind, template) for name in FIXTURES for kind, template in offers(name)]


@pytest.mark.parametrize(("name", "kind", "template"), CASES)
def test_every_offered_combination_validates(tmp_path, name, kind, template) -> None:
    session = Session(
        {
            "dataset": str(DATA / name),
            "boards": ["s32k144", "stm32h743"],
            "output_type": kind,
        },
        cwd=tmp_path,
    )
    assert session.accept("template", template) is None
    if session.value("budget") is None:
        assert session.accept("budget", 0.1) is None
    if session.value("normal_label") is None and "normal_label" in session.keys():  # noqa: SIM118
        assert session.accept("normal_label", session.choices("normal_label")[0].value) is None
    assert session.fill() == []
    target, findings = session.write()
    assert not findings, findings
    assert load_manifest(target).manifest is not None


def test_a_third_party_template_with_a_starter_is_offered(tmp_path) -> None:
    from caravan.templates.mlp import MlpParameters
    from caravan.templates.registry import (
        TemplateParameterSpec,
        TemplateStarter,
        build_registry,
    )

    registry = build_registry()
    registry.register(
        TemplateParameterSpec(
            identifier="mine",
            parameters=MlpParameters,
            consumes_window=True,
            summary="a test template",
            starter=TemplateStarter({"hidden": [4]}, 8, 9, "the test's own"),
        )
    )
    session = Session(
        {"dataset": str(DATA / "synthetic"), "boards": ["esp32"]}, cwd=tmp_path, templates=registry
    )
    assert "mine" in [c.value for c in session.choices("template")]
    assert session.accept("template", "mine") is None
    assert session.value("params") == {"hidden": [4]}


@pytest.mark.parametrize("name", ["synthetic", "frames", "anomaly"])
def test_the_dialogue_and_no_input_write_the_same_bytes(tmp_path, monkeypatch, name) -> None:
    monkeypatch.chdir(tmp_path)
    args = ["--dataset", str(DATA / name), "--board", "esp32"]
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert main(["init", "a.yaml", "--no-input", *args]) == EXIT_OK
    assert main(["init", "b.yaml", "--no-input", *args]) == EXIT_OK
    monkeypatch.setattr("sys.stdin", io.StringIO("\n" * 20))
    assert main(["init", "c.yaml", *args]) == EXIT_OK
    first = (tmp_path / "a.yaml").read_bytes()
    assert first == (tmp_path / "b.yaml").read_bytes() == (tmp_path / "c.yaml").read_bytes()
