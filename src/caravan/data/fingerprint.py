"""What a dataset reference resolves to, and what identifies it.

Standard library only, on purpose. The stage cache compares dataset versions on every run, and it
must do that without a training framework installed (research R4) — so this module parses nothing
and imports nothing but the standard library.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from caravan.manifest.errors import RULE_DATASET_UNREADABLE, run_rule_error

#: Files a dataset directory is read from, in sorted relative-path order.
DATA_SUFFIXES = (".csv", ".tsv", ".txt")

#: How much of a file is hashed at a time. Large enough to be fast, small enough that a multi-
#: gigabyte dataset never has to fit in memory.
_CHUNK = 1 << 20


@dataclass(frozen=True)
class DatasetFiles:
    """A resolved dataset reference: which files, in which order, and what they hash to."""

    root: Path
    files: tuple[Path, ...]
    version: str
    total_bytes: int

    @property
    def relative_names(self) -> tuple[str, ...]:
        return tuple(str(path.relative_to(self.root)) for path in self.files)


def _holds_data(directory: Path) -> bool:
    """Whether a subdirectory contains data at any depth."""
    try:
        return any(
            path.is_file() and path.suffix.lower() in DATA_SUFFIXES for path in directory.rglob("*")
        )
    except OSError:
        # Unreadable: treat it as holding data, so the refusal below asks the author rather than
        # this function guessing.
        return True


def _files_in(root: Path) -> tuple[Path, ...]:
    """The data files of a directory, in sorted relative-path order.

    A subdirectory that holds data is refused rather than searched: a nested layout read partially
    is a silently different dataset, and silence is the one thing this project does not do. A
    subdirectory that holds no data is ignored, because refusing a dataset over a ``__pycache__``
    or a ``.git`` beside it would be a rule about housekeeping rather than about data.
    """
    children = sorted(root.iterdir())
    nested = [child.name for child in children if child.is_dir() and _holds_data(child)]
    if nested:
        run_rule_error(
            RULE_DATASET_UNREADABLE,
            "dataset",
            (
                f"{root} has subdirectories that contain data, which are not read: point the "
                "reference at a directory whose own files are the data, or at a single file"
            ),
            found=nested,
        )
    return tuple(
        child for child in children if child.is_file() and child.suffix.lower() in DATA_SUFFIXES
    )


def resolve_dataset(source: str, manifest_dir: Path) -> DatasetFiles:
    """Resolve ``dataset`` against the manifest's own directory, and fingerprint it.

    The reference is relative to the manifest, so a manifest and its data move together. Every
    failure here is DS-1 and names the path and which of the three things went wrong, because
    "could not read the dataset" without saying why is the message FR-010 exists to prevent.
    """
    root = (manifest_dir / source).resolve() if not Path(source).is_absolute() else Path(source)

    if not root.exists():
        run_rule_error(
            RULE_DATASET_UNREADABLE,
            "dataset",
            f"no such path: {root}",
            found=source,
        )

    if root.is_dir():
        files = _files_in(root)
        if not files:
            run_rule_error(
                RULE_DATASET_UNREADABLE,
                "dataset",
                (
                    f"{root} holds no data file; a dataset directory must contain at least one "
                    f"file ending in {', '.join(DATA_SUFFIXES)}"
                ),
                found=source,
            )
    else:
        files = (root,)
        root = root.parent

    digest = hashlib.sha256()
    total = 0
    for path in files:
        try:
            size = path.stat().st_size
            with path.open("rb") as handle:
                digest.update(str(path.relative_to(root)).encode("utf-8"))
                digest.update(str(size).encode("ascii"))
                while chunk := handle.read(_CHUNK):
                    digest.update(chunk)
        except OSError as error:
            run_rule_error(
                RULE_DATASET_UNREADABLE,
                "dataset",
                f"cannot read {path}: {error.strerror or error}",
                found=source,
            )
        total += size

    return DatasetFiles(
        root=root,
        files=files,
        version=f"sha256:{digest.hexdigest()}",
        total_bytes=total,
    )
