"""``export.test_windows``: how many test windows the export hands a board (feature 009).

data-model §1: an integer from 0 to 64, default 0, read by the export stage only; above 0 it needs
the ``c_array`` format, because the header it writes uses the array's named positions.
"""

from __future__ import annotations

import pytest

from caravan.manifest.resolve import render
from tests.unit.test_features_schema import outcome_for, refused, resolved


def _set(**export):
    def edit(document):
        document["export"].update(export)

    return edit


def test_the_default_is_zero_and_render_shows_it(tmp_path) -> None:
    assert resolved(tmp_path)["export"]["test_windows"] == 0
    outcome = outcome_for(tmp_path)
    assert "test_windows: 0" in render(outcome.manifest)


@pytest.mark.parametrize("count", [0, 1, 16, 64])
def test_zero_to_sixty_four_is_accepted(tmp_path, count) -> None:
    assert resolved(tmp_path, _set(test_windows=count))["export"]["test_windows"] == count


@pytest.mark.parametrize("count", [-1, 65])
def test_outside_the_range_is_refused_at_the_field(tmp_path, count) -> None:
    _, path, _ = refused(tmp_path, _set(test_windows=count))
    assert path == "export.test_windows"


def test_windows_without_the_c_array_are_refused_naming_the_formats(tmp_path) -> None:
    _, path, problem = refused(tmp_path, _set(test_windows=4, formats=["flatbuffer"]))
    assert path == "export.test_windows"
    assert "export.formats" in problem
    assert "c_array" in problem


def test_zero_windows_need_no_c_array(tmp_path) -> None:
    assert resolved(tmp_path, _set(formats=["flatbuffer"]))["export"]["test_windows"] == 0
