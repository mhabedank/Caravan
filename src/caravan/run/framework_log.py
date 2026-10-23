"""Keep the training framework's output off the console and in the run directory.

Measured before feature 007: an export printed a Keras listing of every captured variable to
standard output, which also broke ``--json``, and dozens of lines of TensorFlow's C++ logging to
standard error. The C++ part is written straight to file descriptor 2, so redirecting Python's
``sys.stdout`` and ``sys.stderr`` does not reach it. This redirects the descriptors themselves
(research R1), and swaps ``sys.stdout`` and ``sys.stderr`` for the same file, so that Python-level
writes land there too even where those objects no longer wrap the descriptors (a test harness, an
embedding application). Caravan prints nothing while stages run, so nothing of its own is captured.

Standard library only: this module is part of the core and imports no framework.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

STREAMS = (1, 2)


@contextmanager
def captured(path: Path | None) -> Iterator[None]:
    """Send everything written to descriptors 1 and 2 to ``path`` until the block ends.

    ``None`` redirects nothing (``--framework-output``). The descriptors are restored before any
    exception leaves the block, so the failure is reported on the console. An empty file is
    removed, because a log that says nothing is not worth a line in the run directory.
    """
    if path is None:
        yield
        return

    sys.stdout.flush()
    sys.stderr.flush()
    saved = {fd: os.dup(fd) for fd in STREAMS}
    saved_streams = (sys.stdout, sys.stderr)
    try:
        with path.open("a", encoding="utf-8", errors="replace", buffering=1) as log:
            log.flush()
            for fd in STREAMS:
                os.dup2(log.fileno(), fd)
            sys.stdout = sys.stderr = log
            try:
                yield
            finally:
                log.flush()
                sys.stdout, sys.stderr = saved_streams
                for fd, copy in saved.items():
                    os.dup2(copy, fd)
    finally:
        for copy in saved.values():
            os.close(copy)
        if path.exists() and path.stat().st_size == 0:
            path.unlink()


def mentioned(path: Path | None) -> str | None:
    """The console line pointing at the log, or ``None`` when there is nothing to point at."""
    if path is None or not path.exists():
        return None
    return f"    framework output: {path}"
