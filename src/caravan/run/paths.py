"""The run directory: one per invocation, never overwritten.

Each run gets ``runs/<UTC timestamp>-<first 8 hex of the manifest digest>/``. The timestamp
orders runs, the digest distinguishes runs of different manifests without opening them, and a
collision fails the run rather than overwriting an artifact.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

RUN_DIR_PATTERN = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")

REPORT_NAME = "report.json"
RESOLVED_MANIFEST_NAME = "resolved-manifest.yaml"


class RunDirectoryError(Exception):
    """The run directory could not be created, or the requested parent is not usable."""


def file_digest(path: Path) -> str:
    """The SHA-256 of a file's exact bytes, for provenance and for the directory name."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_runs_dir(runs_dir: Path) -> None:
    """Refuse a runs directory that points inside an existing run directory.

    Nesting runs inside runs would make one invocation write into another's artifacts, which is
    exactly what the never-overwrite rule exists to prevent.
    """
    candidates = [runs_dir, *runs_dir.parents]
    for candidate in candidates[:3]:
        if RUN_DIR_PATTERN.match(candidate.name) or (candidate / REPORT_NAME).is_file():
            raise RunDirectoryError(
                f"{runs_dir} is inside an existing run directory ({candidate}); "
                "choose a directory that holds run directories, not one of them"
            )


def run_directory_name(digest: str, now: datetime | None = None) -> str:
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    return f"{moment.strftime('%Y%m%dT%H%M%SZ')}-{digest[:8]}"


def create_run_directory(runs_dir: Path, digest: str, now: datetime | None = None) -> Path:
    """Create a fresh run directory and return it. An existing one is an error, not a reuse."""
    check_runs_dir(runs_dir)
    run_dir = runs_dir / run_directory_name(digest, now)
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise RunDirectoryError(
            f"{run_dir} already exists; a run never overwrites an artifact of another run"
        ) from exc
    except OSError as exc:
        raise RunDirectoryError(f"{run_dir} could not be created: {exc.strerror}") from exc
    return run_dir
