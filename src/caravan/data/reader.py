"""Records to arrays. The only module in the project that parses a dataset.

Behind the ``train`` extra: it imports ``numpy``, so nothing in the core may import it. The core's
own ``fingerprint`` module identifies a dataset without parsing it, which is what lets the stage
cache work in an installation that has no training framework at all (research R4).

Two passes over each file, both in C: the header is read with the standard library so that the
column checks can name exact column names, and the values are read with ``numpy.loadtxt``, which
since numpy 1.23 is a C reader fast enough for the author's real dataset. The slow, precise Python
scan runs only when something is wrong — a bad cell has to be named exactly, and that is worth a
second read of the one file that has it.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from caravan.data.fingerprint import DatasetFiles
from caravan.manifest.errors import (
    RULE_DATASET_CELL,
    RULE_DATASET_COLUMNS,
    RULE_DATASET_HEADERS_DIFFER,
    RULE_SPLIT_VALUE,
    RULE_UNKNOWN_INPUT_COLUMN,
    run_rule_error,
)
from caravan.manifest.schema.dataset import PART_NAMES
from caravan.manifest.schema.io import DEFAULT_OUTPUT_COLUMN

_DELIMITERS = {".csv": ",", ".tsv": "\t", ".txt": ","}


def delimiter_for(path: Path) -> str:
    return _DELIMITERS.get(path.suffix.lower(), ",")


@dataclass(frozen=True)
class RecordSchema:
    """The header, once it has been read and agreed on by every file."""

    #: The input's columns, in the order they go into the tensor.
    feature_names: tuple[str, ...]
    label_column: int
    record_count: int
    #: The output's column.
    label_name: str = DEFAULT_OUTPUT_COLUMN
    #: Columns neither the input nor the output reads — visible, so a column a stated list left
    #: out is never dropped silently.
    ignored_names: tuple[str, ...] = ()
    #: The column naming each record's part of a fixed split, or ``None`` (feature 007).
    split_name: str | None = None

    @property
    def feature_count(self) -> int:
        return len(self.feature_names)


@dataclass(frozen=True)
class RecordSet:
    """Every record of the dataset, in sequence order, as the model will see them."""

    schema: RecordSchema
    #: Shape ``(records, features)``, float32 — what the framework wants, without a later copy.
    features: np.ndarray
    #: The label of each record, parallel to ``features``.
    labels: tuple[str, ...]
    #: The part each record names, parallel to ``labels``, for a fixed split; else ``None``.
    parts: tuple[str, ...] | None = None


def _read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter=delimiter_for(path)):
            return [cell.strip() for cell in row]
    run_rule_error(
        RULE_DATASET_COLUMNS,
        "dataset.source",
        f"{path.name} is empty: a data file must carry a header row and at least one record",
        found=path.name,
    )


@dataclass(frozen=True)
class _Columns:
    """Where in one file's header the input and the output are."""

    feature_names: tuple[str, ...]
    feature_positions: tuple[int, ...]
    label_index: int
    ignored: tuple[str, ...]
    split_index: int | None = None


