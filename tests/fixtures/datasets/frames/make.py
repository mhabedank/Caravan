"""Generate the ``frames`` dataset: planes of feature frames for the ``conv2d`` template.

Feature 010. Shaped like keyword spotting's input after feature extraction — one record per frame,
one column per coefficient — and nothing like it otherwise: the values are arithmetic. Each sample
is a plane of 12 frames by 8 columns, and its class is a ridge that a two-dimensional convolution
sees and a per-column view does not: along the diagonal, along one frame, or along one column.

As for ``synthetic``: only ``randrange`` is used, so every Python in the matrix writes the same
bytes, and ``tests/unit/test_fixture_datasets.py`` asserts that it does. Principle XI: no model
produced any of it.

Run it with ``python tests/fixtures/datasets/frames/make.py``; it writes ``records.csv`` beside
itself.
"""

from __future__ import annotations

import random
from pathlib import Path

ROWS = 12
COLUMNS = 8
LABELS = ("ridge_diag", "ridge_row", "ridge_col")
SAMPLES_PER_LABEL = 60
SEED = 20261029
HEADER = ("label", *(f"c{index}" for index in range(COLUMNS)))


def _plane(label: str, rng: random.Random) -> list[list[int]]:
    """One sample: a background with noise, and the class's ridge."""
    plane = [[10 + rng.randrange(-6, 7) for _ in range(COLUMNS)] for _ in range(ROWS)]
    if label == "ridge_diag":
        offset = rng.randrange(-2, 3)
        for row in range(ROWS):
            column = (row + offset) * COLUMNS // ROWS
            if 0 <= column < COLUMNS:
                plane[row][column] += 40 + rng.randrange(-5, 6)
    elif label == "ridge_row":
        row = rng.randrange(2, ROWS - 2)
        for column in range(COLUMNS):
            plane[row][column] += 40 + rng.randrange(-5, 6)
    else:
        column = rng.randrange(1, COLUMNS - 1)
        for row in range(ROWS):
            plane[row][column] += 40 + rng.randrange(-5, 6)
    return plane


def generate() -> str:
    rng = random.Random(SEED)
    lines = [",".join(HEADER)]
    # Interleaved, so every part of a split holds every class wherever its windows are drawn.
    for _ in range(SAMPLES_PER_LABEL):
        for label in LABELS:
            for row in _plane(label, rng):
                lines.append(",".join((label, *(str(value) for value in row))))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    (Path(__file__).parent / "records.csv").write_text(generate(), encoding="utf-8")
