"""How many rows go into one prediction: a table and a proposal from the data (research R12).

The counts come from the data stage's own planner and split (feature 014), so what this table says
is what ``build`` later does: windows inside each recording, the label rule of the output type, the
split derived from the recordings, and the windows per class that land in the test part.
"""

from __future__ import annotations

import itertools
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from caravan.data.windows import plan_windows, recordings_from, split_for
from caravan.manifest.errors import RunRuleFailure
from caravan.manifest.schema.preprocessing import DEFAULT_PROBABILITIES

CANDIDATES = (4, 8, 16, 32, 64, 128)
#: The proposal loses at most this share of windows to mixed labels…
MAX_LOST = 0.05
#: …and keeps at least this many test windows of every class.
MIN_TEST_PER_CLASS = 5
SEED = 42
STRIP_ROWS = 70


@dataclass
class WindowRow:
    size: int
    #: Windows kept in total and lost to labels that differ inside them.
    kept: int = 0
    lost: int = 0
    #: Test windows per class (one pool, ``""``, for a number output).
    test: dict[str, int] = field(default_factory=dict)
    split: str = ""
    #: Why this size cannot be used, when it cannot.
    refused: str = ""

    @property
    def lost_share(self) -> float:
        total = self.kept + self.lost
        return self.lost / total if total else 1.0

    @property
    def usable(self) -> bool:
        return not self.refused and self.kept > 0


@dataclass
class WindowTable:
    rows: list[WindowRow]
    classes: tuple[str, ...]
    proposal: int | None
    reason: str
    rule: str

    def row(self, size: int) -> WindowRow | None:
        return next((row for row in self.rows if row.size == size), None)


def label_rule(output_type: str) -> str:
    """The rule feature 014 resolves when the manifest states none."""
    return "last" if output_type == "number" else "all_equal"


def measure(
    labels: Sequence[str],
    files: Sequence[tuple[str, int]],
    output_type: str,
    size: int,
) -> WindowRow:
    """One candidate size, measured as the data stage would cut and split it."""
    rule = label_rule(output_type)
    if output_type == "number":
        labels = [repr(float(value)) if value else value for value in labels]
    row = WindowRow(size)
    try:
        plan = plan_windows(labels, size, recordings=recordings_from(files), rule=rule)
    except RunRuleFailure as failure:
        row.refused = failure.finding.problem
        return row
    row.kept = plan.samples
    row.lost = plan.discarded_mixed + plan.discarded_tied
    classes = () if output_type == "number" else tuple(sorted(set(plan.labels)))
    spec = {"type": "derived", "probabilities": list(DEFAULT_PROBABILITIES), "column": None}
    try:
        split = split_for(plan, spec, seed=SEED, labels=classes)
    except RunRuleFailure as failure:
        row.refused = failure.finding.problem
        return row
    row.split = split.type
    counted = Counter(plan.labels[position] for position in split.indices("test"))
    if classes:
        row.test = {name: counted.get(name, 0) for name in classes}
    else:
        row.test = {"": len(split.indices("test"))}
    return row


def _shortest_run(labels: Sequence[str]) -> int:
    """The fewest consecutive rows a label holds, a run cut only by a change of label."""
    shortest = len(labels)
    run = 1
    for before, after in itertools.pairwise(labels):
        if after == before:
            run += 1
        else:
            shortest = min(shortest, run)
            run = 1
    return shortest


def table(
    labels: Sequence[str],
    files: Sequence[tuple[str, int]],
    output_type: str,
    *,
    extra: Sequence[int] = (),
    fits: Callable[[int], str | None] | None = None,
) -> WindowTable:
    """Every candidate that fits the longest recording, and the proposal.

    ``extra`` adds sizes beyond the powers of two: the proposed template's own window, so data cut
    for it (the anomaly fixture's 5 rows) is measured at that size too.
    """
    longest = max((rows for _, rows in files), default=0)
    sizes = sorted({*CANDIDATES, *(size for size in extra if size > 0)})
    sizes = [size for size in sizes if size <= longest]
    rows = []
    for size in sizes:
        problem = fits(size) if fits is not None else None
        rows.append(
            WindowRow(size, refused=problem)
            if problem
            else measure(labels, files, output_type, size)
        )
    classes: tuple[str, ...] = ()
    for row in rows:
        if row.usable:
            classes = tuple(row.test)
            break
    rule = label_rule(output_type)

    def enough(row: WindowRow) -> bool:
        return (
            row.usable
            and row.lost_share <= MAX_LOST
            and all(count >= MIN_TEST_PER_CLASS for count in row.test.values())
        )

    good = [row for row in rows if enough(row)]
    if good:
        best = good[-1]
        if output_type == "number":
            reason = (
                f"a number output takes the newest row's value, so no window is lost; "
                f"{best.size} rows still leaves {best.test.get('', 0)} test windows"
            )
        else:
            run = _shortest_run(labels)
            reason = (
                f"in your data a label holds for at least {run} rows at a time; at "
                f"{best.size} rows {best.lost_share:.0%} of windows mix two labels and every "
                f"class keeps at least {min(best.test.values())} test windows"
            )
        return WindowTable(rows, classes, best.size, reason, rule)
    usable = [row for row in rows if row.usable]
    if usable:
        best = min(usable, key=lambda row: (row.lost_share, -row.size))
        reason = (
            f"no size keeps {MIN_TEST_PER_CLASS} test windows of every class with at most "
            f"{MAX_LOST:.0%} lost; {best.size} rows loses the fewest"
        )
        return WindowTable(rows, classes, best.size, reason, rule)
    return WindowTable(rows, classes, None, "no candidate size yields windows in this data", rule)


def strip(
    labels: Sequence[str], size: int, *, width: int = STRIP_ROWS, number: bool = False
) -> list[str]:
    """About ``width`` rows around the first change of label, cut into windows of ``size``.

    Three lines: the rows (one letter per label), the windows, and what each window learns — the
    label, or ``✗`` when the rows inside it disagree (all_equal) and it is lost.
    """
    if not labels:
        return []
    if number:
        shown = min(len(labels), max(width // size, 1) * size)
        box = "[" + "─" * (size - 2) + "]" if size >= 2 else "|"
        cut = box * (shown // size)
        return [
            f"rows 0 to {shown}, cut into windows of {size}",
            "windows  " + cut,
            "learns   the value of each window's last row (a number output; none is lost)",
        ]
    change = next(
        (i for i in range(1, len(labels)) if labels[i] != labels[i - 1]), len(labels) // 2
    )
    start = max(0, (change - width // 2) // size * size)
    shown = labels[start : start + width]
    shown = shown[: len(shown) // size * size] or shown
    letters = {value: (value[:1] or "?") for value in sorted(set(shown))}
    row_line = "".join(letters[value] for value in shown)
    windows = []
    learns = []
    for offset in range(0, len(shown) - size + 1, size):
        part = shown[offset : offset + size]
        windows.append("[" + "─" * (size - 2) + "]" if size >= 2 else "|")
        mark = letters[part[0]] if len(set(part)) == 1 else "✗"
        learns.append(mark.center(size))
    key = ", ".join(f"{letter} = {value}" for value, letter in letters.items())
    return [
        f"rows {start} to {start + len(shown)}, around the first change of label",
        "rows     " + row_line,
        "windows  " + "".join(windows),
        "learns   " + "".join(learns),
        f"{key}; ✗ = labels differ, window lost",
    ]
