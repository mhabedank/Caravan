"""The run directory: one per invocation, never overwritten.

Each run gets ``runs/<UTC timestamp>-<first 8 hex of the manifest digest>/``. The timestamp orders
runs, and the digest distinguishes runs of different manifests without opening them.

Two runs of the *same* manifest inside one second would collide, and a second run of a manifest is
an ordinary thing to do — feature 002's stage cache makes a fully reused run take under a third of
a second, so back-to-back runs land in the same second routinely. The invariant is that a run never
overwrites another's artifacts; failing the second run was never the point. So a collision takes
the next free ``-2``, ``-3`` and so on, and the common case keeps the name it always had.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

#: The trailing group is the same-second disambiguator described above, absent for the first run
#: of a manifest in any given second.
RUN_DIR_PATTERN = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}(-\d+)?$")

#: How many runs of one manifest may start inside the same second before this is treated as a
#: loop that has gone wrong rather than a person running a command twice.
MAX_RUNS_PER_SECOND = 100

REPORT_NAME = "report.json"
RESOLVED_MANIFEST_NAME = "resolved-manifest.yaml"
#: What the training framework, the converter and their libraries printed while stages ran
#: (feature 007). Kept rather than discarded, so a failure inside the framework keeps its cause.
FRAMEWORK_LOG_NAME = "framework.log"


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
    """Create a fresh run directory and return it. An existing one is never reused.

    ``mkdir`` without ``exist_ok`` is what makes this safe rather than a check followed by a
    create: the directory is claimed atomically, so two processes starting in the same second
    cannot both believe they own it.
    """
    check_runs_dir(runs_dir)
    base = runs_dir / run_directory_name(digest, now)
    for attempt in range(1, MAX_RUNS_PER_SECOND + 1):
        candidate = base if attempt == 1 else base.with_name(f"{base.name}-{attempt}")
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            continue
        except OSError as exc:
            raise RunDirectoryError(f"{candidate} could not be created: {exc.strerror}") from exc
    raise RunDirectoryError(
        f"{MAX_RUNS_PER_SECOND} runs of the same manifest already started in the second "
        f"{base.name} names; this looks like a loop rather than a run"
    )
