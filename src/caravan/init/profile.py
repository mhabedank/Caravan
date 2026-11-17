"""What the data says about each column: a proposed type and the reason (feature 013, R3 to R5).

Read with the standard library's ``csv``, so it runs without a framework. A bounded sample of
50,000 rows is enough for every rule below and keeps a million-row dataset under a second (SC-005).
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from caravan.data.fingerprint import TABLE_DELIMITERS, data_files
from caravan.manifest.schema.features import NAME_PATTERN

#: Rows read for the proposals (research R3).
SAMPLE_ROWS = 50_000
#: Distinct values kept per column; every threshold below is under it.
DISTINCT_CAP = 257
#: At most this many distinct integers make a category rather than a number (R4 rule 7).
SMALL_CODES = 16
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".pgm")
#: Output names, in order of preference (R5).
OUTPUT_NAMES = ("label", "target", "class", "y", "condition", "outcome")
#: The value of an anomaly column that means normal unless stated (the schema's default).
NORMAL = "normal"


class ProfileError(Exception):
    """The data cannot be set up: a missing path, no header, headers that differ."""


@dataclass
class ColumnProfile:
    """One column as the sample shows it, with the type proposed and why."""

    name: str
    rows_seen: int = 0
    empty: int = 0
    numeric: bool = True
    integer: bool = True
    distinct: list[str] = field(default_factory=list)
    distinct_capped: bool = False
    #: ``number``, ``category``, ``binary``, or ``None`` for "leave out".
    proposal: str | None = None
    reason: str = ""
    image_like: bool = False

    @property
    def values(self) -> int:
        return len(self.distinct)

    def summary(self) -> str:
        """The distinct values in a few words: ``4 values: dos, fuzzy, normal, replay``."""
        shown = ", ".join(self.distinct[:6])
        more = "…" if len(self.distinct) > 6 or self.distinct_capped else ""
        count = f"{self.values}{'+' if self.distinct_capped else ''}"
        return f"{count} values: {shown}{more}"


@dataclass
class DataProfile:
    root: Path
    files: tuple[Path, ...]
    columns: tuple[ColumnProfile, ...]
    rows_read: int
    complete: bool

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    def column(self, name: str) -> ColumnProfile:
        return next(column for column in self.columns if column.name == name)

    def sample_note(self) -> str:
        if self.complete:
            return f"read all {self.rows_read:,} rows"
        return f"sampled the first {self.rows_read:,} rows"


def _number(cell: str) -> tuple[bool, bool]:
    """Whether a cell is a number, and whether it is an integer."""
    try:
        int(cell)
        return True, True
    except ValueError:
        pass
    try:
        float(cell)
        return True, False
    except ValueError:
        return False, False


def _header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=TABLE_DELIMITERS.get(path.suffix.lower(), ","))
        return [cell.strip() for cell in next(reader, [])]


def read_header(root: Path, files: Sequence[Path]) -> list[str]:
    """The one header every file shares, or a ``ProfileError`` naming what differs."""
    headers = {path: _header(path) for path in files}
    first = headers[files[0]]
    if not first:
        raise ProfileError(f"{files[0]} is empty: a data file starts with a header row")
    if all(_number(cell)[0] for cell in first if cell):
        raise ProfileError(
            f"{files[0].relative_to(root)} has no header row: its first row is numbers "
            f"({', '.join(first[:4])}…); add a row naming the columns"
        )
    for path, header in headers.items():
        if header != first:
            missing = [name for name in first if name not in header]
            extra = [name for name in header if name not in first]
            detail = "; ".join(
                part
                for part in (
                    f"lacks {', '.join(missing)}" if missing else "",
                    f"adds {', '.join(extra)}" if extra else "",
                    "orders the columns differently" if not missing and not extra else "",
                )
                if part
            )
            raise ProfileError(
                f"the files have different headers: {path.relative_to(root)} {detail} "
                f"compared with {files[0].relative_to(root)}; every file of a dataset has the "
                "same columns"
            )
    return first


def _propose(column: ColumnProfile) -> None:
    """Research R4: the first matching rule gives the proposal and the reason shown."""
    name = column.name
    if column.rows_seen == column.empty:
        column.proposal, column.reason = None, "every sampled cell is empty"
    elif column.values == 1 and not column.distinct_capped:
        column.proposal = None
        column.reason = "one value in every sampled row: carries no information"
    elif column.distinct and all(
        value.lower().endswith(IMAGE_SUFFIXES) for value in column.distinct[:20]
    ):
        column.proposal, column.image_like = None, True
        column.reason = "file names of images: image inputs are not set up by init yet"
    elif column.values == 2 and not column.distinct_capped:
        first, second = column.distinct
        column.proposal, column.reason = "binary", f"2 distinct values: {first} and {second}"
    elif (
        column.numeric
        and column.integer
        and (name == "id" or name.endswith("_id") or name == "code" or name.endswith("code"))
    ):
        column.proposal = "category"
        column.reason = "integers in a column named like an identifier: a code, not a magnitude"
    elif not column.numeric:
        count = f"{column.values}{'+' if column.distinct_capped else ''}"
        column.proposal, column.reason = "category", f"text values, {count} distinct"
    elif column.integer and column.values <= SMALL_CODES and not column.distinct_capped:
        column.proposal, column.reason = "category", f"{column.values} distinct integer values"
    else:
        count = f"{column.values}{'+' if column.distinct_capped else ''}"
        column.proposal, column.reason = "number", f"numeric, {count} distinct values"
    if column.proposal is not None and not NAME_PATTERN.match(name):
        column.proposal = None
        column.reason = (
            f"the name {name!r} cannot name a feature (lower case letters, digits and _, "
            "starting with a letter): rename the column to use it"
        )


def profile(path: Path, *, sample_rows: int = SAMPLE_ROWS) -> DataProfile:
    """Profile the data at ``path``: a directory of tables, or one table."""
    try:
        root, files = data_files(path.resolve())
    except Exception as exc:  # RunRuleFailure: the dataset rule's own message
        finding = getattr(exc, "finding", None)
        raise ProfileError(finding.problem if finding is not None else str(exc)) from exc
    names = read_header(root, files)
    columns = [ColumnProfile(name) for name in names]
    seen: list[set[str]] = [set() for _ in names]
    rows = 0
    complete = True
    for table in files:
        if rows >= sample_rows:
            complete = False
            break
        with table.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, delimiter=TABLE_DELIMITERS.get(table.suffix.lower(), ","))
            next(reader, None)
            for row in reader:
                if not row:
                    continue
                if rows >= sample_rows:
                    complete = False
                    break
                rows += 1
                for position, column in enumerate(columns):
                    cell = row[position].strip() if position < len(row) else ""
                    column.rows_seen += 1
                    if not cell:
                        column.empty += 1
                        continue
                    if column.numeric:
                        numeric, integer = _number(cell)
                        column.numeric = numeric
                        column.integer = column.integer and integer
                    if not column.distinct_capped and cell not in seen[position]:
                        if len(column.distinct) >= DISTINCT_CAP:
                            column.distinct_capped = True
                        else:
                            seen[position].add(cell)
                            column.distinct.append(cell)
    for column in columns:
        if column.empty == column.rows_seen:
            column.numeric = column.integer = False
        _propose(column)
    return DataProfile(root, files, tuple(columns), rows, complete)


# --- the output (research R5) ------------------------------------------------------------------


def proposed_output(data: DataProfile) -> str | None:
    usable = [column for column in data.columns if NAME_PATTERN.match(column.name)]
    for name in OUTPUT_NAMES:
        if any(column.name == name for column in usable):
            return name
    for column in reversed(usable):
        if column.proposal in ("category", "binary"):
            return column.name
    return None


def output_types(column: ColumnProfile) -> tuple[str, ...]:
    """The output types this column's values allow, the proposal first."""
    if column.values < 2:
        return ()
    if not column.numeric:
        if column.values == 2 and not column.distinct_capped:
            return ("binary", "category", "anomaly")
        return ("category", "anomaly")
    offered = ["number"]
    if column.integer and column.values == 2 and not column.distinct_capped:
        offered.append("binary")
    if column.integer and column.values <= SMALL_CODES and not column.distinct_capped:
        offered.append("category")
    return tuple(offered)


def read_column(data: DataProfile, name: str) -> tuple[list[str], list[tuple[str, int]]]:
    """Every value of one column, and each file with its row count, in reading order.

    The whole column rather than the sample: the window table counts windows the data stage would
    form, so it reads what the data stage reads (research R12).
    """
    values: list[str] = []
    files: list[tuple[str, int]] = []
    position = data.names.index(name)
    for table in data.files:
        before = len(values)
        with table.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, delimiter=TABLE_DELIMITERS.get(table.suffix.lower(), ","))
            next(reader, None)
            for row in reader:
                if not row:
                    continue
                values.append(row[position].strip() if position < len(row) else "")
        files.append((str(table.relative_to(data.root)), len(values) - before))
    return values, files
