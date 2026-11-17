"""Generate the ``soc`` dataset: a continuous number to predict.

Feature 014. Shaped like a battery state-of-charge log: ``soc`` falls a little every row and never
repeats within a file, so every window's rows disagree about the output. Before feature 014 that
dropped every window (the review of 2026-11-16 measured 156 of 156); with the ``last`` rule each
window takes its newest row's value. Two files, so the windows also have two recordings to respect.

The fall is 0.0005 per row rather than the review's 0.01, so a thousand rows stay between 0 and 1;
what matters is that no two consecutive rows agree. Values are written with four decimals.

Only ``randrange`` is used, so every Python in the matrix writes the same bytes. Principle XI: no
model produced any of it.

Run it with ``python tests/fixtures/datasets/soc/make.py``; it writes ``d1.csv`` and ``d2.csv``.
"""

from __future__ import annotations

import random
from pathlib import Path

HEADER = ("soc", "current", "voltage", "temp")
ROWS = 1000
STEP = 0.0005
SEED = 20261118


def generate(start: float, rng: random.Random) -> str:
    lines = [",".join(HEADER)]
    for index in range(ROWS):
        soc = start - STEP * index
        current = 12 + rng.randrange(-3, 4)
        voltage = 3.0 + 1.2 * soc + rng.randrange(-5, 6) / 1000
        temp = 25 + index // 100 + rng.randrange(0, 2)
        lines.append(f"{soc:.4f},{current},{voltage:.3f},{temp}")
    return "\n".join(lines) + "\n"


def main() -> None:
    rng = random.Random(SEED)
    here = Path(__file__).parent
    (here / "d1.csv").write_text(generate(1.0, rng), encoding="utf-8")
    (here / "d2.csv").write_text(generate(0.9, rng), encoding="utf-8")


if __name__ == "__main__":
    main()
