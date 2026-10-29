"""The command blocks of a document, read the way a reader would copy them (feature 007, SC-003).

A block is a fenced ``bash`` block whose first line is ``# step: <name>``, the name in lower case
with hyphens allowed (``board-copy``). The installation page marks its block ``install``; the
tutorial's parts mark theirs ``fetch`` and ``run`` (part 1), ``own-columns`` (part 2),
``board-tools``, ``board-copy``, ``board-build`` and ``board-flash`` (part 3) and ``tighten``
(part 4). The tests execute what needs no board; the release workflow executes ``install``,
``fetch`` and ``run`` against the published release, and the firmware workflow builds part 3's.

Run as ``python -m tests.support_docs <file> <step>`` to print that step's blocks, one after the
other, for a shell to execute.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BLOCK = re.compile(
    r"^```bash\n# step: (?P<step>[a-z-]+)\n(?P<body>.*?)^```$", re.MULTILINE | re.DOTALL
)


def blocks(path: Path, step: str) -> list[str]:
    """Every block of ``step`` in ``path``, in document order, without the marker line."""
    text = path.read_text(encoding="utf-8")
    return [m["body"] for m in BLOCK.finditer(text) if m["step"] == step]


def commands(path: Path, step: str) -> list[str]:
    """The commands of ``step``: one per line, continuation lines joined, comments dropped."""
    out: list[str] = []
    for body in blocks(path, step):
        joined = body.replace("\\\n", " ")
        lines = (line.strip() for line in joined.splitlines())
        out.extend(line for line in lines if line and not line.startswith("#"))
    return out


def main(argv: list[str]) -> int:
    path, step = Path(argv[0]), argv[1]
    found = blocks(path, step)
    if not found:
        print(f"{path}: no block marked '# step: {step}'", file=sys.stderr)
        return 1
    sys.stdout.write("".join(found))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
