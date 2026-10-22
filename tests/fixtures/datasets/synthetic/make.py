"""Generate the one dataset this repository commits.

Why both a generator and its output are committed: a generated-at-test-time fixture cannot be
inspected when a test fails, and a committed file alone leaves nobody able to say what it is.
Together, with ``tests/unit/test_fixture_dataset.py`` asserting that regenerating produces the
same bytes, the file provably corresponds to this script.

It is not real data and does not pretend to be. The columns are shaped like a CAN capture so the
pilot manifest reads naturally; the values are arithmetic. Principle XI applies: no model and no
labelled data in this project comes from Claude, and a seeded standard-library generator is the
cheapest thing that is obviously not a model.

The layout is chosen to exercise the windowing rule, not to be learnable:

* 20 pure windows of 64 records for each of the manifest's four labels, and
* one deliberately mixed window — 32 records of ``normal`` followed by 32 of ``dos`` — so that
  at least one window is discarded and SC-010 has something to measure.

Everything is aligned to the window size, so the record count is an exact multiple of 64 and no
records are dropped as a remainder. That keeps the three counts in a run report unambiguous:
80 kept, 1 discarded for disagreeing about the label, 0 dropped.

Run it with ``python tests/fixtures/datasets/synthetic/make.py``; it writes ``records.csv`` beside
itself.
"""

from __future__ import annotations

import random
from pathlib import Path

HEADER = ("label", "can_id", "dlc", "b0", "b1", "b2")
LABELS = ("normal", "dos", "fuzzy", "replay")
WINDOW = 64
WINDOWS_PER_LABEL = 20
SEED = 20261022

#: Only ``randrange`` is used, and nothing that has ever changed between Python versions, because
#: the regeneration test runs on every Python in the matrix and must produce identical bytes.
_NORMAL_IDS = (291, 608, 790, 1072)


def _record(label: str, index: int, rng: random.Random) -> tuple[str, ...]:
    """One record. The label decides the shape, so the file is not noise."""
    if label == "normal":
        can_id = _NORMAL_IDS[index % len(_NORMAL_IDS)]
        base = 16 + rng.randrange(8)
        return (label, str(can_id), "8", str(base), str(base * 2 % 256), str(base * 3 % 256))
    if label == "dos":
        # The textbook denial-of-service injection: one identifier, saturated payload.
        return (label, "0", "8", "255", "255", str(248 + rng.randrange(8)))
    if label == "fuzzy":
        return (
            label,
            str(rng.randrange(2048)),
            str(rng.randrange(1, 9)),
            str(rng.randrange(256)),
            str(rng.randrange(256)),
            str(rng.randrange(256)),
        )
    # replay: a normal frame under a shifted identifier, which is what makes it hard.
    can_id = _NORMAL_IDS[index % len(_NORMAL_IDS)] + 1
    base = 16 + (index % 8)
    return (label, str(can_id), "8", str(base), str(base * 2 % 256), str(base * 3 % 256))


def rows() -> list[tuple[str, ...]]:
    rng = random.Random(SEED)
    out: list[tuple[str, ...]] = []
    for label in LABELS:
        for window in range(WINDOWS_PER_LABEL):
            for position in range(WINDOW):
                out.append(_record(label, window * WINDOW + position, rng))
    # The one window that spans a change of label, and must therefore be discarded.
    for position in range(WINDOW // 2):
        out.append(_record("normal", position, rng))
    for position in range(WINDOW // 2):
        out.append(_record("dos", position, rng))
    return out


def generate(destination: Path) -> Path:
    """Write ``records.csv`` into ``destination`` and return its path."""
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "records.csv"
    lines = [",".join(HEADER)]
    lines.extend(",".join(row) for row in rows())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    written = generate(Path(__file__).parent)
    print(f"{written}: {len(rows())} records")
