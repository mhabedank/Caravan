"""The window table of ``caravan init`` counts what the data stage would (feature 013, R12)."""

from __future__ import annotations

from pathlib import Path

from caravan.data.windows import plan_windows, recordings_from, split_for
from caravan.init import windows
from caravan.init.profile import profile, read_column

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"


def labels_of(name: str, column: str):
    return read_column(profile(DATA / name), column)


def test_the_table_equals_the_planner_and_the_split() -> None:
    labels, files = labels_of("recordings", "label")
    row = windows.measure(labels, files, "binary", 16)
    plan = plan_windows(labels, 16, recordings=recordings_from(files), rule="all_equal")
    spec = {"type": "derived", "probabilities": [0.7, 0.15, 0.15], "column": None}
    split = split_for(plan, spec, seed=windows.SEED, labels=("idle", "move"))
    assert row.kept == plan.samples
    assert row.lost == plan.discarded_mixed
    assert row.split == split.type == "recording"
    assert sum(row.test.values()) == len(split.test)


def test_the_proposal_keeps_test_windows_of_every_class_and_says_why() -> None:
    labels, files = labels_of("synthetic", "label")
    table = windows.table(labels, files, "category")
    chosen = table.row(table.proposal)
    assert chosen is not None
    assert chosen.lost_share <= windows.MAX_LOST
    assert min(chosen.test.values()) >= windows.MIN_TEST_PER_CLASS
    bigger = [row for row in table.rows if row.size > chosen.size and row.usable]
    assert all(
        row.lost_share > windows.MAX_LOST or min(row.test.values()) < windows.MIN_TEST_PER_CLASS
        for row in bigger
    )
    assert "label holds for at least" in table.reason


def test_a_number_output_loses_no_window_and_the_strip_says_so() -> None:
    labels, files = labels_of("soc", "soc")
    table = windows.table(labels, files, "number")
    assert table.rule == "last"
    assert all(row.lost == 0 for row in table.rows if row.usable)
    assert "newest row" in table.reason
    assert "none is lost" in windows.strip(labels, 32, number=True)[-1]


def test_the_template_window_is_measured_too() -> None:
    labels, files = labels_of("anomaly", "condition")
    table = windows.table(labels, files, "anomaly", extra=(5,))
    assert table.row(5) is not None


def test_the_strip_marks_a_window_whose_labels_differ() -> None:
    labels = ["a"] * 10 + ["b"] * 10
    lines = windows.strip(labels, 4)
    assert lines[1].endswith("a" * 8 + "b" * 8) or "ab" in lines[1]
    assert "✗" in lines[3]


def test_the_table_says_which_rule_made_the_proposal() -> None:
    # Feature 015, research R1.3: a size that meets the table's criteria is certain, the
    # fewest-lost fallback is not. Measured with each shipped manifest's own template.
    from caravan.init.session import Session

    def path(name: str, kind: str, template: str) -> str:
        session = Session(
            {
                "dataset": str(DATA / name),
                "boards": ["s32k144"],
                "output_type": kind,
                "template": template,
            }
        )
        table = session.window_table()
        assert table is not None
        return table.path

    assert path("synthetic", "category", "mlp") == "criteria"
    assert path("anomaly", "anomaly", "autoencoder") == "fallback"
    assert path("recordings", "category", "conv1d") == "fallback"
