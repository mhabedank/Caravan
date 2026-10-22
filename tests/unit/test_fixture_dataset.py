"""The one dataset this repository commits, and the script that generated it.

FR-013 allows exactly one: the synthetic fixture. These tests are what make the committed file
trustworthy — that it is what its generator produces, that it is small, and that it has the shape
the pilot manifest expects, including the one window that must be discarded (SC-009, SC-010).
"""

from __future__ import annotations

import importlib.util
import sys

from tests.support import (
    FIXTURE_LABELS,
    FIXTURE_RECORDS,
    FIXTURE_WINDOWS_DISCARDED,
    FIXTURE_WINDOWS_KEPT,
    SYNTHETIC_DATASET,
)

MAXIMUM_BYTES = 200 * 1024


def load_generator():
    """Import ``make.py`` by path: it is a fixture script, not an importable package."""
    path = SYNTHETIC_DATASET / "make.py"
    spec = importlib.util.spec_from_file_location("synthetic_make", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_committed_file_is_what_its_generator_produces(tmp_path) -> None:
    # Why both are committed: a generated-at-test-time fixture cannot be inspected when a test
    # fails, and a committed file alone leaves nobody able to say what it is.
    make = load_generator()
    regenerated = make.generate(tmp_path / "again")
    committed = SYNTHETIC_DATASET / "records.csv"
    assert regenerated.read_bytes() == committed.read_bytes()


def test_the_fixture_stays_small(tmp_path) -> None:
    total = sum(path.stat().st_size for path in SYNTHETIC_DATASET.glob("*.csv"))
    assert total <= MAXIMUM_BYTES, f"{total} bytes is over the {MAXIMUM_BYTES} the spec allows"


def test_the_fixture_has_the_shape_the_pilot_manifest_expects() -> None:
    lines = (SYNTHETIC_DATASET / "records.csv").read_text(encoding="utf-8").splitlines()
    header, records = lines[0], lines[1:]
    assert header.split(",")[0] == "label"
    assert len(header.split(",")) == 6  # label plus five features
    assert len(records) == FIXTURE_RECORDS
    assert sorted({line.split(",")[0] for line in records}) == list(FIXTURE_LABELS)


def test_the_fixture_contains_a_window_that_spans_a_change_of_label() -> None:
    # SC-010's first half. Without it, nothing in the suite would exercise the discard rule on
    # real committed data, and the counts in a run report would always be zero.
    from caravan.data.windows import plan_windows

    records = (SYNTHETIC_DATASET / "records.csv").read_text(encoding="utf-8").splitlines()[1:]
    plan = plan_windows([line.split(",")[0] for line in records], window=64)
    assert plan.samples == FIXTURE_WINDOWS_KEPT
    assert plan.discarded_mixed == FIXTURE_WINDOWS_DISCARDED
    assert plan.dropped_remainder == 0
