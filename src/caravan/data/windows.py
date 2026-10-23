"""From records to samples, and from samples to splits.

Arithmetic over indices and labels — no array library, no framework. That is deliberate: these two
rules decide what the model is trained on, so their tests run on every Python in the matrix rather
than only where the training extra can be installed (research R5, R6).
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import NoReturn

from caravan.manifest.errors import RULE_DATASET_NO_SAMPLES, RULE_SPLIT_EMPTY, run_rule_error

#: The split names, in the order a tie is broken by.
SPLIT_NAMES = ("train", "val", "test")


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
    #: Records at the end of the sequence that did not fill a window.
    dropped_remainder: int
    #: The part each kept sample belongs to, parallel to ``kept``, when the data names it
    #: (a fixed split, feature 007); ``None`` when the split is drawn by fractions.
    parts: tuple[str, ...] | None = None
    #: Windows whose records named different parts. Never assigned, always counted.
    discarded_mixed_split: int = 0

    @property
    def samples(self) -> int:
        return len(self.kept)


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

    def indices(self, split: str) -> tuple[int, ...]:
        return getattr(self, split)  # type: ignore[no-any-return]

    @property
    def counts(self) -> dict[str, int]:
        return {name: len(self.indices(name)) for name in SPLIT_NAMES}


def plan_windows(
    record_labels: Sequence[str],
    window: int | None,
    *,
    parts: Sequence[str] | None = None,
) -> WindowPlan:
    """Group records into samples.

    With a window, a sample is ``window`` consecutive records and windows do not overlap —
    overlapping windows share records, so one can land in train and another in test, and the test
    score stops meaning anything. Without a window, one record is one sample: a path no manifest
    can reach while the only registered template requires a window, which is why it is tested
    directly rather than through a manifest (FR-024).

    A window whose records disagree about the label is discarded rather than given a label it
    cannot be known to have (FR-025). Majority voting has no answer for a tie, and the last
    record's label mislabels the tail of every burst.

    With ``parts`` (a fixed split, feature 007), a window whose records name different parts is
    discarded and counted the same way. A window mixed both ways counts as mixed by label.
    """
    total = len(record_labels)

    if window is None:
        if total == 0:
            _no_samples(total, window, 0, 0, 0)
        return WindowPlan(
            window=None,
            records=total,
            kept=tuple(range(total)),
            labels=tuple(record_labels),
            discarded_mixed=0,
            dropped_remainder=0,
            parts=None if parts is None else tuple(parts),
        )

    complete = total // window
    remainder = total - complete * window

    kept: list[int] = []
    labels: list[str] = []
    kept_parts: list[str] = []
    mixed = 0
    mixed_split = 0
    for index in range(complete):
        start = index * window
        span = record_labels[start : start + window]
        first = span[0]
        if any(label != first for label in span):
            mixed += 1
            continue
        if parts is not None:
            named = parts[start : start + window]
            if any(part != named[0] for part in named):
                mixed_split += 1
                continue
            kept_parts.append(named[0])
        kept.append(start)
        labels.append(first)

    if not kept:
        _no_samples(total, window, complete, mixed + mixed_split, remainder)

    return WindowPlan(
        window=window,
        records=total,
        kept=tuple(kept),
        labels=tuple(labels),
        discarded_mixed=mixed,
        dropped_remainder=remainder,
        parts=None if parts is None else tuple(kept_parts),
        discarded_mixed_split=mixed_split,
    )


def _no_samples(
    records: int, window: int | None, examined: int, mixed: int, remainder: int
) -> NoReturn:
    """DS-6, with every count that explains it.

    "No usable data" is never reported as a training run over zero samples, and never without the
    numbers that say why — too few records, or every window straddling a change of label.
    """
    if window is not None and records < window:
        problem = (
            f"the dataset holds {records} records, fewer than the {window} one window needs, "
            "so there is nothing to train on"
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
        "dataset.source",
        problem,
        found={
            "records": records,
            "window": window,
            "windows_examined": examined,
            "windows_discarded_mixed": mixed,
            "records_dropped_remainder": remainder,
        },
    )


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
        f"dataset.split.{name}",
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
    per_label = {
        label: {
            name: sum(1 for position in parts[name] if plan.labels[position] == label)
            for name in SPLIT_NAMES
        }
        for label in labels
    }
    for name in SPLIT_NAMES:
        if not parts[name]:
            run_rule_error(
                RULE_SPLIT_EMPTY,
                "dataset.split.column",
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
    )


def split_for(
    plan: WindowPlan, spec: Mapping[str, object], *, seed: int, labels: Sequence[str]
) -> SplitPlan:
    """The split a resolved ``dataset.split`` asks for, in either form (feature 007)."""
    column = spec.get("column")
    if column is not None:
        return plan_split(
            plan, None, stratified=False, seed=None, labels=labels, column=str(column)
        )
    return plan_split(
        plan,
        {name: float(spec[name]) for name in SPLIT_NAMES},  # type: ignore[arg-type]
        stratified=bool(spec["stratified"]),
        seed=seed,
        labels=labels,
    )
