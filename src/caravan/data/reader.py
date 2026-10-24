"""Records to arrays. The only module in the project that parses a dataset.

Behind the ``train`` extra: it imports ``numpy``, so nothing in the core may import it. The core's
own ``fingerprint`` module identifies a dataset without parsing it, which is what lets the stage
cache work in an installation that has no training framework at all (research R4 of feature 002).

Feature 008: the columns are typed. A ``number`` column is read as float32, with ``nan`` where a
cell is empty — the feature's ``missing_value_strategy`` decides what fills it, after fitting. A
``category`` or ``binary`` column, the output and the split are read as the text of their cells and
kept as text until the fitted tables map them. A column no feature, output or split reads is
returned as ignored, visibly.

Two passes over each file, both in C: the header is read with the standard library so that the
column checks can name exact column names, and the values with ``numpy.loadtxt``. The slow, precise
Python scan runs only when something is wrong or a number column has an empty cell.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
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
from caravan.manifest.schema.preprocessing import FIXED_SPLIT_VALUES

_DELIMITERS = {".csv": ",", ".tsv": "\t", ".txt": ","}


def delimiter_for(path: Path) -> str:
    return _DELIMITERS.get(path.suffix.lower(), ",")


@dataclass(frozen=True)
class RecordSchema:
    """The header, once it has been read and agreed on by every file."""

    #: The input features' columns, in manifest order, and their types.
    feature_names: tuple[str, ...]
    feature_types: tuple[str, ...]
    record_count: int
    #: The output feature's column and type.
    label_name: str = "label"
    label_type: str = "category"
    #: Columns no feature, output or split reads — visible, so nothing is dropped silently.
    ignored_names: tuple[str, ...] = ()
    #: The column naming each record's part of a fixed split, or ``None`` (feature 007).
    split_name: str | None = None

    @property
    def feature_count(self) -> int:
        return len(self.feature_names)


@dataclass(frozen=True)
class RecordSet:
    """Every record of the dataset, in sequence order, column by column."""

    schema: RecordSchema
    #: Per input feature: float32 for ``number`` (``nan`` where empty), the cell text otherwise.
    columns: dict[str, np.ndarray]
    #: The output of each record, as the data spells it; a ``number`` in its canonical text.
    labels: tuple[str, ...]
    #: The part each record names (``train``, ``val`` or ``test``) for a fixed split; else ``None``.
    parts: tuple[str, ...] | None = None


def _read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter=delimiter_for(path)):
            return [cell.strip() for cell in row]
    run_rule_error(
        RULE_DATASET_COLUMNS,
        "dataset",
        f"{path.name} is empty: a data file must carry a header row and at least one record",
        found=path.name,
    )


@dataclass(frozen=True)
class _Columns:
    """Where in one file's header each feature, the output and the split are."""

    positions: tuple[int, ...]
    label_index: int
    ignored: tuple[str, ...]
    split_index: int | None = None


def _check_header(
    path: Path,
    header: list[str],
    features: Sequence[tuple[str, str]],
    output: str,
    split_column: str | None,
) -> _Columns:
    if header.count(output) != 1:
        run_rule_error(
            RULE_DATASET_COLUMNS,
            "output_features[0].name",
            (
                f"{path.name} must have exactly one column named {output!r}, which holds the "
                f"output; it has {header.count(output)}"
            ),
            found=header,
            accepted=(output,),
        )
    label_index = header.index(output)
    split_index: int | None = None
    if split_column is not None:
        if header.count(split_column) != 1:
            run_rule_error(
                RULE_SPLIT_VALUE,
                "preprocessing.split.column",
                (
                    f"{path.name} must have exactly one column named {split_column!r}, which says "
                    f"where each record belongs; it has {header.count(split_column)}"
                ),
                found=header,
                accepted=(split_column,),
            )
        split_index = header.index(split_column)
    positions: list[int] = []
    for index, (name, _) in enumerate(features):
        if header.count(name) != 1:
            if name in header:
                run_rule_error(
                    RULE_DATASET_COLUMNS,
                    f"input_features[{index}].name",
                    f"{path.name} has {header.count(name)} columns named {name!r}; a feature "
                    "reads exactly one",
                    found=header,
                )
            run_rule_error(
                RULE_UNKNOWN_INPUT_COLUMN,
                f"input_features[{index}].name",
                f"the feature names a column {path.name} does not have: {name}",
                found=name,
                accepted=tuple(column for column in header if column != output),
            )
        positions.append(header.index(name))
    read = {*positions, label_index, *(() if split_index is None else (split_index,))}
    ignored = tuple(name for position, name in enumerate(header) if position not in read)
    return _Columns(tuple(positions), label_index, ignored, split_index)


