"""``caravan init``: write a first manifest by answering questions (feature 013).

Thin, like the other verbs: options become given answers, the session asks the rest (in the
full-screen interface when the ``authoring`` extra is installed and both ends are terminals, else
line by line), and the outcome becomes an exit code (contracts/cli-init.md).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from caravan.cli.main import EXIT_INTERNAL, EXIT_OK, EXIT_RULE, EXIT_USAGE
from caravan.manifest._yaml import read_flow_mapping
from caravan.manifest.errors import render_finding

INSTALL_HINT = (
    "the full-screen interface comes with the authoring extra: "
    'pip install "caravan-ml[authoring] @ <the release wheel>"'
)

#: Where a finding's path sends the dialogue back to (research R10).
OWNERS = (
    ("model.params", "params"),
    ("model.template", "template"),
    ("preprocessing.window_size", "window"),
    ("export.targets", "boards"),
    ("input_features", "inputs"),
    ("output_features", "budget"),
    ("dataset", "dataset"),
)


def add_parser(subcommands: Any) -> None:
    sub = subcommands.add_parser(
        "init", help="write a first manifest from your data by answering questions"
    )
    sub.add_argument("manifest", metavar="<manifest>", nargs="?", help="the file to write")
    sub.add_argument("--dataset", metavar="<path>", help="a directory of tables, or one table")
    sub.add_argument("--output", metavar="<column>", help="the column the model predicts")
    sub.add_argument("--output-type", metavar="<type>", help="category, binary, number or anomaly")
    sub.add_argument("--normal-label", metavar="<value>", help="for anomaly: the normal value")
    sub.add_argument(
        "--input",
        metavar="<column>=<type>",
        action="append",
        default=[],
        help="one input column and its type, or <column>=- to leave it out; repeatable",
    )
    sub.add_argument("--template", metavar="<id>", help="a registered template")
    sub.add_argument(
        "--params", metavar="<mapping>", help="the template's parameters, e.g. '{hidden: [32]}'"
    )
    sub.add_argument("--window", metavar="<rows>", type=int, help="rows per window")
    sub.add_argument(
        "--board", metavar="<id>", action="append", default=[], help="a board; repeatable"
    )
    sub.add_argument("--quantization", metavar="<int8|none>", help="how the weights are stored")
    sub.add_argument("--budget", metavar="<value>", type=float, help="the output's int8 budget")
    sub.add_argument("--name", metavar="<model-name>", help="model.name")
    sub.add_argument(
        "--overwrite", action="store_true", help="confirms replacing an existing <manifest>"
    )
    sub.add_argument("--no-input", action="store_true", help="ask nothing; options, then proposals")
    sub.add_argument(
        "--plain", action="store_true", help="the line dialogue even with the authoring extra"
    )


def _given(args: argparse.Namespace) -> dict[str, Any]:
    given: dict[str, Any] = {
        "dataset": args.dataset,
        "boards": list(args.board) or None,
        "quantization": args.quantization,
        "output": args.output,
        "output_type": args.output_type,
        "normal_label": args.normal_label,
        "window": args.window,
        "template": args.template,
        "budget": args.budget,
        "name": args.name,
        "file": args.manifest,
    }
    if args.params is not None:
        given["params"] = read_flow_mapping(args.params)
    return given


def _inputs(edits: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for edit in edits:
        if "=" not in edit:
            raise ValueError(
                f"--input {edit}: write <column>=<type>, or <column>=- to leave it out"
            )
        name, kind = (part.strip() for part in edit.split("=", 1))
        out[name] = None if kind in ("-", "") else kind
    return out


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def run(args: argparse.Namespace) -> int:
    from caravan.init.session import Aborted, Session

    try:
        given = _given(args)
        edits = _inputs(args.input)
    except ValueError as problem:
        print(f"caravan init: {problem}", file=sys.stderr)
        return EXIT_USAGE
    ordered = {
        key: given.get(key)
        for key in ("dataset", "boards", "quantization", "output", "output_type", "normal_label")
    }
    try:
        session = Session(ordered, overwrite=args.overwrite)
        if edits:
            proposal = dict(session.value("inputs") or {})
            unknown = [name for name in edits if name not in proposal]
            if unknown:
                raise ValueError(f"--input: no column {unknown[0]!r} besides the output")
            proposal.update(edits)
            problem = session.accept("inputs", proposal)
            if problem:
                raise ValueError(f"--input: {problem}")
            session.given.add("inputs")
        for key in ("window", "template", "params", "budget", "name", "file"):
            if given.get(key) is not None:
                problem = session.accept(key, given[key])
                if problem:
                    raise ValueError(f"{key.replace('_', '-')}: {problem}")
                session.given.add(key)
    except ValueError as problem:
        print(f"caravan init: {problem}", file=sys.stderr)
        return EXIT_USAGE

    if args.no_input:
        missing = session.fill()
        if missing:
            from caravan.init.session import OPTIONS

            names = [OPTIONS.get(item.split(":")[0], item) for item in missing]
            print(
                f"caravan init: no answer and no proposal for {', '.join(names)}; give "
                f"{'it' if len(names) == 1 else 'them'} as an option",
                file=sys.stderr,
            )
            if any(":" in item for item in missing):
                print(f"caravan init: {missing[0]}", file=sys.stderr)
            return EXIT_USAGE
        return _write(session, dialogue=False)

    use_tui = not args.plain and _interactive()
    if use_tui:
        try:
            from caravan.tui.app import run_app
        except ImportError:
            print(f"caravan init: {INSTALL_HINT}", file=sys.stderr)
            use_tui = False
    try:
        while True:
            if use_tui:
                if not run_app(session):
                    raise Aborted
            else:
                from caravan.init import line

                def read(prompt: str) -> str:
                    print(prompt, end="", file=sys.stderr, flush=True)
                    text = sys.stdin.readline()
                    if not text:
                        raise EOFError
                    return text.rstrip("\n")

                line.run(session, read, lambda text: print(text, file=sys.stderr))
            code = _write(session, dialogue=True)
            if code is not None:
                return code
    except Aborted:
        print("caravan init: stopped; nothing was written", file=sys.stderr)
        return EXIT_USAGE


def _write(session: Any, *, dialogue: bool) -> int | None:
    """Write and report. ``None`` when the dialogue goes back to fix a finding (research R10)."""
    target, findings = session.write()
    name = target.name
    if not findings:
        try:
            shown = target.relative_to(session.cwd)
        except ValueError:
            shown = target
        print(f"wrote {shown} — valid", file=sys.stderr)
        print(f"next: caravan build {shown}", file=sys.stderr)
        print(shown)
        return EXIT_OK
    for finding in findings:
        print(render_finding(name, finding), file=sys.stderr)
    if not dialogue:
        print("caravan init: nothing was written", file=sys.stderr)
        return EXIT_RULE
    first = findings[0].path
    owner = next((key for prefix, key in OWNERS if first.startswith(prefix)), None)
    if owner is None or owner not in session.asked():
        print("caravan init: an offered choice was refused; this is a defect", file=sys.stderr)
        return EXIT_INTERNAL
    session.answers.pop("review", None)
    session.go(owner)
    return None
