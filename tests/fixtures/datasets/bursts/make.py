"""Generate the ``bursts`` dataset: short attack bursts between normal CAN frames.

Feature 014. Shaped like an in-vehicle intrusion capture: ``normal`` traffic with a 20-frame ``dos``
burst every 200 frames, starting at frame 100. A window of 64 frames never holds a burst alone, so
the ``all_equal`` rule keeps no ``dos`` window at all (the review of 2026-11-16 measured exactly
this); the rule ``{any: dos}`` keeps one or more per burst. The values are arithmetic: a burst
floods one identifier at full length with a fixed payload.

Only ``randrange`` is used, so every Python in the matrix writes the same bytes. Principle XI: no
model produced any of it.

Run it with ``python tests/fixtures/datasets/bursts/make.py``; it writes ``frames.csv``.
"""

from __future__ import annotations

import random
from pathlib import Path

HEADER = ("label", "can_id", "dlc", "b0")
ROWS = 4000
BURST_EVERY = 200
BURST_START = 100
BURST_LENGTH = 20
SEED = 20261119
IDENTIFIERS = (0x0F1, 0x130, 0x2C0, 0x316, 0x43F, 0x545)


def label_of(index: int) -> str:
    offset = (index - BURST_START) % BURST_EVERY
    return "dos" if index >= BURST_START and offset < BURST_LENGTH else "normal"


def generate() -> str:
    rng = random.Random(SEED)
    lines = [",".join(HEADER)]
    for index in range(ROWS):
        label = label_of(index)
        if label == "dos":
            row = (label, "0", "8", "0")
        else:
            row = (
                label,
                str(rng.choice(IDENTIFIERS)),
                str(rng.randrange(2, 9)),
                str(rng.randrange(256)),
            )
        lines.append(",".join(row))
    return "\n".join(lines) + "\n"


def main() -> None:
    (Path(__file__).parent / "frames.csv").write_text(generate(), encoding="utf-8")


if __name__ == "__main__":
    main()
