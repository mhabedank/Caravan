"""User story 1 of feature 014: no window crosses a recording (FR-001 to FR-004, SC-003).

Pure arithmetic over the label sequence, so these run on every Python with no framework; the two
tests that go through the reader skip where numpy is not installed.
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

from caravan.data.windows import Recording, plan_windows, recordings_from
from caravan.manifest.errors import (
    RULE_DATASET_NO_SAMPLES,
    RULE_WINDOW_COLUMN_OR_VALUE,
    RunRuleFailure,
)
from tests.support import BURSTS_DATASET, RECORDINGS_DATASET, SOC_DATASET

WINDOW = 64


def generator(directory: Path):
    spec = importlib.util.spec_from_file_location(f"{directory.name}_make", directory / "make.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_labels(directory: Path, column: str) -> tuple[list[str], list[tuple[str, int]]]:
    """Every record's ``column`` in file order, and (file, rows) per file — the reader's order."""
    labels: list[str] = []
    files: list[tuple[str, int]] = []
    for path in sorted(directory.glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            rows = [row[column] for row in csv.DictReader(handle)]
        labels.extend(rows)
        files.append((path.name, len(rows)))
    return labels, files


# --- the fixtures are what their generators write -------------------------------------------------


def test_the_recordings_fixture_is_what_its_generator_writes(tmp_path, monkeypatch) -> None:
    module = generator(RECORDINGS_DATASET)
    import random

    rng = random.Random(module.SEED)
    for number, length in enumerate(module.LENGTHS, start=1):
        committed = (RECORDINGS_DATASET / f"r{number}.csv").read_text(encoding="utf-8")
        assert committed == module.generate(length, rng)
        assert len(committed.splitlines()) - 1 == length


def test_the_soc_and_bursts_fixtures_are_what_their_generators_write() -> None:
    import random

    soc = generator(SOC_DATASET)
    rng = random.Random(soc.SEED)
    assert (SOC_DATASET / "d1.csv").read_text(encoding="utf-8") == soc.generate(1.0, rng)
    assert (SOC_DATASET / "d2.csv").read_text(encoding="utf-8") == soc.generate(0.9, rng)
    bursts = generator(BURSTS_DATASET)
    assert (BURSTS_DATASET / "frames.csv").read_text(encoding="utf-8") == bursts.generate()


# --- windows inside recordings ------------------------------------------------------------------


def test_no_window_crosses_a_file_and_each_file_starts_its_own_grid() -> None:
    labels, files = read_labels(RECORDINGS_DATASET, "label")
    recordings = recordings_from(files)
    plan = plan_windows(labels, WINDOW, recordings=recordings)

    assert [r.rows for r in recordings] == [450, 517, 600, 389, 702, 498]
    for position, start in enumerate(plan.kept):
        recording = recordings[plan.recording_of[position]]
        assert recording.start <= start and start + WINDOW <= recording.end  # SC-003
    # Each file's first window starts at its first row: the grid restarts per file. With the
    # ``last`` rule nothing is dropped, so the first kept window of a file is its first window.
    every = plan_windows(labels, WINDOW, recordings=recordings, rule="last")
    first: dict[int, int] = {}
    for position, start in enumerate(every.kept):
        first.setdefault(every.recording_of[position], start)
    assert first == {index: recording.start for index, recording in enumerate(recordings)}
    # One global grid would have started r2 at a multiple of 64; r2 starts at 450, which is not.
    assert recordings[1].start == 450 and 450 % WINDOW != 0


def test_each_recording_reports_its_rows_windows_and_leftover() -> None:
    labels, files = read_labels(RECORDINGS_DATASET, "label")
    plan = plan_windows(labels, WINDOW, recordings=recordings_from(files))
    first = plan.per_recording[0]
    assert first["file"] == "r1.csv" and first["rows"] == 450
    assert first["leftover_rows"] == 450 - 7 * WINDOW == 2
    assert [entry["leftover_rows"] for entry in plan.per_recording] == [
        rows % WINDOW for _, rows in files
    ]
    assert plan.dropped_remainder == sum(rows % WINDOW for _, rows in files)


def test_a_recording_shorter_than_a_window_yields_none_and_is_named() -> None:
    labels = ["a"] * 100 + ["a"] * 30 + ["a"] * 70
    recordings = recordings_from([("long.csv", 100), ("short.csv", 30), ("mid.csv", 70)])
    plan = plan_windows(labels, 64, recordings=recordings)
    assert plan.too_short == ("short.csv",)
    assert [entry["windows"] for entry in plan.per_recording] == [1, 0, 1]
    assert plan.per_recording[1]["leftover_rows"] == 30


def test_every_recording_too_short_is_refused_naming_the_longest() -> None:
    recordings = recordings_from([("a.csv", 40), ("b.csv", 50)])
    with pytest.raises(RunRuleFailure) as caught:
        plan_windows(["x"] * 90, 64, recordings=recordings)
    finding = caught.value.finding
    assert finding.rule == RULE_DATASET_NO_SAMPLES
    assert "b.csv" in finding.problem and "50" in finding.problem


def test_a_recording_column_cuts_a_file_and_a_returning_value_is_a_new_recording() -> None:
    keys = ["s1"] * 70 + ["s2"] * 70 + ["s1"] * 70
    recordings = recordings_from([("one.csv", 210)], keys)
    assert [(r.key, r.start, r.end) for r in recordings] == [
        ("s1", 0, 70),
        ("s2", 70, 140),
        ("s1", 140, 210),
    ]
    plan = plan_windows(["a"] * 210, 64, recordings=recordings)
    for start in plan.kept:
        assert len(set(keys[start : start + 64])) == 1
    assert plan.samples == 3
    # The grid of the old behaviour (one sequence) would have cut at 0, 64, 128: across s1/s2.
    assert plan.kept == (0, 70, 140)


def test_without_recordings_the_whole_sequence_is_one(capsys) -> None:
    plan = plan_windows(["a"] * 130, 64)
    assert plan.recordings == (Recording(0, 130),)
    assert plan.kept == (0, 64) and plan.dropped_remainder == 2


# --- through the reader --------------------------------------------------------------------------


def test_the_reader_returns_one_recording_per_file(tmp_path) -> None:
    pytest.importorskip("numpy")
    from caravan.data.fingerprint import resolve_dataset
    from caravan.data.reader import read_records

    dataset = resolve_dataset(str(RECORDINGS_DATASET), tmp_path)
    records = read_records(
        dataset, features=[("a", "number"), ("b", "number")], output=("label", "category")
    )
    assert [(r.file, r.rows) for r in records.recordings] == [
        ("r1.csv", 450),
        ("r2.csv", 517),
        ("r3.csv", 600),
        ("r4.csv", 389),
        ("r5.csv", 702),
        ("r6.csv", 498),
    ]


def test_a_recording_column_missing_from_a_file_is_refused(tmp_path) -> None:
    pytest.importorskip("numpy")
    from caravan.data.fingerprint import resolve_dataset
    from caravan.data.reader import read_records

    dataset = resolve_dataset(str(RECORDINGS_DATASET), tmp_path)
    with pytest.raises(RunRuleFailure) as caught:
        read_records(
            dataset,
            features=[("a", "number")],
            output=("label", "category"),
            recording_column="session",
        )
    assert caught.value.finding.rule == RULE_WINDOW_COLUMN_OR_VALUE
    assert caught.value.finding.path == "preprocessing.recording_column"