def _bad_cell(path: Path, number: int, column: str, cell: str) -> None:
    run_rule_error(
        RULE_DATASET_CELL,
        "dataset",
        f"{path.name}, record {number}, column {column!r}: {cell!r} is not a number",
        found=cell,
    )


def _scan_numbers(path: Path, header: list[str], positions: Sequence[int]) -> np.ndarray:
    """The careful read of a file's number columns: an empty cell is ``nan``, text is DS-4.

    Runs only when the fast reader refused the file, so its cost is paid on the path that has an
    empty cell or something worse — and it names the record and the column.
    """
    rows: list[list[float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter_for(path))
        next(reader, None)
        for number, row in enumerate(reader, start=1):
            if len(row) != len(header):
                _ragged(path, number, len(row), len(header), row)
            values: list[float] = []
            for position in positions:
                cell = row[position].strip()
                if cell == "":
                    values.append(float("nan"))
                    continue
                try:
                    values.append(float(cell))
                except ValueError:
                    _bad_cell(path, number, header[position], cell)
            rows.append(values)
    return np.array(rows, dtype=np.float32).reshape(len(rows), len(positions))


def _ragged(path: Path, number: int, found: int, declared: int, row: list[str]) -> None:
    run_rule_error(
        RULE_DATASET_CELL,
        "dataset",
        f"{path.name}, record {number}: {found} values where the header declares {declared} columns",
        found=row,
    )


def _check_field_counts(path: Path, header: list[str], records: int) -> None:
    """Prove every record has exactly as many fields as the header declares.

    ``numpy.loadtxt`` with ``usecols`` silently ignores the extras in a record with too many
    fields, so a stray column appended to one file would be dropped without a word. If the file
    holds exactly ``records * (columns - 1)`` delimiters outside its header, and no record was
    short (which ``loadtxt`` refuses), no record can be long either. Quoted fields containing the
    delimiter are not supported by this contract.
    """
    delimiter = delimiter_for(path).encode("utf-8")
    seen = 0
    with path.open("rb") as handle:
        handle.readline()
        while chunk := handle.read(1 << 20):
            seen += chunk.count(delimiter)
    if seen == records * (len(header) - 1):
        return
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter_for(path))
        next(reader, None)
        for number, row in enumerate(reader, start=1):
            if len(row) != len(header):
                _ragged(path, number, len(row), len(header), row)
    run_rule_error(  # pragma: no cover - only if the count and the scan disagree
        RULE_DATASET_CELL,
        "dataset",
        f"{path.name}: the delimiters do not add up, and a scan found no ragged record",
        found=path.name,
    )


def _read_text(path: Path, positions: Sequence[int]) -> np.ndarray:
    """The text of the given columns, shape (records, columns), stripped."""
    values = np.loadtxt(
        path,
        delimiter=delimiter_for(path),
        skiprows=1,
        usecols=tuple(positions),
        dtype=str,
        ndmin=2,
        comments=None,
    )
    return np.char.strip(values.reshape(-1, len(positions)))


def _read_numbers(path: Path, header: list[str], positions: Sequence[int]) -> np.ndarray:
    if not positions:
        return np.zeros((0, 0), dtype=np.float32)
    try:
        values = np.loadtxt(
            path,
            delimiter=delimiter_for(path),
            skiprows=1,
            usecols=tuple(positions),
            dtype=np.float32,
            ndmin=2,
        )
    except ValueError:
        return _scan_numbers(path, header, positions)
    return values.reshape(-1, len(positions))


def _parts(path: Path, values: np.ndarray, split_column: str) -> list[str]:
    """Each record's part, checked against the values a fixed split accepts (DS-13)."""
    out: list[str] = []
    for index, value in enumerate(values.tolist()):
        part = FIXED_SPLIT_VALUES.get(value)
        if part is None:
            run_rule_error(
                RULE_SPLIT_VALUE,
                "preprocessing.split.column",
                (
                    f"{path.name}, line {index + 2}: column {split_column!r} holds {value!r}; a "
                    f"fixed split accepts only {', '.join(FIXED_SPLIT_VALUES)}"
                ),
                found=value,
                accepted=tuple(FIXED_SPLIT_VALUES),
            )
        out.append(part)  # type: ignore[arg-type]
    return out


