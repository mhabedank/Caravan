"""What a run of ``caravan init`` ended in, for people and for programs (feature 015).

``accepting_command`` rebuilds the command as given and adds what it lacks — each open item's
example and ``--yes`` — so a message or a document can say exactly what to run next
(contracts/cli-init.md, "Without a person"). ``document`` is the JSON object of ``--json``
(contracts/init-result.md): one per run, every key always present, keys in a fixed order.
"""

from __future__ import annotations

import argparse
import json
import shlex
from collections.abc import Sequence
from typing import Any

#: Each outcome and its exit code (contracts/cli-init.md, "Exit codes and outcomes"); the codes
#: are ``caravan.cli.main``'s, which ``tests/contract/test_init_json.py`` checks.
OUTCOMES = {
    "written": 0,
    "invalid": 1,
    "unusable": 1,
    "proposed": 2,
    "incomplete": 2,
    "refused": 2,
}

#: The options of ``init`` that take a value, in the order the command is rebuilt.
VALUED = (
    ("dataset", "--dataset"),
    ("output", "--output"),
    ("output_type", "--output-type"),
    ("normal_label", "--normal-label"),
    ("template", "--template"),
    ("params", "--params"),
    ("window", "--window"),
    ("quantization", "--quantization"),
    ("budget", "--budget"),
    ("name", "--name"),
)
FLAGS = (
    ("agents_md", "--agents-md"),
    ("overwrite", "--overwrite"),
    ("no_input", "--no-input"),
    ("yes", "--yes"),
    ("json", "--json"),
)


def command(args: argparse.Namespace) -> list[str]:
    """The command as given, rebuilt from the parsed options in one canonical order."""
    out = ["caravan", "init"]
    if getattr(args, "manifest", None):
        out.append(args.manifest)
    for name, option in VALUED:
        value = getattr(args, name, None)
        if value is not None:
            out += [option, f"{value:g}" if isinstance(value, float) else str(value)]
    for edit in getattr(args, "input", None) or []:
        out += ["--input", edit]
    for board in getattr(args, "board", None) or []:
        out += ["--board", board]
    for name, option in FLAGS:
        if getattr(args, name, False):
            out.append(option)
    return out


def accepting_command(args: argparse.Namespace, examples: Sequence[str]) -> str:
    """The command as given, plus every example (each already shell-quoted), plus ``--yes``."""
    words = command(args)
    for example in examples:
        if example.startswith("-"):
            words += shlex.split(example)
        elif not getattr(args, "manifest", None):  # the positional <manifest>
            words.insert(2, shlex.split(example)[0])
    if "--yes" not in words:
        words.append("--yes")
    return shlex.join(words)


def document(
    outcome: str,
    *,
    proposal: Any = None,
    findings: Sequence[Any] = (),
    notes: Sequence[Any] = (),
    written: Sequence[str] = (),
    next_command: str | None = None,
) -> str:
    """The result document (contracts/init-result.md), serialised as ``validate --json`` is."""
    assert outcome in OUTCOMES, outcome
    body = {
        "outcome": outcome,
        "written": list(written),
        "dataset": proposal.dataset if proposal is not None else None,
        "items": [item.as_dict() for item in proposal.items] if proposal is not None else [],
        "memory": [record.as_dict() for record in proposal.memory] if proposal is not None else [],
        "findings": [finding.as_dict() for finding in findings],
        "notes": [note.as_dict() for note in notes],
        "next": next_command,
    }
    return json.dumps(body, indent=2, ensure_ascii=False) + "\n"
