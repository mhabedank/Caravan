"""The ``AGENTS.md`` that ``caravan init --agents-md`` writes beside the manifest (feature 015).

A guide for a coding agent working in the author's project: which file describes the model, how to
check and build it, what the exit codes mean, and which decisions belong to the author
(contracts/agents-md.md, spec FR-025 to FR-029, constitution v4.5.0 Principle XII). Its only
variable is the manifest's file name: no value of the manifest (Principle I), no date, no version.
It claims no check of rights (Principle VI) and describes no workflow in which an agent produces
data, labels or selection signals (Principle XI).

The file is written only after the manifest has validated, never over an existing ``AGENTS.md``,
and together with the manifest or not at all (research R8).
"""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path

NAME = "AGENTS.md"

#: The guide's text, kept as a file beside this module so it reads as what it is: the exact text of
#: contracts/agents-md.md, with ``{manifest}`` its only variable.
TEXT = files("caravan.init").joinpath("agents.md").read_text(encoding="utf-8")


def render(manifest_name: str) -> str:
    """The guide for the manifest called ``manifest_name`` in the same directory."""
    return TEXT.replace("{manifest}", manifest_name)


def place(directory: Path, text: str) -> Path | None:
    """Create ``AGENTS.md`` in ``directory`` exclusively; ``None`` when one is already there.

    Written to a temporary file first and linked into place, so the guide either appears whole or
    not at all, and a file created meanwhile by someone else is never replaced.
    """
    target = directory / NAME
    if target.exists():
        return None
    temporary = directory / f".caravan-init-{os.getpid()}-{NAME}"
    temporary.write_text(text, encoding="utf-8")
    try:
        try:
            os.link(temporary, target)
        except FileExistsError:
            return None
        except OSError:  # a file system without hard links: create it exclusively instead
            try:
                with target.open("x", encoding="utf-8") as stream:
                    stream.write(text)
            except FileExistsError:
                return None
    finally:
        temporary.unlink(missing_ok=True)
    return target
