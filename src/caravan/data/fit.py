"""Fitting each feature's preprocessing on the training part (feature 008, research R6, R7).

Core module, standard library only: what a feature's preprocessing learns from the data decides
what the model is trained on, so these rules are tested on every Python in the matrix, and a reader
can reproduce them without a framework.

Every function here is handed the values of the **training part only**. Ludwig fits on all parts
together, which leaks the test part into the preprocessing (research note, section 5); Caravan
does not. What a function returns is what ``data/preprocessing.json`` records and what the
pipeline merges into the resolved manifest under the feature's ``preprocessing.fitted``, so it is
part of the keys of every later stage (Principle III).

Values arrive as the reader gives them: a number as a float, ``nan`` when the cell was empty; a
category or binary value as the text of its cell, ``""`` when empty.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from caravan.manifest.errors import (
    RULE_BINARY_SPELLINGS,
    RULE_CLASS_OUTSIDE_TRAIN,
    RULE_DATASET_LABELS,
    RULE_TOO_FEW_CLASSES,
    run_rule_error,
)

#: The symbol Ludwig uses for "unknown"; as a category's fill value it means a missing reading is
#: unknown rather than a value of its own.
UNKNOWN = "<UNK>"

#: The index of "unknown" in every input vocabulary: a value the training part did not show lands
#: there, on the device as much as here.
UNKNOWN_INDEX = 0

#: Ludwig's spellings of true and false for a binary column (compared case-insensitively).
TRUE_SPELLINGS = frozenset({"true", "1", "1.0", "yes", "y", "t", "on"})
FALSE_SPELLINGS = frozenset({"false", "0", "0.0", "no", "n", "f", "off"})

#: Noted in the fitted record when a column is constant on the training part.
SCALE_ZERO_NOTE = "the column is constant on the training part; its scale is set to 1"


# --- number ------------------------------------------------------------------------------------


def fit_number(
    values: Sequence[float],
    *,
    normalization: str | None,
    strategy: str,
    fill_value: float,
) -> dict[str, Any]:
    """The shift and scale of a ``number`` feature, and the value that fills a missing reading.

    The statistics are computed on the filled values: they describe what the model is trained on.
    ``zscore`` is the mean and the population standard deviation, ``minmax`` the minimum and the
    range, ``iq`` the median and the interquartile range (Ludwig's definitions). A scale of zero —
    a constant column — becomes 1, with a note, rather than a division by zero.
    """
    present = [float(value) for value in values if not math.isnan(value)]
    missing = len(values) - len(present)
    fill = statistics.fmean(present) if strategy == "fill_with_mean" and present else fill_value
    filled = present + [float(fill)] * missing
    shift, scale = _shift_and_scale(filled, normalization)
    out: dict[str, Any] = {
        "normalization": normalization,
        "shift": shift,
        "scale": scale,
        "fill": float(fill),
    }
    if normalization is not None and scale == 1.0 and _spread(filled, normalization) == 0.0:
        out["note"] = SCALE_ZERO_NOTE
    return out


def _spread(values: Sequence[float], normalization: str) -> float:
    if not values:
        return 0.0
    if normalization == "zscore":
        return statistics.pstdev(values)
    if normalization == "minmax":
        return max(values) - min(values)
    quartiles = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else []
    return quartiles[2] - quartiles[0] if quartiles else 0.0


def _shift_and_scale(values: Sequence[float], normalization: str | None) -> tuple[float, float]:
    if normalization is None or not values:
        return 0.0, 1.0
    if normalization == "zscore":
        shift = statistics.fmean(values)
    elif normalization == "minmax":
        shift = min(values)
    else:
        shift = statistics.median(values)
    scale = _spread(values, normalization)
    return float(shift), float(scale) if scale > 0 else 1.0


def apply_number(value: float, fitted: Mapping[str, Any]) -> float:
    """What the model's ``Standardize`` computes for one raw value, for tests and readers."""
    return (value - fitted["shift"]) / fitted["scale"]


# --- category ------------------------------------------------------------------------------------


def _is_integer(text: str) -> bool:
    try:
        int(text)
    except ValueError:
        return False
    return True


def by_frequency(counts: Mapping[str, int]) -> list[str]:
    """Values ordered by count, descending, ties by text: Ludwig's order, made deterministic."""
    return sorted(counts, key=lambda value: (-counts[value], value))


def fit_category(
    values: Iterable[str],
    *,
    most_common: int,
    fill_value: Any,
    pinned: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """The vocabulary of a ``category`` input and the codes the device passes.

    The vocabulary is the ``most_common`` most frequent values, or the pinned list in its order;
    everything else is "unknown", index 0, and ``cut`` counts the distinct values that were cut.

    A column whose values are all integers is passed to the device as those integers, and the model
    compares against them: ``codes`` is the vocabulary itself and ``text_codes`` is ``None``. A
    column of text is passed as codes 1..V in vocabulary order, and ``text_codes`` is the table a
    firmware uses. ``missing`` is what a firmware passes when a reading is absent.
    """
    explicit_fill = fill_value is not None and str(fill_value) != UNKNOWN
    raw = [str(value).strip() for value in values]
    filled = [str(fill_value) if value == "" and explicit_fill else value for value in raw]
    counts = Counter(value for value in filled if value != "" and value != UNKNOWN)
    stated = None if pinned is None else [str(value) for value in pinned]
    integer = all(_is_integer(value) for value in counts) and (
        stated is None or all(_is_integer(value) for value in stated)
    )

    if stated is None:
        ordered = by_frequency(counts)
        vocab_text = ordered[:most_common]
    else:
        vocab_text = stated
    cut = sum(1 for value in counts if value not in set(vocab_text))

    if integer:
        vocab: list[Any] = [int(value) for value in vocab_text]
        codes = list(vocab)
        text_codes = None
        # Any integer that is not in the vocabulary lands in "unknown"; without a fill value of the
        # author's, this one is stated so a firmware author need not choose.
        missing = int(str(fill_value)) if explicit_fill else min(-1, min(codes, default=0) - 1)
    else:
        vocab = list(vocab_text)
        codes = list(range(1, len(vocab) + 1))
        text_codes = {text: code for text, code in zip(vocab, codes, strict=True)}
        missing = text_codes.get(str(fill_value), UNKNOWN_INDEX) if explicit_fill else UNKNOWN_INDEX
    return {
        "vocab": vocab,
        "codes": codes,
        "text_codes": text_codes,
        "cut": cut,
        "unknown_index": UNKNOWN_INDEX,
        "missing": missing,
    }


def category_code(value: str, fitted: Mapping[str, Any]) -> int:
    """The int32 a firmware passes for one cell of a ``category`` column."""
    text = value.strip()
    if text == "":
        return int(fitted["missing"])
    table = fitted["text_codes"]
    if table is not None:
        return int(table.get(text, UNKNOWN_INDEX))
    try:
        return int(text)
    except ValueError:
        return int(fitted["missing"])


# --- binary --------------------------------------------------------------------------------------


def fit_binary(
    values: Iterable[str],
    *,
    fallback_true_label: str | None,
    path: str,
    fill_value: Any = False,
) -> dict[str, Any]:
    """Which spelling of a ``binary`` column is true, as Ludwig reads it.

    With ``fallback_true_label``, that spelling is true and every other one false. Without it, the
    spellings Ludwig knows (yes/no, true/false, 1/0, ...) are read as such; two other spellings are
    read with the one that sorts second as true, and noted. More than two other spellings are
    refused (DS-15): which of them is true cannot be known.
    """
    spellings = sorted({str(value).strip() for value in values} - {""})
    table: dict[str, int] = {}
    note = None
    if fallback_true_label is not None:
        table = {spelling: int(spelling == fallback_true_label) for spelling in spellings}
        true_spelling: str | None = fallback_true_label
    elif all(_standard(spelling) is not None for spelling in spellings):
        table = {spelling: int(_standard(spelling)) for spelling in spellings}  # type: ignore[arg-type]
        true_spelling = next((s for s in spellings if table[s] == 1), None)
    elif len(spellings) <= 2:
        table = {
            spelling: int(index == len(spellings) - 1) for index, spelling in enumerate(spellings)
        }
        true_spelling = spellings[-1]
        note = (
            f"{true_spelling!r} is read as true because it sorts second; state "
            "preprocessing.fallback_true_label to choose"
        )
    else:
        run_rule_error(
            RULE_BINARY_SPELLINGS,
            path,
            (
                f"the binary column holds {len(spellings)} spellings, and which of them is true "
                "cannot be known; state preprocessing.fallback_true_label, or use a category"
            ),
            found=spellings,
        )
    out: dict[str, Any] = {
        "spellings": table,
        "true_spelling": true_spelling,
        "missing": binary_code(str(fill_value), table) if fill_value is not None else 0,
    }
    if note is not None:
        out["note"] = note
    return out


def _standard(spelling: str) -> bool | None:
    lowered = spelling.lower()
    if lowered in TRUE_SPELLINGS:
        return True
    if lowered in FALSE_SPELLINGS:
        return False
    return None


def binary_code(value: str, table: Mapping[str, int]) -> int:
    """0 or 1 for one cell of a ``binary`` column, by the fitted table, then Ludwig's spellings."""
    text = value.strip()
    if text in table:
        return int(table[text])
    standard = _standard(text)
    return int(bool(standard))


# --- outputs -------------------------------------------------------------------------------------


def fit_output_category(
    train: Sequence[str], every: Sequence[str], *, pinned: Sequence[str] | None, path: str
) -> dict[str, Any]:
    """The label order of a ``category`` output: by frequency in the training part, or pinned.

    There is no "unknown": a class the training part does not show could not be learned, so it is
    refused (DS-14). A pinned list must name every class the data shows, and only those (DS-5).
    """
    seen = set(every)
    if pinned is not None:
        unlisted = sorted(seen - set(pinned))
        if unlisted:
            run_rule_error(
                RULE_DATASET_LABELS,
                f"{path}.preprocessing.vocab",
                (
                    f"the data contains {len(unlisted)} label(s) the manifest does not list: "
                    f"{', '.join(unlisted)}"
                ),
                found=unlisted,
                accepted=tuple(pinned),
            )
        unseen = sorted(set(pinned) - seen)
        if unseen:
            run_rule_error(
                RULE_DATASET_LABELS,
                f"{path}.preprocessing.vocab",
                (
                    f"the manifest lists {len(unseen)} label(s) the data never shows: "
                    f"{', '.join(unseen)}"
                ),
                found=sorted(seen),
                accepted=tuple(pinned),
            )
    if len(seen) < 2:
        run_rule_error(
            RULE_TOO_FEW_CLASSES,
            f"{path}.name",
            (
                f"the output column holds {len(seen)} distinct value(s), so there is nothing to "
                "classify; a category output needs at least two"
            ),
            found=sorted(seen),
        )
    _all_in_training(train, seen, path)
    labels = list(pinned) if pinned is not None else by_frequency(Counter(train))
    return {"labels": labels, "labels_source": "stated" if pinned is not None else "derived"}


def fit_output_binary(
    train: Sequence[str], every: Sequence[str], *, fallback_true_label: str | None, path: str
) -> dict[str, Any]:
    """Which spelling of a ``binary`` output is true; both classes must be in the training part."""
    fitted = fit_binary(every, fallback_true_label=fallback_true_label, path=path, fill_value=None)
    classes = {binary_code(value, fitted["spellings"]) for value in every}
    if len(classes) < 2:
        run_rule_error(
            RULE_TOO_FEW_CLASSES,
            f"{path}.name",
            "the binary output holds one class only, so there is nothing to decide",
            found=sorted(set(every)),
        )
    trained = {binary_code(value, fitted["spellings"]) for value in train}
    if trained != classes:
        absent = "true" if 1 not in trained else "false"
        run_rule_error(
            RULE_CLASS_OUTSIDE_TRAIN,
            f"{path}.name",
            (
                f"the class {absent} occurs in the data but not in the training part, so nothing "
                "could learn it"
            ),
            found=absent,
        )
    fitted.pop("missing", None)
    return fitted


def fit_output_number(train: Sequence[float], *, normalization: str | None) -> dict[str, Any]:
    """The shift and scale a ``number`` output is learned in, inverted inside the model."""
    shift, scale = _shift_and_scale([float(value) for value in train], normalization)
    return {"normalization": normalization, "shift": shift, "scale": scale}


def _all_in_training(train: Sequence[str], seen: set[str], path: str) -> None:
    absent = sorted(seen - set(train))
    if absent:
        run_rule_error(
            RULE_CLASS_OUTSIDE_TRAIN,
            f"{path}.name",
            (
                f"{len(absent)} class(es) occur in the data but not in the training part, so "
                f"nothing could learn them: {', '.join(absent)}"
            ),
            found=absent,
        )
