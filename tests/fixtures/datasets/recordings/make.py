"""Generate the ``recordings`` dataset: six recording sessions, one file each.

Feature 014. Shaped like an activity or machine-state capture split into sessions: each file is one
recording, holds stretches of both classes (``idle`` and ``move``), and has a length that is not a
multiple of 64, so a window grid that ran across files would shift from one file to the next. The
values are arithmetic: ``idle`` rows stay near a level, ``move`` rows swing.

Only ``randrange`` is used, so every Python in the matrix writes the same bytes. Principle XI: no
model produced any of it.

Run it with ``python tests/fixtures/datasets/recordings/make.py``; it writes ``r1.csv`` … ``r6.csv``
beside itself.
"""

from __future__ import annotations

import random
from pathlib import Path

HEADER = ("label", "a", "b", "c")
LENGTHS = (450, 517, 600, 389, 702, 498)
SEED = 20261117


def _row(label: str, index: int, rng: random.Random) -> tuple[str, ...]:
    if label == "idle":
        values = (50 + rng.randrange(-2, 3), 20 + rng.randrange(-2, 3), 5 + rng.randrange(0, 2))
    else:
        swing = (index % 8) * 6
        values = (50 + swing + rng.randrange(-4, 5), 20 - swing // 2 + rng.randrange(-4, 5), 30)
    return (label, *(str(value) for value in values))


def generate(length: int, rng: random.Random) -> str:
    lines = [",".join(HEADER)]
    label = "idle" if rng.randrange(2) == 0 else "move"
    written = 0
    while written < length:
        stretch = min(length - written, 90 + rng.randrange(0, 80))
        for index in range(stretch):
            lines.append(",".join(_row(label, index, rng)))
        written += stretch
        label = "move" if label == "idle" else "idle"
    return "\n".join(lines) + "\n"


def main() -> None:
    rng = random.Random(SEED)
    here = Path(__file__).parent
    for number, length in enumerate(LENGTHS, start=1):
        (here / f"r{number}.csv").write_text(generate(length, rng), encoding="utf-8")


if __name__ == "__main__":
    main()