def _check_header(
    path: Path,
    header: list[str],
    input_columns: tuple[str, ...] | None,
    output_column: str,
    split_column: str | None = None,
) -> _Columns:
    if header.count(output_column) != 1:
        run_rule_error(
            RULE_DATASET_COLUMNS,
            "dataset.source",
            (
                f"{path.name} must have exactly one column named {output_column!r}, which holds "
                f"the class name (outputs[0].column); it has {header.count(output_column)}"
            ),
            found=header,
            accepted=(output_column,),
        )
    label_index = header.index(output_column)
    split_index: int | None = None
    if split_column is not None:
        if header.count(split_column) != 1:
            run_rule_error(
                RULE_SPLIT_VALUE,
                "dataset.split.column",
                (
                    f"{path.name} must have exactly one column named {split_column!r}, which says "
                    f"where each record belongs; it has {header.count(split_column)}"
                ),
                found=header,
                accepted=(split_column,),
            )
        split_index = header.index(split_column)
    if input_columns is None:
        names = tuple(
            name
            for position, name in enumerate(header)
            if position != label_index and position != split_index
        )
        if not names:
            run_rule_error(
                RULE_DATASET_COLUMNS,
                "dataset.source",
                f"{path.name} has no feature column: every column but {output_column!r} is a "
                "feature",
                found=header,
            )
    else:
        missing = [name for name in input_columns if name not in header]
        if missing:
            run_rule_error(
                RULE_UNKNOWN_INPUT_COLUMN,
                "inputs[0].columns",
                (
                    f"the input names {len(missing)} column(s) {path.name} does not have: "
                    f"{', '.join(missing)}"
                ),
                found=missing,
                accepted=tuple(name for name in header if name != output_column),
            )
        names = tuple(input_columns)
    positions = tuple(header.index(name) for name in names)
    read = {*positions, label_index, *(() if split_index is None else (split_index,))}
    ignored = tuple(name for position, name in enumerate(header) if position not in read)
    return _Columns(names, positions, label_index, ignored, split_index)


def _diagnose_bad_cell(path: Path, feature_columns: tuple[int, ...]) -> None:
    """Find the exact cell that is not a number, and refuse naming it.

    The fast reader knows only that a file did not parse. DS-4 promises the file, the record and
    the column, so when something is wrong this walks the one file in Python to say precisely
    where — the cost of a second read is paid only on the path that is already failing.
    """
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter_for(path))
        header = [cell.strip() for cell in next(reader, [])]
        for number, row in enumerate(reader, start=1):
            if len(row) != len(header):
                run_rule_error(
                    RULE_DATASET_CELL,
                    "dataset.source",
                    (
                        f"{path.name}, record {number}: {len(row)} values where the header "
                        f"declares {len(header)} columns"
                    ),
                    found=row,
                )
            for column in feature_columns:
                cell = row[column].strip()
                try:
                    float(cell)
                except ValueError:
                    run_rule_error(
                        RULE_DATASET_CELL,
                        "dataset.source",
                        (
                            f"{path.name}, record {number}, column {header[column]!r}: "
                            + ("the value is empty" if cell == "" else f"{cell!r} is not a number")
                            + "; there is no missing-value policy, because inventing one "
                            "silently is worse than refusing"
                        ),
                        found=cell,
                    )
    run_rule_error(  # pragma: no cover - only if numpy and the scan disagree
        RULE_DATASET_CELL,
        "dataset.source",
        f"{path.name} could not be read as numbers, and a scan found no single bad cell",
        found=path.name,
    )


def _check_field_counts(
    path: Path, columns: int, records: int, feature_columns: tuple[int, ...]
) -> None:
    """Prove every record has exactly as many fields as the header declares.

    ``numpy.loadtxt`` with ``usecols`` raises for a record with too *few* fields and silently
    ignores the extras in a record with too many — so a stray column appended to one file would
    be dropped without a word. That is precisely the silence this project does not do.

    The check is exact and costs one pass of byte counting at C speed rather than a Python loop
    over every record: if the file holds exactly ``records * (columns - 1)`` delimiters outside
    its header, and no record was short (which ``loadtxt`` would have refused), then no record can
    be long either. Quoted fields containing the delimiter are not supported by this contract, and
    would show up here as a mismatch rather than as a wrong number.
    """
    delimiter = delimiter_for(path).encode("utf-8")
    seen = 0
    with path.open("rb") as handle:
        handle.readline()  # the header's own delimiters are not part of the count
        while chunk := handle.read(1 << 20):
            seen += chunk.count(delimiter)
    if seen != records * (columns - 1):
        # Something is ragged. The scan names the record; it checks the same feature columns the
        # fast reader did, so it cannot invent a complaint about the label column.
        _diagnose_bad_cell(path, feature_columns)


