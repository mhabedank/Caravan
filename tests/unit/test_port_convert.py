"""The pace-cnn converter finds its repository by name, not by position (T036).

The defect of 2026-10-24: the script counted two parents up and took that for the repository, so a
copy outside the checkout refused nothing or the wrong thing. It now looks for a ``pyproject.toml``
naming ``caravan-ml``. The check needs no archive and no array library beyond what the converter
imports at the top, so it is loaded the way a user runs it: as a file.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ports" / "pace-cnn" / "convert.py"


def load():
    pytest.importorskip("numpy")
    spec = importlib.util.spec_from_file_location("pace_cnn_convert", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_inside_the_checkout_the_repository_is_found() -> None:
    assert load().find_repository(SCRIPT) == ROOT


def test_a_copy_outside_a_checkout_finds_none(tmp_path) -> None:
    copy = tmp_path / "elsewhere" / "ports" / "pace-cnn" / "convert.py"
    copy.parent.mkdir(parents=True)
    copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    assert load().find_repository(copy) is None


def test_another_project_is_not_taken_for_the_repository(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "other"\n', encoding="utf-8")
    script = tmp_path / "a" / "b" / "convert.py"
    script.parent.mkdir(parents=True)
    script.write_text("", encoding="utf-8")
    assert load().find_repository(script) is None


def test_the_split_is_written_in_ludwigs_words() -> None:
    assert load().PART_WORDS == {"train": "train", "val": "validation", "test": "test"}
