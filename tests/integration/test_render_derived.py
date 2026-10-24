"""Render shows where a fitted value will come from, not an empty value (features 006, 008).

``render`` reads no data, so what fitting on the training part decides — the label order, a
category's vocabulary, the embedding size — is marked ``derived``. A run writes what it fitted in
their place; that half needs the training extra and is asserted in
``tests/train/test_typed_end_to_end.py``.
"""

from __future__ import annotations

from caravan.cli.main import EXIT_OK, main
from caravan.manifest._yaml import read_mapping
from tests.support import PILOT_FIXTURE, PILOT_FIXTURE_PINNED


def rendered(path, tmp_path, capsys) -> dict:
    assert main(["render", str(path), "--stdout"]) == EXIT_OK
    target = tmp_path / "resolved.yaml"
    target.write_text(capsys.readouterr().out, encoding="utf-8")
    return read_mapping(target)


def test_derived_values_are_marked(tmp_path, capsys) -> None:
    data = rendered(PILOT_FIXTURE, tmp_path, capsys)
    assert data["output_features"][0]["preprocessing"]["vocab"] == "derived"
    assert data["input_features"][0]["preprocessing"]["vocab"] == "derived"
    assert data["input_features"][0]["encoder"]["embedding_size"] == "derived"


def test_a_pinned_value_is_rendered_as_written(tmp_path, capsys) -> None:
    data = rendered(PILOT_FIXTURE_PINNED, tmp_path, capsys)
    assert data["output_features"][0]["preprocessing"]["vocab"] == [
        "normal",
        "dos",
        "fuzzy",
        "replay",
    ]
    assert data["input_features"][0]["preprocessing"]["vocab"] == [291, 608, 790, 1072]


def test_the_two_forms_differ_only_where_one_pins(tmp_path, capsys) -> None:
    derived = rendered(PILOT_FIXTURE, tmp_path, capsys)
    pinned = rendered(PILOT_FIXTURE_PINNED, tmp_path, capsys)
    pinned["output_features"][0]["preprocessing"]["vocab"] = "derived"
    pinned["input_features"][0]["preprocessing"]["vocab"] = "derived"
    assert derived == pinned