def _labels(path: Path, values: np.ndarray, output: str, kind: str) -> list[str]:
    """The output of each record; an empty cell has no answer to learn, so it is refused."""
    labels = values.tolist()
    for index, label in enumerate(labels):
        if label == "":
            run_rule_error(
                RULE_DATASET_CELL,
                "dataset",
                f"{path.name}, record {index + 1}, column {output!r}: the output is empty",
                found=label,
            )
    if kind != "number":
        return labels
    out: list[str] = []
    for index, label in enumerate(labels):
        try:
            out.append(repr(float(label)))
        except ValueError:
            _bad_cell(path, index + 1, output, label)
    return out


def read_records(
    dataset: DatasetFiles,
    *,
    features: Sequence[tuple[str, str]],
    output: tuple[str, str] = ("label", "category"),
    split_column: str | None = None,
) -> RecordSet:
    """Read every record of the dataset, in sequence order.

    Sequence order is file order, and across files the sorted relative-path order the fingerprint
    used — so the windows a run produces are the windows its dataset version identifies.
    """
    output_name, output_type = output
    numbers = [index for index, (_, kind) in enumerate(features) if kind == "number"]
    texts = [index for index, (_, kind) in enumerate(features) if kind != "number"]

    first: tuple[Path, list[str], _Columns] | None = None
    number_blocks: list[np.ndarray] = []
    text_blocks: list[np.ndarray] = []
    labels: list[str] = []
    parts: list[str] = []

    for path in dataset.files:
        header = _read_header(path)
        columns = _check_header(path, header, features, output_name, split_column)
        if first is None:
            first = (path, header, columns)
        elif header != first[1]:
            first_path, first_header, _ = first
            differing = next(
                (name for name, other in zip(header, first_header, strict=False) if name != other),
                None,
            )
            if differing is None:
                longer = header if len(header) > len(first_header) else first_header
                differing = longer[min(len(header), len(first_header))]
            run_rule_error(
                RULE_DATASET_HEADERS_DIFFER,
                "dataset",
                (
                    f"{path.name} and {first_path.name} disagree about their columns, first at "
                    f"{differing!r}; every file of one dataset must carry the same header, because "
                    "they are read as one sequence"
                ),
                found={path.name: header, first_path.name: first_header},
            )
        text_positions = [columns.positions[index] for index in texts]
        extra = [columns.label_index]
        if columns.split_index is not None:
            extra.append(columns.split_index)
        try:
            text = _read_text(path, [*text_positions, *extra])
        except ValueError:
            # loadtxt refuses a short record; the scan names it.
            _check_field_counts(path, header, -1)
            raise  # pragma: no cover - the check above always raises here
        _check_field_counts(path, header, text.shape[0])
        number_blocks.append(_read_numbers(path, header, [columns.positions[i] for i in numbers]))
        text_blocks.append(text)
        labels.extend(_labels(path, text[:, len(texts)], output_name, output_type))
        if columns.split_index is not None and split_column is not None:
            parts.extend(_parts(path, text[:, len(texts) + 1], split_column))

    assert first is not None  # resolve_dataset guarantees at least one file
    number_all = np.concatenate(number_blocks, axis=0) if numbers else None
    text_all = np.concatenate(text_blocks, axis=0)
    out: dict[str, np.ndarray] = {}
    for slot, index in enumerate(numbers):
        out[features[index][0]] = np.ascontiguousarray(number_all[:, slot])  # type: ignore[index]
    for slot, index in enumerate(texts):
        out[features[index][0]] = text_all[:, slot]

    return RecordSet(
        schema=RecordSchema(
            feature_names=tuple(name for name, _ in features),
            feature_types=tuple(kind for _, kind in features),
            record_count=len(labels),
            label_name=output_name,
            label_type=output_type,
            ignored_names=first[2].ignored,
            split_name=split_column,
        ),
        columns={name: out[name] for name, _ in features},
        labels=tuple(labels),
        parts=tuple(parts) if split_column is not None else None,
    )
