"""What the run says about its windows and split (feature 014, contracts/reports.md, FR-014).

The data stage adds these keys to ``data/schema.json`` beside the existing ones; the console prints
one line from them; the run's resolved manifest records the split type the data decided.
"""

from __future__ import annotations

from caravan.cli.pipeline import merge_split, split_line
from caravan.data.test_part import window_report
from caravan.data.windows import plan_windows, recordings_from, split_for
from tests.unit.test_split_groups import spec


def report_for(kind: str = "derived") -> dict:
    labels = ["a" if (i // 100) % 2 == 0 else "b" for i in range(1200)]
    files = [(f"f{i}.csv", 200) for i in range(6)]
    plan = plan_windows(labels, 20, recordings=recordings_from(files), stride=10)
    split = split_for(plan, spec(kind), seed=4, labels=("a", "b"))
    return {"windows_kept": plan.samples, **window_report(plan, split)}


def test_the_report_names_the_window_the_recordings_the_drops_and_the_split() -> None:
    report = report_for()
    assert report["window"] == {"size": 20, "stride": 10, "label_rule": "all_equal"}
    assert [entry["file"] for entry in report["recordings"]] == [f"f{i}.csv" for i in range(6)]
    assert report["recordings_too_short"] == []
    assert set(report["windows_dropped"]) == {"mixed", "tied", "mixed_split", "purged"}
    plan = report["split_plan"]
    assert plan["type"] == "recording" and plan["derived"] is True
    assert sorted(sum(plan["assignment"].values(), [])) == [f"f{i}.csv" for i in range(6)]
    assert abs(sum(plan["shares"].values()) - 1) < 1e-3


def test_the_console_line_says_how_the_windows_were_cut_and_split() -> None:
    line = split_line(report_for())
    assert line is not None
    assert "of 20 rows, every 10 (label: all_equal), from 6 recordings" in line
    assert "split by recording (derived: 6 recordings)" in line


def test_without_a_window_there_is_no_line() -> None:
    assert split_line({"window": {"size": None}, "split_plan": {}}) is None


def test_the_run_records_the_split_type_the_data_decided() -> None:
    resolved = {"preprocessing": {"split": {"type": "derived", "probabilities": [0.7, 0.15, 0.15]}}}
    merged = merge_split(resolved, report_for())
    assert merged["preprocessing"]["split"]["type"] == "recording"
    assert merged["preprocessing"]["split"]["derived"] is True
    assert resolved["preprocessing"]["split"]["type"] == "derived"  # the input is not changed


def test_a_stated_split_is_left_as_stated() -> None:
    resolved = {"preprocessing": {"split": {"type": "blocked"}}}
    assert merge_split(resolved, report_for("blocked")) is resolved
