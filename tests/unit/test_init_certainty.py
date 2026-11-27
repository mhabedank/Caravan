"""Every certain proposal agrees with the intended manifest (feature 015, FR-003, SC-002).

A rule may call its proposal ``certain`` only where it agrees with every tabular dataset shipped
with Caravan that has an intended answer. The table below states those answers: from the shipped
manifests where there is one, otherwise from the dataset's own ``make.py``. Adding a shipped dataset
means adding a row; a rule that then disagrees loses its certainty (research R1).

The edge-case tables under ``tests/fixtures/datasets/init/`` have no intended manifest and are not
part of this table.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from caravan.init import windows
from caravan.init.profile import CERTAIN, OPEN, UNCERTAIN, profile
from caravan.init.session import Session

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"

#: dataset → (output, output type, template, {input: type})
INTENDED = {
    # examples/picket-mlp.yaml
    "synthetic": (
        "label",
        "category",
        "mlp",
        {"can_id": "category", "dlc": "number", "b0": "number", "b1": "number", "b2": "number"},
    ),
    # examples/anomaly-autoencoder.yaml
    "anomaly": ("condition", "anomaly", "autoencoder", {f"m{i}": "number" for i in range(8)}),
    # tests/fixtures/manifests/valid/recordings-conv1d.yaml
    "recordings": ("label", "category", "conv1d", {"a": "number", "b": "number", "c": "number"}),
    # examples/frames-conv2d.yaml
    "frames": ("label", "category", "conv2d", {f"c{i}": "number" for i in range(8)}),
    # tests/fixtures/datasets/soc/make.py: a continuous state of charge to predict
    "soc": ("soc", "number", None, {"current": "number", "voltage": "number", "temp": "number"}),
    # tests/fixtures/datasets/bursts/make.py: the CAN shape of `synthetic`
    "bursts": ("label", None, None, {"can_id": "category", "dlc": "number", "b0": "number"}),
}


def session(name: str, **given: object) -> Session:
    return Session({"dataset": str(DATA / name), "boards": ["s32k144"], **given})


@pytest.mark.parametrize("name", sorted(INTENDED))
def test_a_certain_column_proposal_is_the_intended_type(name: str) -> None:
    output, _, _, inputs = INTENDED[name]
    for column in profile(DATA / name).columns:
        if column.name == output or column.certainty != CERTAIN:
            continue
        assert column.proposal == inputs[column.name], (name, column.name, column.reason)


@pytest.mark.parametrize("name", sorted(INTENDED))
def test_a_certain_output_is_the_intended_one(name: str) -> None:
    output = INTENDED[name][0]
    found = session(name)
    certainty, reason = found.certainty("output")
    if certainty == CERTAIN:
        assert found.value("output") == output, (name, reason)


@pytest.mark.parametrize("name", sorted(n for n in INTENDED if INTENDED[n][1]))
def test_a_certain_output_type_is_the_intended_one(name: str) -> None:
    output, kind, _, _ = INTENDED[name]
    found = session(name, output=output)
    certainty, reason = found.certainty("output_type")
    if certainty == CERTAIN:
        assert found.value("output_type") == kind, (name, reason)


@pytest.mark.parametrize("name", sorted(n for n in INTENDED if INTENDED[n][2]))
def test_a_certain_template_is_the_intended_one(name: str) -> None:
    output, kind, template, _ = INTENDED[name]
    found = session(name, output=output, output_type=kind)
    if found.certainty("template")[0] == CERTAIN:
        assert found.value("template") == template


@pytest.mark.parametrize("name", sorted(n for n in INTENDED if INTENDED[n][2]))
def test_a_certain_window_meets_the_table_criteria_and_a_fallback_is_uncertain(name: str) -> None:
    # Research R1.3: the shipped sizes predate the window table, so the table's own criteria are
    # the reference (spec FR-003); measured with each manifest's own template.
    output, kind, template, _ = INTENDED[name]
    found = session(name, output=output, output_type=kind, template=template)
    table = found.window_table()
    if table is None:
        return
    certainty, _ = found.certainty("window")
    if table.path == "criteria":
        assert certainty == CERTAIN
        row = table.row(table.proposal)
        assert row is not None and row.lost_share <= windows.MAX_LOST
        assert all(count >= windows.MIN_TEST_PER_CLASS for count in row.test.values())
    else:
        assert certainty in (UNCERTAIN, OPEN)


def test_the_seven_differences_of_2026_11_24_are_not_certain() -> None:
    def column(name: str, column: str) -> str:
        return profile(DATA / name).column(column).certainty

    assert column("synthetic", "dlc") == UNCERTAIN
    assert column("recordings", "c") == UNCERTAIN
    assert column("soc", "current") == UNCERTAIN
    assert column("soc", "temp") == UNCERTAIN
    assert session("anomaly").certainty("output_type")[0] == UNCERTAIN
    assert session("recordings").certainty("output_type")[0] == UNCERTAIN
    assert session("soc").certainty("output")[0] in (UNCERTAIN, OPEN)


def test_on_the_synthetic_data_only_the_boards_and_two_columns_are_asked() -> None:
    # SC-001: data, boards, one step for the uncertain columns, the decision.
    found = Session({"dataset": str(DATA / "synthetic")})
    assert found.to_ask() == ["boards", "inputs"]
    assert found.uncertain_columns() == ["can_id", "dlc"]
