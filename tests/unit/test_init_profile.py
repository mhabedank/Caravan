"""What ``caravan init`` proposes for each column, and why (feature 013, research R3 to R5)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from caravan.init.profile import ProfileError, output_types, profile, proposed_output

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"
EDGES = DATA / "init"


def proposals(path: Path) -> dict[str, str | None]:
    return {column.name: column.proposal for column in profile(path).columns}


def test_the_fixtures_get_the_types_research_r4_measured() -> None:
    assert proposals(DATA / "synthetic") == {
        "label": "category",
        "can_id": "category",
        "dlc": "category",
        "b0": "number",
        "b1": "number",
        "b2": "number",
    }
    assert set(proposals(DATA / "frames").values()) == {"category", "number"}
    anomaly = proposals(DATA / "anomaly")
    assert all(anomaly[f"m{i}"] == "number" for i in range(8))


@pytest.mark.parametrize(
    ("table", "column", "proposal", "reason"),
    [
        ("empty-column.csv", "empty", None, "every sampled cell is empty"),
        ("constant.csv", "mode", None, "one value in every sampled row: carries no information"),
        ("ids.csv", "sensor_id", "category", "a code, not a magnitude"),
        ("ids.csv", "code", "category", "a code, not a magnitude"),
        ("small-codes.csv", "gear", "category", "5 distinct integer values"),
        ("missing.csv", "temp", "number", "numeric, 3 distinct values"),
        ("bad-name.csv", "Speed (km/h)", None, "cannot name a feature"),
        ("constant.csv", "label", "binary", "2 distinct values: a and b"),
    ],
)
def test_each_rule_gives_its_proposal_and_reason(table, column, proposal, reason) -> None:
    found = profile(EDGES / table).column(column)
    assert found.proposal == proposal
    assert reason in found.reason


def test_empty_cells_are_counted() -> None:
    assert profile(EDGES / "missing.csv").column("temp").empty == 1


def test_images_are_flagged_and_not_proposed() -> None:
    image = profile(DATA / "images").column("image")
    assert image.image_like and image.proposal is None
    assert "image inputs are not set up by init yet" in image.reason


def test_the_output_is_proposed_by_name_and_its_types_follow_its_values() -> None:
    assert proposed_output(profile(DATA / "synthetic")) == "label"
    assert proposed_output(profile(DATA / "anomaly")) == "condition"
    numeric = profile(EDGES / "numeric-output.csv")
    assert proposed_output(numeric) == "target"
    assert output_types(numeric.column("target")) == ("number",)
    assert output_types(profile(DATA / "synthetic").column("label")) == ("category", "anomaly")
    assert output_types(profile(DATA / "anomaly").column("condition"))[0] == "binary"


def test_headers_that_differ_stop_with_both_files_named() -> None:
    with pytest.raises(ProfileError, match=r"different headers: b\.csv lacks b; adds c"):
        profile(EDGES / "headers-differ")


def test_a_file_without_a_header_is_named() -> None:
    with pytest.raises(ProfileError, match="has no header row"):
        profile(EDGES / "no-header")


def test_a_missing_path_is_named() -> None:
    with pytest.raises(ProfileError, match="no such path"):
        profile(EDGES / "nowhere")


def test_a_million_rows_are_profiled_quickly_from_a_sample(tmp_path) -> None:
    # SC-005: proposals for a million rows within five seconds, by reading a bounded sample.
    table = tmp_path / "big.csv"
    with table.open("w", encoding="utf-8") as handle:
        handle.write("a,b,label\n")
        for i in range(1_000_000):
            handle.write(f"{i % 97},{i * 0.5},{'x' if i % 3 else 'y'}\n")
    began = time.perf_counter()
    found = profile(table)
    elapsed = time.perf_counter() - began
    print(f"profiling 1,000,000 rows: {elapsed:.2f} s")
    assert elapsed < 5
    assert found.sample_note() == "sampled the first 50,000 rows"
