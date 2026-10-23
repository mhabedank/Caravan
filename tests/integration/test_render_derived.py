"""FR-013 of feature 006: render shows where a derived value will come from, not an empty value.

``render`` reads no data, so the labels and the input columns a run will derive are marked
``derived``. A run writes the values the data stage found in their place — that half needs the
training extra and is asserted in ``tests/train/test_declared_io_end_to_end.py``.
"""

from __future__ import annotations

from caravan.cli.main import EXIT_OK, main
from caravan.manifest._yaml import read_mapping
from tests.support import PILOT_V01, PILOT_V01_DERIVED


def rendered(path, tmp_path, capsys) -> dict:
    assert main(["render", str(path), "--stdout"]) == EXIT_OK
    target = tmp_path / "resolved.yaml"
    target.write_text(capsys.readouterr().out, encoding="utf-8")
    return read_mapping(target)


def test_derived_values_are_marked(tmp_path, capsys) -> None:
    data = rendered(PILOT_V01_DERIVED, tmp_path, capsys)
    assert data["inputs"][0]["columns"] == "derived"
    assert data["outputs"][0]["labels"] == "derived"


def test_a_pinned_value_is_rendered_as_written(tmp_path, capsys) -> None:
    data = rendered(PILOT_V01, tmp_path, capsys)
    assert data["outputs"][0]["labels"] == ["normal", "dos", "fuzzy", "replay"]
    assert data["inputs"][0]["columns"] == "derived"


def test_the_two_forms_differ_only_where_one_pins_the_labels(tmp_path, capsys) -> None:
    derived = rendered(PILOT_V01_DERIVED, tmp_path, capsys)
    pinned = rendered(PILOT_V01, tmp_path, capsys)
    pinned["outputs"][0]["labels"] = "derived"
    assert derived == pinned
