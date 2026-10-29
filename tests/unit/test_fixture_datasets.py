"""The three datasets of feature 010, and the scripts that generated them.

As for the pilot's dataset (``test_fixture_dataset.py``): a committed file is trusted because its
generator produces exactly it, on every Python of the matrix — which is why the generators use only
``randrange`` and the PNG files are stored, not compressed. And they stay small.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tests.support import FIXTURES

DATASETS = FIXTURES / "datasets"
MAXIMUM_BYTES = 200 * 1024


def generator(name: str):
    path = DATASETS / name / "make.py"
    spec = importlib.util.spec_from_file_location(f"{name}_make", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["frames", "anomaly"])
def test_a_table_is_what_its_generator_produces(name: str) -> None:
    committed = (DATASETS / name / "records.csv").read_text(encoding="utf-8")
    assert generator(name).generate() == committed
    assert len(committed.encode("utf-8")) < MAXIMUM_BYTES


def test_the_images_are_what_their_generator_produces(tmp_path: Path) -> None:
    generator("images").generate(tmp_path)
    committed = DATASETS / "images"
    assert (tmp_path / "labels.csv").read_bytes() == (committed / "labels.csv").read_bytes()
    regenerated = sorted(path.name for path in (tmp_path / "img").iterdir())
    assert regenerated == sorted(path.name for path in (committed / "img").iterdir())
    total = 0
    for name in regenerated:
        data = (committed / "img" / name).read_bytes()
        assert (tmp_path / "img" / name).read_bytes() == data, name
        total += len(data)
    assert total < MAXIMUM_BYTES


def test_the_anomaly_windows_never_mix_conditions() -> None:
    # A window whose records disagree would be discarded; the fixture is built so none is.
    lines = (DATASETS / "anomaly" / "records.csv").read_text(encoding="utf-8").splitlines()[1:]
    conditions = [line.split(",", 1)[0] for line in lines]
    frames = generator("anomaly").FRAMES
    for start in range(0, len(conditions), frames):
        assert len(set(conditions[start : start + frames])) == 1
    assert {"normal", "fault"} == set(conditions)
