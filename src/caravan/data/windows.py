"""From records to samples, and from samples to splits.

Arithmetic over indices and labels — no array library, no framework. That is deliberate: these two
rules decide what the model is trained on, so their tests run on every Python in the matrix rather
than only where the training extra can be installed (research R5, R6).

Feature 014 made both rules aware of recordings. A recording is a stretch of rows taken in one go —
a file, or a run of equal values of the recording column — and no window crosses one. A window
starts every ``stride`` rows within its recording, takes its label by a rule, and the splits by
recording, by group and by block assign whole groups of windows, so neighbouring windows of one
recording do not sit on both sides of a part boundary (specs/014-recording-aware-windows).
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NoReturn

from caravan.manifest.errors import (
    RULE_CLASS_NOT_IN_EVERY_PART,
    RULE_DATASET_NO_SAMPLES,
    RULE_SPLIT_EMPTY,
    RULE_TOO_FEW_GROUPS,
    RULE_WINDOW_COLUMN_OR_VALUE,
    run_rule_error,
)

#: The split names, in the order a tie is broken by.
SPLIT_NAMES = ("train", "val", "test")

#: How many seeds after the stated one a split by recording or group tries before it gives up on
#: giving every part every class (research R4). Every attempt is reproducible from the report.
GROUP_RETRIES = 100

#: About how many blocks a stretch of one label is cut into by a blocked split (research R5).
BLOCKS_PER_STRETCH = 10

#: The window label rules (research R3). ``{"any": value}`` is the one with a value.
LABEL_RULES = ("all_equal", "last", "majority", "mean")


@dataclass(frozen=True)
class Recording:
    """A stretch of rows taken in one go: ``[start, end)`` in the concatenated sequence."""

    start: int
    end: int
    #: The data file it comes from, as its relative name; ``None`` for a bare label sequence.
    file: str | None = None
    #: The recording column's value, when the column cut the file.
    key: str | None = None

    @property
    def rows(self) -> int:
        return self.end - self.start

    @property
    def name(self) -> str:
        """How the report and a refusal name it."""
        base = self.file or "records"
        return f"{base}[{self.key}]" if self.key is not None else base


@dataclass(frozen=True)
class WindowPlan:
    """Which records form which sample, and what was thrown away doing it."""

    window: int | None
    records: int
    #: The first record index of each kept sample, in sequence order.
    kept: tuple[int, ...]
    #: The label of each kept sample, parallel to ``kept``.
    labels: tuple[str, ...]
    #: Windows whose records did not all carry the same label. Never labelled, always counted.
    discarded_mixed: int
    #: Records that did not fill a window: the rows after each recording's last window.
    dropped_remainder: int
    #: The part each kept sample belongs to, parallel to ``kept``, when the data names it
    #: (a fixed split, feature 007); ``None`` when the split is drawn by fractions.
    parts: tuple[str, ...] | None = None
    #: Windows whose records named different parts or groups. Never assigned, always counted.
    discarded_mixed_split: int = 0
    # --- feature 014 ----------------------------------------------------------------------------
    #: How many records apart two windows start within a recording; the window when ``None``.
    stride: int | None = None
    #: The label rule applied: a name of ``LABEL_RULES`` or ``{"any": value}``.
    rule: Any = "all_equal"
    #: The recordings the sequence was cut into.
    recordings: tuple[Recording, ...] = ()
    #: The index into ``recordings`` of each kept sample, parallel to ``kept``.
    recording_of: tuple[int, ...] = ()
    #: The group each kept sample belongs to, parallel to ``kept``, for a split by a column.
    groups: tuple[str, ...] | None = None
    #: Windows a ``majority`` rule could not label because two labels tied.
    discarded_tied: int = 0
    #: Per recording: its windows and the rows after its last window.
    per_recording: tuple[dict[str, Any], ...] = ()

    @property
    def samples(self) -> int:
        return len(self.kept)

    @property
    def step(self) -> int:
        return self.stride or self.window or 1

    @property
    def length(self) -> int:
        return self.window or 1

    @property
    def too_short(self) -> tuple[str, ...]:
        """The recordings shorter than one window, by name."""
        if self.window is None:
            return ()
        return tuple(r.name for r in self.recordings if r.rows < self.window)


@dataclass(frozen=True)
class SplitPlan:
    """Which samples belong to which split. Indices are positions in ``WindowPlan.kept``."""

    train: tuple[int, ...]
    val: tuple[int, ...]
    test: tuple[int, ...]
    stratified: bool
    #: ``None`` for a fixed split: the data decided, not a generator.
    seed: int | None
    #: label -> split -> count, written into the run report so the split is inspectable.
    per_label_counts: dict[str, dict[str, int]]
    #: ``fractions``, or ``column:<name>`` for a split the data decided (feature 007).
    source: str = "fractions"
    # --- feature 014 ----------------------------------------------------------------------------
    #: The effective type: random, stratify, fixed, recording, group or blocked.
    type: str = "random"
    #: Whether the manifest left the type to the data.
    derived: bool = False
    #: For recording, group and blocked: part -> the groups or blocks it received.
    assignment: dict[str, list[str]] = field(default_factory=dict)
    #: Windows left out because they shared a row with, or (blocked) adjoined, another part.
    purged: int = 0

    def indices(self, split: str) -> tuple[int, ...]:
        return getattr(self, split)  # type: ignore[no-any-return]

    @property
    def counts(self) -> dict[str, int]:
        return {name: len(self.indices(name)) for name in SPLIT_NAMES}

    @property
    def shares(self) -> dict[str, float]:
        """The share of windows each part actually received."""
        total = sum(self.counts.values()) or 1
        return {name: round(count / total, 4) for name, count in self.counts.items()}


# --- windows ------------------------------------------------------------------------------------


def _run_ends(values: Sequence[Any]) -> list[int]:
    """For each index, the first index after it where the value differs (or the length)."""
    ends = [0] * len(values)
    end = len(values)
    for index in range(len(values) - 1, -1, -1):
        if index + 1 < len(values) and values[index + 1] != values[index]:
            end = index + 1
        ends[index] = end
    return ends


def _rule_name(rule: Any) -> str:
    return "any" if isinstance(rule, Mapping) else str(rule)


def plan_windows(
    record_labels: Sequence[str],
    window: int | None,
    *,
    parts: Sequence[str] | None = None,
    recordings: Sequence[Recording] | None = None,
    stride: int | None = None,
    rule: Any = "all_equal",
    groups: Sequence[str] | None = None,
) -> WindowPlan:
    """Group records into samples.

    With a window, a sample is ``window`` consecutive records of one recording, and a new one starts
    every ``stride`` records (the window when not given: no overlap). Without a window, one record
    is one sample: the path of an image input, which nothing here changes.

    The label of a window follows ``rule`` (research R3): ``all_equal`` keeps a window only when its
    records agree, because majority voting has no answer for a tie and the last record's label
    mislabels the tail of every burst; ``last`` takes the newest record's, ``majority`` the most
    frequent (a tie is dropped), ``mean`` the mean of a number, and ``{"any": v}`` takes ``v`` when
    any record holds it and otherwise behaves as ``all_equal``.

    With ``parts`` (a fixed split, feature 007) or ``groups`` (a split by a column, feature 014), a
    window whose records name different parts or groups is discarded and counted the same way. A
    window mixed both ways counts as mixed by label.
    """
    total = len(record_labels)
    if recordings is None:
        recordings = (Recording(0, total),)
    recordings = tuple(recordings)
    recording_index = _recording_index(recordings, total)

    if window is None:
        if total == 0:
            _no_samples(total, window, 0, 0, 0, recordings)
        return WindowPlan(
            window=None,
            records=total,
            kept=tuple(range(total)),
            labels=tuple(record_labels),
            discarded_mixed=0,
            dropped_remainder=0,
            parts=None if parts is None else tuple(parts),
            stride=None,
            rule=rule,
            recordings=recordings,
            recording_of=tuple(recording_index),
            groups=None if groups is None else tuple(groups),
            per_recording=tuple(
                {
                    "file": r.file,
                    "key": r.key,
                    "rows": r.rows,
                    "windows": r.rows,
                    "leftover_rows": 0,
                }
                for r in recordings
            ),
        )

    step = stride or window
    name = _rule_name(rule)
    label_ends = _run_ends(record_labels)
    part_ends = _run_ends(parts) if parts is not None else None
    group_ends = _run_ends(groups) if groups is not None else None
    wanted = str(rule["any"]) if name == "any" else None
    if wanted is not None:
        if wanted not in set(record_labels):
            run_rule_error(
                RULE_WINDOW_COLUMN_OR_VALUE,
                "preprocessing.window_label",
                f"the any rule names {wanted!r}, and the output column never holds it",
                found=wanted,
                accepted=tuple(sorted(set(record_labels))),
            )
        seen = [0]
        for value in record_labels:
            seen.append(seen[-1] + (value == wanted))
    if name == "mean":
        sums = [0.0]
        for value in record_labels:
            sums.append(sums[-1] + float(value))

    kept: list[int] = []
    labels: list[str] = []
    kept_parts: list[str] = []
    kept_groups: list[str] = []
    kept_recording: list[int] = []
    per_recording: list[dict[str, Any]] = []
    examined = mixed = tied = mixed_split = remainder = 0

    for index, recording in enumerate(recordings):
        windows_here = 0
        last_end = recording.start
        start = recording.start
        while start + window <= recording.end:
            end = start + window
            examined += 1
            last_end = end
            uniform = label_ends[start] >= end
            if name == "all_equal":
                label = record_labels[start] if uniform else None
            elif name == "last":
                label = record_labels[end - 1]
            elif name == "mean":
                label = repr((sums[end] - sums[start]) / window)
            elif name == "majority":
                counts = Counter(record_labels[start:end]).most_common(2)
                label = counts[0][0] if len(counts) == 1 or counts[0][1] > counts[1][1] else None
                if label is None:
                    tied += 1
                    start += step
                    continue
            else:  # any
                label = (
                    wanted
                    if seen[end] - seen[start] > 0
                    else (record_labels[start] if uniform else None)
                )
            if label is None:
                mixed += 1
                start += step
                continue
            if part_ends is not None and part_ends[start] < end:
                mixed_split += 1
                start += step
                continue
            if group_ends is not None and group_ends[start] < end:
                mixed_split += 1
                start += step
                continue
            kept.append(start)
            labels.append(label)
            kept_recording.append(index)
            if parts is not None:
                kept_parts.append(parts[start])
            if groups is not None:
                kept_groups.append(groups[start])
            windows_here += 1
            start += step
        leftover = recording.end - last_end
        remainder += leftover
        per_recording.append(
            {
                "file": recording.file,
                "key": recording.key,
                "rows": recording.rows,
                "windows": windows_here,
                "leftover_rows": leftover,
            }
        )

    if not kept:
        _no_samples(total, window, examined, mixed + tied + mixed_split, remainder, recordings)

    return WindowPlan(
        window=window,
        records=total,
        kept=tuple(kept),
        labels=tuple(labels),
        discarded_mixed=mixed,
        dropped_remainder=remainder,
        parts=None if parts is None else tuple(kept_parts),
        discarded_mixed_split=mixed_split,
        stride=step,
        rule=rule,
        recordings=recordings,
        recording_of=tuple(kept_recording),
        groups=None if groups is None else tuple(kept_groups),
        discarded_tied=tied,
        per_recording=tuple(per_recording),
    )


def _recording_index(recordings: Sequence[Recording], total: int) -> list[int]:
    """The recording of every record; also checks that the recordings tile the sequence."""
    out = [0] * total
    cursor = 0
    for index, recording in enumerate(recordings):
        if recording.start != cursor or recording.end < recording.start:
            raise ValueError(f"recordings must tile the records in order; {recording} does not")
        for row in range(recording.start, recording.end):
            out[row] = index
        cursor = recording.end
    if cursor != total:
        raise ValueError(f"recordings cover {cursor} records of {total}")
    return out


def recordings_from(
    files: Sequence[tuple[str, int]], keys: Sequence[str] | None = None
) -> tuple[Recording, ...]:
    """The recordings of a dataset: one per file, cut again wherever ``keys`` change value.

    ``files`` are (relative name, rows) in sequence order; ``keys`` the recording column's text per
    record, or ``None`` when the manifest names no recording column.
    """
    out: list[Recording] = []
    start = 0
    for name, rows in files:
        end = start + rows
        if keys is None:
            out.append(Recording(start, end, name))
        else:
            cut = start
            for row in range(start + 1, end + 1):
                if row == end or keys[row] != keys[row - 1]:
                    out.append(Recording(cut, row, name, keys[cut]))
                    cut = row
            if start == end:
                out.append(Recording(start, end, name))
        start = end
    return tuple(out)


def _no_samples(
    records: int,
    window: int | None,
    examined: int,
    mixed: int,
    remainder: int,
    recordings: Sequence[Recording] = (),
) -> NoReturn:
    """DS-6, with every count that explains it.

    "No usable data" is never reported as a training run over zero samples, and never without the
    numbers that say why — too few records, every recording shorter than the window, or every
    window straddling a change of label.
    """
    longest = max(recordings, key=lambda r: r.rows, default=None)
    if window is not None and records < window:
        problem = (
            f"the dataset holds {records} records, fewer than the {window} one window needs, "
            "so there is nothing to train on"
        )
    elif window is not None and examined == 0 and longest is not None:
        problem = (
            f"every recording is shorter than the window of {window} records; the longest, "
            f"{longest.name}, holds {longest.rows}, and no window crosses from one recording to "
            "the next"
        )
    else:
        problem = (
            f"no usable sample remains: {records} records gave {examined} complete windows, "
            f"{mixed} of which were discarded because their records disagreed about the label "
            "or the part of a fixed split, "
            f"and {remainder} records did not fill a window"
        )
    run_rule_error(
        RULE_DATASET_NO_SAMPLES,
        "dataset",
        problem,
        found={
            "records": records,
            "window": window,
            "windows_examined": examined,
            "windows_discarded_mixed": mixed,
            "records_dropped_remainder": remainder,
        },
    )


# --- splits by fractions (features 002, 007) ----------------------------------------------------


def _largest_split(fractions: Mapping[str, float]) -> str:
    """The split a leftover sample goes to: the largest fraction, ties to the earlier name."""
    return min(SPLIT_NAMES, key=lambda name: (-fractions[name], SPLIT_NAMES.index(name)))


def _take(indices: list[int], fractions: Mapping[str, float]) -> dict[str, list[int]]:
    """Cut one pool into three parts by the procedure in ``contracts/dataset.md``."""
    size = len(indices)
    taken = {name: math.floor(size * fractions[name]) for name in SPLIT_NAMES}
    leftover = size - sum(taken.values())
    taken[_largest_split(fractions)] += leftover

    out: dict[str, list[int]] = {}
    cursor = 0
    for name in SPLIT_NAMES:
        out[name] = indices[cursor : cursor + taken[name]]
        cursor += taken[name]
    return out


def plan_split(
    plan: WindowPlan,
    fractions: Mapping[str, float] | None,
    *,
    stratified: bool,
    seed: int | None,
    labels: Sequence[str],
    column: str | None = None,
) -> SplitPlan:
    """Split samples — never records — reproducibly.

    The procedure is written down in ``contracts/dataset.md`` and implemented here verbatim,
    including which split a leftover sample goes to. "Shuffle and slice" is not reproducible from
    a report; this is. The standard library's generator is used rather than the framework's, so
    the split can be reproduced by someone who has no framework installed.

    With ``column`` the data has decided: each sample goes to the part its records named
    (feature 007). An empty part is refused the same way, naming the column.
    """
    if column is not None:
        return _fixed_split(plan, column, labels)
    assert fractions is not None and seed is not None
    pools: dict[str, list[int]] = {}
    if stratified:
        for label in labels:
            pools[label] = sorted(
                position for position, value in enumerate(plan.labels) if value == label
            )
    else:
        pools[""] = sorted(range(plan.samples))

    parts: dict[str, list[int]] = {name: [] for name in SPLIT_NAMES}
    per_label: dict[str, dict[str, int]] = {}
    for pool_name, pool in pools.items():
        shuffled = list(pool)
        random.Random(seed).shuffle(shuffled)
        cut = _take(shuffled, fractions)
        for name in SPLIT_NAMES:
            parts[name].extend(cut[name])
        if stratified:
            per_label[pool_name] = {name: len(cut[name]) for name in SPLIT_NAMES}

    if not stratified:
        for label in labels:
            per_label[label] = {
                name: sum(1 for position in parts[name] if plan.labels[position] == label)
                for name in SPLIT_NAMES
            }

    for name in SPLIT_NAMES:
        if not parts[name]:
            _empty_split(name, plan, fractions, per_label, stratified)
    if stratified:
        for label in labels:
            for name in SPLIT_NAMES:
                if per_label[label][name] == 0:
                    _empty_split(name, plan, fractions, per_label, stratified, label=label)

    return SplitPlan(
        train=tuple(sorted(parts["train"])),
        val=tuple(sorted(parts["val"])),
        test=tuple(sorted(parts["test"])),
        stratified=stratified,
        seed=seed,
        per_label_counts=per_label,
        type="stratify" if stratified else "random",
    )


def _empty_split(
    name: str,
    plan: WindowPlan,
    fractions: Mapping[str, float],
    per_label: Mapping[str, Mapping[str, int]],
    stratified: bool,
    label: str | None = None,
) -> NoReturn:
    """DS-8. The manifest already forbids a zero fraction, so an empty part means too little data.

    Naming the label matters: with a stratified split it is almost always one rare class that ran
    out, and "the test split is empty" would send the author looking in the wrong place.
    """
    where = f" for label {label!r}" if label else ""
    counts = (
        {key: dict(value) for key, value in per_label.items()}
        if stratified
        else {"all": dict(per_label.get(next(iter(per_label), ""), {}))}
    )
    run_rule_error(
        RULE_SPLIT_EMPTY,
        "preprocessing.split.probabilities",
        (
            f"the {name} split comes out empty{where}: {plan.samples} samples at a fraction of "
            f"{fractions[name]:g} leaves nothing, so there is no data to "
            + ("train on" if name == "train" else "measure against")
        ),
        found={"samples": plan.samples, "per_label": counts},
    )


def _fixed_split(plan: WindowPlan, column: str, labels: Sequence[str]) -> SplitPlan:
    """The parts the data named, in sample order."""
    if plan.parts is None:  # pragma: no cover - the stages always pass parts with a column
        raise ValueError("a fixed split needs the part of every sample")
    parts: dict[str, list[int]] = {name: [] for name in SPLIT_NAMES}
    for position, part in enumerate(plan.parts):
        parts[part].append(position)
    per_label = _per_label(plan, parts, labels)
    for name in SPLIT_NAMES:
        if not parts[name]:
            run_rule_error(
                RULE_SPLIT_EMPTY,
                "preprocessing.split.column",
                (
                    f"no window of the data is in the {name} part: column {column!r} names it "
                    "for no whole window, so there is no data to "
                    + ("train on" if name == "train" else "measure against")
                ),
                found={"samples": plan.samples, "per_label": per_label},
            )
    return SplitPlan(
        train=tuple(parts["train"]),
        val=tuple(parts["val"]),
        test=tuple(parts["test"]),
        stratified=False,
        seed=None,
        per_label_counts=per_label,
        source=f"column:{column}",
        type="fixed",
    )


def _per_label(
    plan: WindowPlan, parts: Mapping[str, Sequence[int]], labels: Sequence[str]
) -> dict[str, dict[str, int]]:
    return {
        label: {
            name: sum(1 for position in parts[name] if plan.labels[position] == label)
            for name in SPLIT_NAMES
        }
        for label in labels
    }


# --- splits by group: recording, group, blocked (feature 014) -----------------------------------


def _assign(
    order: Sequence[str], sizes: Mapping[str, int], fractions: Mapping[str, float]
) -> dict[str, str]:
    """Groups to parts: one each to the smallest parts first, then each to the largest deficit.

    Giving every part one group before the deficit walk is what keeps a small part from coming out
    empty when the first groups are large (research R4, R5).
    """
    total = sum(sizes[key] for key in order)
    filled = dict.fromkeys(SPLIT_NAMES, 0)
    out: dict[str, str] = {}
    seeding = sorted(SPLIT_NAMES, key=lambda name: (fractions[name], -SPLIT_NAMES.index(name)))
    for key, part in zip(order, seeding, strict=False):
        out[key] = part
        filled[part] += sizes[key]
    for key in order[len(seeding) :]:
        part = max(
            SPLIT_NAMES,
            key=lambda name: (fractions[name] * total - filled[name], -SPLIT_NAMES.index(name)),
        )
        out[key] = part
        filled[part] += sizes[key]
    return out


def _group_split(
    plan: WindowPlan,
    keys: Sequence[str],
    fractions: Mapping[str, float],
    *,
    seed: int,
    labels: Sequence[str],
    kind: str,
    source: str,
    derived: bool,
) -> SplitPlan:
    """Every window of a group in one part; retry seeds until every part has every class."""
    order: list[str] = []
    sizes: Counter[str] = Counter()
    for key in keys:
        if key not in sizes:
            order.append(key)
        sizes[key] += 1
    if len(order) < len(SPLIT_NAMES):
        run_rule_error(
            RULE_TOO_FEW_GROUPS,
            "preprocessing.split.type",
            (
                f"a split by {kind} needs at least {len(SPLIT_NAMES)} {kind}s, one for each "
                f"part, and the data has {len(order)}; a blocked split cuts recordings into "
                "blocks instead"
            ),
            found={"groups": len(order), "parts": len(SPLIT_NAMES)},
            accepted=("blocked",),
        )
    for attempt in range(GROUP_RETRIES):
        shuffled = list(order)
        random.Random(seed + attempt).shuffle(shuffled)
        assigned = _assign(shuffled, sizes, fractions)
        parts: dict[str, list[int]] = {name: [] for name in SPLIT_NAMES}
        for position, key in enumerate(keys):
            parts[assigned[key]].append(position)
        per_label = _per_label(plan, parts, labels)
        if all(parts.values()) and all(
            count > 0 for counts in per_label.values() for count in counts.values()
        ):
            return _finish(
                plan,
                parts,
                per_label,
                seed=seed + attempt,
                kind=kind,
                source=source,
                derived=derived,
                stratified=False,
                assignment={
                    name: [key for key in order if assigned[key] == name] for name in SPLIT_NAMES
                },
                adjacency=False,
            )
    per_group = {
        key: dict(Counter(plan.labels[p] for p, k in enumerate(keys) if k == key)) for key in order
    }
    run_rule_error(
        RULE_CLASS_NOT_IN_EVERY_PART,
        "preprocessing.split.type",
        (
            f"no assignment of the {len(order)} {kind}s to the parts gives every part every class "
            f"(seeds {seed} to {seed + GROUP_RETRIES - 1} tried); a class held by too few {kind}s "
            "cannot be in training, validation and test at once"
        ),
        found={"windows_per_class_per_group": per_group},
    )


def _blocks(plan: WindowPlan, by_label: bool) -> list[tuple[str, str, list[int]]]:
    """Contiguous blocks of windows within each stretch of one label of each recording.

    Returns (block name, pool, positions). A stretch is a run of consecutive kept windows of one
    recording with one label (one label for all, without classes); it is cut into about
    ``BLOCKS_PER_STRETCH`` blocks, none smaller than the purge at its edge can afford.
    """
    stretches: list[tuple[str, list[int]]] = []
    current: list[int] = []
    for position in range(plan.samples):
        pool = plan.labels[position] if by_label else ""
        if current:
            previous = current[-1]
            same = (
                plan.recording_of[previous] == plan.recording_of[position]
                and (plan.labels[previous] if by_label else "") == pool
            )
            if not same:
                stretches.append((plan.labels[previous] if by_label else "", current))
                current = []
        current.append(position)
    if current:
        stretches.append((plan.labels[current[-1]] if by_label else "", current))

    # A block must outlast what the purge takes at its edge: a window touches up to
    # ceil(window / step) windows on each side, so a block of fewer would lose most of itself
    # (found by tests/unit/test_split_report.py with a stride of half the window).
    reach = math.ceil(plan.length / plan.step)
    smallest = 2 * reach + 1
    out: list[tuple[str, str, list[int]]] = []
    for pool, positions in stretches:
        size = max(smallest, round(len(positions) / BLOCKS_PER_STRETCH))
        for first in range(0, len(positions), size):
            chunk = positions[first : first + size]
            recording = plan.recordings[plan.recording_of[chunk[0]]]
            begin = plan.kept[chunk[0]]
            end = plan.kept[chunk[-1]] + plan.length
            out.append((f"{recording.name}[{begin}:{end}]", pool, chunk))
    return out


def _blocked_split(
    plan: WindowPlan,
    fractions: Mapping[str, float],
    *,
    seed: int,
    labels: Sequence[str],
    derived: bool,
) -> SplitPlan:
    """Contiguous blocks to parts, per class; then windows touching another part are left out."""
    by_label = bool(labels)
    blocks = _blocks(plan, by_label)
    pools: dict[str, list[tuple[str, list[int]]]] = {}
    for name, pool, positions in blocks:
        pools.setdefault(pool, []).append((name, positions))
    rng = random.Random(seed)
    parts: dict[str, list[int]] = {name: [] for name in SPLIT_NAMES}
    assignment: dict[str, list[str]] = {name: [] for name in SPLIT_NAMES}
    for pool in sorted(pools):
        members = pools[pool]
        if len(members) < len(SPLIT_NAMES):
            windows = sum(len(positions) for _, positions in members)
            if by_label:
                run_rule_error(
                    RULE_CLASS_NOT_IN_EVERY_PART,
                    "preprocessing.split.type",
                    (
                        f"class {pool!r} has {windows} windows in {len(members)} block(s), and a "
                        f"blocked split needs at least {len(SPLIT_NAMES)} to give every part some; "
                        "it occurs in too short a stretch of the data"
                    ),
                    found={"class": pool, "windows": windows, "blocks": len(members)},
                )
            run_rule_error(
                RULE_TOO_FEW_GROUPS,
                "preprocessing.split.type",
                (
                    f"the data gives {windows} windows in {len(members)} block(s), and a blocked "
                    f"split needs at least {len(SPLIT_NAMES)}"
                ),
                found={"windows": windows, "blocks": len(members)},
            )
        order = [name for name, _ in members]
        rng.shuffle(order)
        sizes = {name: len(positions) for name, positions in members}
        assigned = _assign(order, sizes, fractions)
        for name, positions in members:
            parts[assigned[name]].extend(positions)
            assignment[assigned[name]].append(name)
    for name in SPLIT_NAMES:
        parts[name].sort()
    return _finish(
        plan,
        parts,
        _per_label(plan, parts, labels),
        seed=seed,
        kind="blocked",
        source="blocked",
        derived=derived,
        stratified=by_label,
        assignment=assignment,
        adjacency=True,
    )


def _finish(
    plan: WindowPlan,
    parts: Mapping[str, list[int]],
    per_label: dict[str, dict[str, int]],
    *,
    seed: int,
    kind: str,
    source: str,
    derived: bool,
    stratified: bool,
    assignment: dict[str, list[str]],
    adjacency: bool,
) -> SplitPlan:
    kept, purged = purge(plan, parts, adjacency=adjacency)
    per_label = _per_label(plan, kept, list(per_label))
    for name in SPLIT_NAMES:
        if not kept[name]:
            run_rule_error(
                RULE_SPLIT_EMPTY,
                "preprocessing.split.type",
                (
                    f"the {name} part comes out empty after windows on part boundaries were left "
                    f"out; {plan.samples} windows are too few for a {kind} split"
                ),
                found={"samples": plan.samples, "per_label": per_label},
            )
    return SplitPlan(
        train=tuple(kept["train"]),
        val=tuple(kept["val"]),
        test=tuple(kept["test"]),
        stratified=stratified,
        seed=seed,
        per_label_counts=per_label,
        source=source,
        type=kind,
        derived=derived,
        assignment=assignment,
        purged=purged,
    )


def purge(
    plan: WindowPlan, parts: Mapping[str, Sequence[int]], *, adjacency: bool
) -> tuple[dict[str, list[int]], int]:
    """Leave out every window that shares a row with — or, with ``adjacency``, directly follows —
    a kept window of another part in the same recording (FR-018).

    Walks each recording in row order and compares a window with the last window kept before it, so
    after a change of part exactly the windows that would touch the previous part are dropped.
    """
    part_of: dict[int, str] = {}
    for name, positions in parts.items():
        for position in positions:
            part_of[position] = name
    out: dict[str, list[int]] = {name: [] for name in SPLIT_NAMES}
    purged = 0
    previous: tuple[int, int, str] | None = None  # recording, end row, part
    for position in sorted(part_of, key=lambda p: plan.kept[p]):
        start = plan.kept[position]
        part = part_of[position]
        recording = plan.recording_of[position] if plan.recording_of else 0
        touches = previous is not None and (
            start < previous[1] or (adjacency and start == previous[1])
        )
        if touches and previous[0] == recording and previous[2] != part:  # type: ignore[index]
            purged += 1
            continue
        out[part].append(position)
        previous = (recording, start + plan.length, part)
    return out, purged


# --- the split a manifest asks for ---------------------------------------------------------------


def derive_split_type(plan: WindowPlan) -> str:
    """``recording`` when as many recordings as parts yield windows, ``blocked`` otherwise."""
    with_windows = len(set(plan.recording_of))
    return "recording" if with_windows >= len(SPLIT_NAMES) else "blocked"


def split_for(
    plan: WindowPlan, spec: Mapping[str, object], *, seed: int, labels: Sequence[str]
) -> SplitPlan:
    """The split a resolved ``preprocessing.split`` asks for.

    ``labels`` are the classes a stratified or blocked split draws per; a ``number`` output has
    none. ``derived`` (feature 014) is decided here from the data and recorded on the plan.
    """
    kind = str(spec["type"])
    if kind == "fixed":
        return plan_split(
            plan, None, stratified=False, seed=None, labels=labels, column=str(spec["column"])
        )
    probabilities = [float(value) for value in spec["probabilities"]]  # type: ignore[attr-defined]
    fractions = dict(zip(SPLIT_NAMES, probabilities, strict=True))
    if kind == "derived":
        kind = derive_split_type(plan)
        derived = True
    else:
        # A later stage reads the run's resolved manifest, where the data stage already wrote the
        # type it decided and marked it derived; the report says so in every stage alike.
        derived = spec.get("derived") is True  # type: ignore[union-attr]
    if kind == "recording":
        keys = [plan.recordings[index].name for index in plan.recording_of]
        return _group_split(
            plan,
            keys,
            fractions,
            seed=seed,
            labels=labels,
            kind="recording",
            source="recording",
            derived=derived,
        )
    if kind == "group":
        if plan.groups is None:  # pragma: no cover - the stages always pass groups with a column
            raise ValueError("a group split needs the group of every sample")
        return _group_split(
            plan,
            plan.groups,
            fractions,
            seed=seed,
            labels=labels,
            kind="group",
            source=f"group:{spec['column']}",
            derived=False,
        )
    if kind == "blocked":
        return _blocked_split(plan, fractions, seed=seed, labels=labels, derived=derived)
    return plan_split(plan, fractions, stratified=kind == "stratify", seed=seed, labels=labels)
