"""Generate the ``anomaly`` dataset: normal windows and faulty ones for the ``autoencoder``.

Feature 010. Shaped like the input of a machine-sound or vibration anomaly detector after feature
extraction — windows of 5 frames by 8 columns — and nothing like it otherwise: the values are
arithmetic. A normal window follows a two-dimensional pattern with noise, so an autoencoder can
learn it through a narrow code; a ``fault`` window carries the same pattern with three columns
pushed up, which the code cannot reproduce. About one window in seven is a fault, interleaved so
that every part of a split holds both.

Only ``randrange`` is used, so every Python in the matrix writes the same bytes
(``tests/unit/test_fixture_datasets.py``). Principle XI: no model produced any of it.

Run it with ``python tests/fixtures/datasets/anomaly/make.py``; it writes ``records.csv`` beside
itself.
"""

from __future__ import annotations

import random
from pathlib import Path

FRAMES = 5
COLUMNS = 8
WINDOWS = 420
FAULT_EVERY = 7
SEED = 20261030
HEADER = ("condition", *(f"m{index}" for index in range(COLUMNS)))

#: The two directions normal windows vary in, per column.
_FIRST = (3, 1, -2, 2, 0, -1, 1, 2)
_SECOND = (0, 2, 1, -1, 3, 1, -2, 1)
#: The columns a fault pushes up.
_FAULT_COLUMNS = (1, 4, 6)


def _window(fault: bool, rng: random.Random) -> list[list[int]]:
    a = rng.randrange(-10, 11)
    b = rng.randrange(-10, 11)
    rows = []
    for frame in range(FRAMES):
        row = [
            100 + a * _FIRST[column] + b * _SECOND[column] + frame + rng.randrange(-3, 4)
            for column in range(COLUMNS)
        ]
        if fault:
            for column in _FAULT_COLUMNS:
                row[column] += 18 + rng.randrange(0, 8)
        rows.append(row)
    return rows


def generate() -> str:
    rng = random.Random(SEED)
    lines = [",".join(HEADER)]
    for index in range(WINDOWS):
        fault = index % FAULT_EVERY == FAULT_EVERY - 1
        condition = "fault" if fault else "normal"
        for row in _window(fault, rng):
            lines.append(",".join((condition, *(str(value) for value in row))))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    (Path(__file__).parent / "records.csv").write_text(generate(), encoding="utf-8")
