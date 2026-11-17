"""User story 4 of feature 014: overlapping windows, safely (FR-016 to FR-018, SC-005).

A window starts every ``stride`` rows within its recording. The splits that assign groups keep every
row in one part; the planning stays linear in the number of rows.
"""

from __future__ import annotations

import time

from caravan.data.windows import SPLIT_NAMES, plan_windows, recordings_from, split_for
from tests.support import RECORDINGS_DATASET
from tests.unit.test_split_groups import shared_rows, spec
from tests.unit.test_windows_recordings import read_labels


def recordings_plan(stride: int):
    labels, files = read_labels(RECORDINGS_DATASET, "label")
    return plan_windows(labels, 64, recordings=recordings_from(files), stride=stride, rule="last")


def test_a_quarter_window_stride_gives_about_four_times_the_windows() -> None:
    without = recordings_plan(64)
    with_overlap = recordings_plan(16)
    assert with_overlap.samples >= 3.5 * without.samples  # SC-005
    assert with_overlap.stride == 16


def test_windows_start_every_stride_rows_and_never_cross_a_recording() -> None:
    plan = recordings_plan(16)
    for position, start in enumerate(plan.kept):
        recording = plan.recordings[plan.recording_of[position]]
        assert (start - recording.start) % 16 == 0
        assert start + 64 <= recording.end


def test_no_row_is_shared_between_parts_and_the_purge_is_counted() -> None:
    plan = recordings_plan(16)
    for kind in ("recording", "blocked"):
        split = split_for(plan, spec(kind), seed=11, labels=("idle", "move"))
        assert shared_rows(plan, split) == 0  # FR-018
        kept = sum(split.counts[name] for name in SPLIT_NAMES)
        assert kept + split.purged == plan.samples
    blocked = split_for(plan, spec("blocked"), seed=11, labels=("idle", "move"))
    assert blocked.purged > 0


def test_planning_grows_linearly_with_the_rows(capsys) -> None:
    # A wall-clock target would flake on a slow CI machine; growth does not (tasks T028).
    def timed(rows: int) -> float:
        labels = ["a" if (i // 5000) % 2 == 0 else "b" for i in range(rows)]
        began = time.perf_counter()
        plan_windows(labels, 64, stride=16, rule="last")
        return time.perf_counter() - began

    small, large = timed(250_000), timed(1_000_000)
    print(f"planning 250,000 rows: {small:.2f} s; 1,000,000 rows: {large:.2f} s")
    assert large <= 6 * small + 0.5
    assert large < 10
