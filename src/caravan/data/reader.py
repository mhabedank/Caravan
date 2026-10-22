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
    RULE_DATASET_LABELS,
    run_rule_error,
)

LABEL_COLUMN = "label"

_DELIMITERS = {".csv": ",", ".tsv": "\t", ".txt": ","}


def delimiter_for(path: Path) -> str:
    return _DELIMITERS.get(path.suffix.lower(), ",")


@dataclass(frozen=True)
class RecordSchema:
    """The header, once it has been read and agreed on by every file."""

    feature_names: tuple[str, ...]
    label_column: int
    record_count: int

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


def _check_header(path: Path, header: list[str]) -> tuple[tuple[str, ...], int]:
    if header.count(LABEL_COLUMN) != 1:
        run_rule_error(
            RULE_DATASET_COLUMNS,
            "dataset.source",
            (
                f"{path.name} must have exactly one column named {LABEL_COLUMN!r}, which holds "
                f"the class name; it has {header.count(LABEL_COLUMN)}"
            ),
            found=header,
            accepted=(LABEL_COLUMN,),
        )
    index = header.index(LABEL_COLUMN)
    features = tuple(name for position, name in enumerate(header) if position != index)
    if not features:
        run_rule_error(
            RULE_DATASET_COLUMNS,
            "dataset.source",
            f"{path.name} has no feature column: every column but {LABEL_COLUMN!r} is a feature",
            found=header,
        )
    return features, index


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


def read_records(dataset: DatasetFiles, declared_labels: tuple[str, ...]) -> RecordSet:
    """Read every record of the dataset, in sequence order, and check it against the manifest.

    Sequence order is file order, and across files the sorted relative-path order the fingerprint
    used — so the windows a run produces are the windows its dataset version identifies.
    """
    schema: tuple[tuple[str, ...], int] | None = None
    first_path: Path | None = None
    blocks: list[np.ndarray] = []
    labels: list[str] = []

    for path in dataset.files:
        header = _read_header(path)
        features, index = _check_header(path, header)
        if schema is None:
            schema, first_path = (features, index), path
        elif (features, index) != schema:
            differing = next(
                (
                    name
                    for name, other in zip(header, [*schema[0][: schema[1]]], strict=False)
                    if name != other
                ),
                header[0],
            )
            run_rule_error(
                RULE_DATASET_HEADERS_DIFFER,
                "dataset.source",
                (
                    f"{path.name} and {first_path.name if first_path else '?'} disagree about "
                    f"their columns, first at {differing!r}; every file of one dataset must carry "
                    "the same header, because they are read as one sequence"
                ),
                found={
                    path.name: header,
                    (first_path.name if first_path else "?"): [
                        *schema[0][: schema[1]],
                        LABEL_COLUMN,
                        *schema[0][schema[1] :],
                    ],
                },
            )
        feature_columns = tuple(position for position in range(len(header)) if position != index)
        block, block_labels = _read_values(path, feature_columns, index)
        _check_field_counts(path, len(header), len(block_labels), feature_columns)
        blocks.append(block)
        labels.extend(block_labels)

    assert schema is not None  # resolve_dataset guarantees at least one file
    feature_names, label_index = schema
    features_array = np.concatenate(blocks, axis=0) if len(blocks) > 1 else blocks[0]

    _check_labels(labels, declared_labels)

    return RecordSet(
        schema=RecordSchema(
            feature_names=feature_names,
            label_column=label_index,
            record_count=len(labels),
        ),
        features=features_array,
        labels=tuple(labels),
    )


def _check_labels(labels: list[str], declared: tuple[str, ...]) -> None:
    """Both directions, because both are a disagreement (DS-5).

    A label in the data the manifest does not declare means the model has no output for it. A
    declared label the data never shows means the model is asked to predict something it will
    never see an example of — which is not a curiosity, it is a split that cannot be stratified
    and a recall that cannot be computed.
    """
    seen = set(labels)
    declared_set = set(declared)
    undeclared = sorted(seen - declared_set)
    unseen = sorted(declared_set - seen)
    if undeclared:
        run_rule_error(
            RULE_DATASET_LABELS,
            "dataset.labels",
            (
                f"the data contains {len(undeclared)} label(s) the manifest does not declare: "
                f"{', '.join(undeclared)}"
            ),
            found=undeclared,
            accepted=tuple(declared),
        )
    if unseen:
        run_rule_error(
            RULE_DATASET_LABELS,
            "dataset.labels",
            (
                f"the manifest declares {len(unseen)} label(s) the data never shows: "
                f"{', '.join(unseen)}"
            ),
            found=sorted(seen),
            accepted=tuple(declared),
        )
