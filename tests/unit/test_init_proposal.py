"""The proposal as shown: compact, worded, and labelled (feature 015, FR-005, FR-006, SC-007)."""

from __future__ import annotations

import csv
from pathlib import Path

from caravan.init import memory, proposal
from caravan.init.profile import CERTAINTIES
from caravan.init.session import Session

DATA = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"


def shown(session: Session) -> list[str]:
    return proposal.lines(proposal.build(session))


def assert_fits(lines: list[str]) -> None:
    assert len(lines) <= 24, "\n".join(lines)
    assert all(len(line) <= 80 for line in lines), [line for line in lines if len(line) > 80]


def test_the_synthetic_proposal_fits_and_words_every_certainty() -> None:
    lines = shown(Session({"dataset": str(DATA / "synthetic")}))
    assert_fits(lines)
    body = [line for line in lines[2:] if line.strip()]
    for line in body:
        tail = line[2 + proposal.LABEL_WIDTH + 2 + proposal.VALUE_WIDTH + 2 :]
        assert tail.split(":")[0] in (*CERTAINTIES, "given", "answered"), line
    text = "\n".join(lines)
    assert "number: b0, b1, b2" in text
    assert "category: can_id" in text and "category: dlc" in text
    assert "open: Caravan does not choose the hardware" in text


def test_two_hundred_columns_fit(tmp_path: Path) -> None:
    table = tmp_path / "wide.csv"
    with table.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([*(f"c{i}" for i in range(199)), "label"])
        for row in range(60):
            writer.writerow([*((row * (i + 3)) % 97 / 7 for i in range(199)), "ab"[row % 2]])
    lines = shown(Session({"dataset": str(table), "boards": ["s32k144"]}))
    assert_fits(lines)


def test_more_than_four_uncertain_columns_are_grouped(tmp_path: Path) -> None:
    table = tmp_path / "codes.csv"
    with table.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([*(f"g{i}" for i in range(6)), "label"])
        for row in range(40):
            writer.writerow([*((row + i) % 5 for i in range(6)), "xyz"[row % 3]])
    lines = shown(Session({"dataset": str(table)}))
    assert_fits(lines)
    unsure = [line for line in lines if "uncertain: 6 columns" in line]
    assert len(unsure) == 1 and "g0, g1" in unsure[0]


def test_each_chosen_board_has_a_memory_line_and_the_label_follows_once() -> None:
    lines = shown(Session({"dataset": str(DATA / "synthetic"), "boards": ["s32k144", "esp32"]}))
    assert_fits(lines)
    at = next(n for n, line in enumerate(lines) if line.lstrip().startswith("boards"))
    assert lines[at + 1].lstrip().startswith("memory") and "s32k144" in lines[at + 1]
    assert "esp32" in lines[at + 2]
    assert lines[at + 3].strip() == memory.SHORT_LABEL
    assert "\n".join(lines).count(memory.SHORT_LABEL) == 1


def test_a_bound_that_exceeds_a_board_is_marked_and_noted() -> None:
    # FR-006: marked and reported before the decision; it does not block writing.
    session = Session(
        {
            "dataset": str(DATA / "synthetic"),
            "boards": ["s32k144"],
            "template": "mlp",
            "params": {"hidden": [4096, 4096]},
        }
    )
    made = proposal.build(session)
    assert made.memory and not made.memory[0].fits
    assert any(line.rstrip().endswith("✗") for line in proposal.lines(made))
    notes = [note for note in made.notes if note.kind == "exceeds-board"]
    assert notes and "s32k144" in notes[0].message
    assert made.ready


def test_items_carry_source_and_certainty_as_the_data_model_says() -> None:
    session = Session({"dataset": str(DATA / "synthetic"), "boards": ["esp32"]})
    made = proposal.build(session)
    boards = made.item("boards")
    assert (boards.source, boards.certainty) == ("given", None)
    dlc = made.item("input", "dlc")
    assert (dlc.source, dlc.certainty, dlc.value) == ("proposed", "uncertain", "category")
    assert dlc.example == "--input dlc=number"
    assert all(item.option and item.example for item in made.items)