def _read_values(path: Path, feature_columns: tuple[int, ...], label_column: int):
    delimiter = delimiter_for(path)
    try:
        features = np.loadtxt(
            path,
            delimiter=delimiter,
            skiprows=1,
            usecols=feature_columns,
            dtype=np.float32,
            ndmin=2,
        )
    except ValueError:
        _diagnose_bad_cell(path, feature_columns)
        raise  # pragma: no cover - the diagnosis above always raises
    labels = np.loadtxt(
        path,
        delimiter=delimiter,
        skiprows=1,
        usecols=(label_column,),
        dtype=str,
        ndmin=1,
    )
    return features, [str(value) for value in labels]


def _read_parts(path: Path, split_index: int, split_column: str) -> list[str]:
    """Each record's part, checked to be one of the three names (DS-13, feature 007)."""
    values = np.loadtxt(
        path,
        delimiter=delimiter_for(path),
        skiprows=1,
        usecols=(split_index,),
        dtype=str,
        ndmin=1,
    )
    parts = [str(value) for value in values]
    for index, part in enumerate(parts):
        if part not in PART_NAMES:
            run_rule_error(
                RULE_SPLIT_VALUE,
                "dataset.split.column",
                (
                    f"{path.name}, line {index + 2}: column {split_column!r} holds {part!r}; a "
                    f"fixed split accepts only {', '.join(PART_NAMES)}"
                ),
                found=part,
                accepted=PART_NAMES,
            )
    return parts


def read_records(
    dataset: DatasetFiles,
    *,
    input_columns: tuple[str, ...] | None = None,
    output_column: str = DEFAULT_OUTPUT_COLUMN,
    split_column: str | None = None,
) -> RecordSet:
    """Read every record of the dataset, in sequence order.

    ``input_columns`` is what the input declares, or ``None`` for every column but the output's,
    in file order. The labels are returned as the data spells them; whether they agree with a
    pinned list is the ``data`` stage's question, not the reader's (feature 006). With
    ``split_column``, each record's part is read too, and that column is never an input
    (feature 007).

    Sequence order is file order, and across files the sorted relative-path order the fingerprint
    used — so the windows a run produces are the windows its dataset version identifies.
    """
    first: tuple[Path, list[str], _Columns] | None = None
    blocks: list[np.ndarray] = []
    labels: list[str] = []
    parts: list[str] = []

    for path in dataset.files:
        header = _read_header(path)
        columns = _check_header(path, header, input_columns, output_column, split_column)
        if first is None:
            first = (path, header, columns)
        elif header != first[1]:
            first_path, first_header, _ = first
            differing = next(
                (name for name, other in zip(header, first_header, strict=False) if name != other),
                None,
            )
            if differing is None:
                # One header is the other plus columns: the first extra column is the difference.
                longer = header if len(header) > len(first_header) else first_header
                differing = longer[min(len(header), len(first_header))]
            run_rule_error(
                RULE_DATASET_HEADERS_DIFFER,
                "dataset.source",
                (
                    f"{path.name} and {first_path.name} disagree about their columns, first at "
                    f"{differing!r}; every file of one dataset must carry the same header, because "
                    "they are read as one sequence"
                ),
                found={path.name: header, first_path.name: first_header},
            )
        block, block_labels = _read_values(path, columns.feature_positions, columns.label_index)
        _check_field_counts(path, len(header), len(block_labels), columns.feature_positions)
        blocks.append(block)
        labels.extend(block_labels)
        if columns.split_index is not None and split_column is not None:
            parts.extend(_read_parts(path, columns.split_index, split_column))

    assert first is not None  # resolve_dataset guarantees at least one file
    columns = first[2]
    features_array = np.concatenate(blocks, axis=0) if len(blocks) > 1 else blocks[0]

    return RecordSet(
        schema=RecordSchema(
            feature_names=columns.feature_names,
            label_column=columns.label_index,
            record_count=len(labels),
            label_name=output_column,
            ignored_names=columns.ignored,
            split_name=split_column,
        ),
        features=features_array,
        labels=tuple(labels),
        parts=tuple(parts) if split_column is not None else None,
    )
