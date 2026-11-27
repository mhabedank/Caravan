"""``caravan init``: a first manifest from one proposal (features 013 and 015).

Thin, like the other verbs: options become given answers, the session proposes the rest, the line
mode asks what is open or uncertain, and the outcome becomes an exit code
(specs/015-init-one-proposal/contracts/cli-init.md). Without a person nothing is asked: ``--yes``
accepts the proposal, anything else writes nothing and says what would (spec FR-012 to FR-017).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from caravan.cli.main import EXIT_INTERNAL, EXIT_OK, EXIT_USAGE
from caravan.manifest._yaml import read_flow_mapping
from caravan.manifest.errors import render_finding

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

#: What a missing answer is called in a message, and the list its example comes from.
MISSING = {
    "dataset": ("data", ""),
    "boards": ("board", "registered"),
    "output": ("output column", "columns"),
    "output_type": ("output type", "allowed"),
    "normal_label": ("value that means normal", "values"),
    "window": ("window", "sizes"),
    "template": ("template", "registered"),
    "budget": ("budget", ""),
}


def add_parser(subcommands: Any) -> None:
    sub = subcommands.add_parser(
        "init", help="propose a first manifest from your data, and write it when accepted"
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
        "--agents-md",
        action="store_true",
        help="also write AGENTS.md beside the manifest, never over an existing one",
    )
    sub.add_argument(
        "--overwrite", action="store_true", help="confirms replacing an existing <manifest>"
    )
    sub.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="accept every proposal not given as an option; ask nothing",
    )
    sub.add_argument(
        "--no-input", action="store_true", help="ask nothing; without --yes, write nothing"
    )
    sub.add_argument(
        "--json",
        action="store_true",
        help="the result as one JSON document on standard output; ask nothing",
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
        "agents_md": True if args.agents_md else None,
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


def _terminal() -> bool:
    """Standard input and standard error are both terminals: the questions reach a person
    (feature 015, research R3). Standard output may be captured."""
    return sys.stdin.isatty() and sys.stderr.isatty()


def _person(args: argparse.Namespace) -> bool:
    """Whether ``init`` may ask (spec FR-012)."""
    return _terminal() and not (args.yes or args.no_input or args.json)


class Run:
    """One run's outcome, told to people on standard error or to programs as one document."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.json = bool(args.json)
        self.notes: list[Any] = []
        self.findings: list[Any] = []
        self.written: list[str] = []
        self.proposal: Any = None
        self.next: str | None = None

    def say(self, text: str = "") -> None:
        if not self.json:
            print(text, file=sys.stderr)

    def note(self, kind: str, message: str, **where: Any) -> None:
        from caravan.init.proposal import Note

        self.notes.append(Note(kind, message, **where))

    def end(self, outcome: str) -> int:
        from caravan.init.result import OUTCOMES, document

        if self.json:
            sys.stdout.write(
                document(
                    outcome,
                    proposal=self.proposal,
                    findings=self.findings,
                    notes=self.notes,
                    written=self.written,
                    next_command=self.next,
                )
            )
        return OUTCOMES[outcome]

    def refuse(self, problem: object, outcome: str = "refused") -> int:
        self.say(f"caravan init: {problem}")
        self.note(outcome, str(problem))
        return self.end(outcome)


def run(args: argparse.Namespace) -> int:
    from caravan.init.session import Session, Unusable

    out = Run(args)
    try:
        given = _given(args)
        edits = _inputs(args.input)
    except ValueError as problem:
        return out.refuse(problem)
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
            session.given_columns.update(edits)
        # The template and its parameters before the window, so a given window is checked
        # against the given template rather than the proposed one.
        for key in ("template", "params", "window", "budget", "name", "file", "agents_md"):
            if given.get(key) is not None:
                problem = session.accept(key, given[key])
                if problem:
                    raise ValueError(f"{key.replace('_', '-')}: {problem}")
                session.given.add(key)
    except Unusable as problem:
        return out.refuse(problem, "unusable")
    except ValueError as problem:
        return out.refuse(problem)

    if _person(args):
        return _with_person(session, out)
    return _without_person(session, out)


def _with_person(session: Any, out: Run) -> int:
    from caravan.init import line
    from caravan.init.session import Aborted

    def read(prompt: str) -> str:
        print(prompt, end="", file=sys.stderr, flush=True)
        text = sys.stdin.readline()
        if not text:
            raise EOFError
        return text.rstrip("\n")

    start: str | None = None
    try:
        while True:
            line.run(session, read, lambda text: print(text, file=sys.stderr), start)
            code = _write(session, out, dialogue=True)
            if isinstance(code, int):
                return code
            start = code
    except Aborted:
        print("caravan init: stopped; nothing was written", file=sys.stderr)
        return EXIT_USAGE


def _missing(session: Any, out: Run, roots: list[str]) -> list[str]:
    """One message per missing answer, each with one option and a working example (FR-015)."""
    examples = []
    for key in roots:
        label, listing = MISSING.get(key, (key.replace("_", " "), ""))
        _, reason = session.certainty(key)
        example = session.example(key)
        offered = ""
        if listing:
            values = [str(c.value) for c in session.choices(key) if not c.disabled]
            if key == "boards":
                values = list(session.boards.identifiers)
            if values:
                offered = f" ({listing}: {', '.join(values)})"
        option = example.split()[0]
        message = f"no {label}: {reason}; give it with {option}, for example"
        out.say(f"caravan init: {message}")
        out.say(f"  {example}{offered}")
        out.note("missing", f"no {label}: {reason}", key=key, example=example)
        examples.append(example)
    return examples


def _unusable(session: Any, roots: list[str]) -> str | None:
    """A missing answer no option can give: the data cannot be set up (research R1)."""
    if "window" in roots:
        table = session.window_table()
        if table is not None and table.path == "none":
            return f"window: {table.reason}"
    if "template" in roots:
        return f"template: {session.certainty('template')[1]}"
    return None


def _without_person(session: Any, out: Run) -> int:
    """Never ask (FR-012): ``--yes`` accepts; otherwise show the proposal and write nothing."""
    from caravan.init import proposal as proposals
    from caravan.init.result import accepting_command

    args = out.args
    if args.yes:
        problems = session.fill()
        failed = [item for item in problems if ":" in item]
        if failed:
            out.proposal = proposals.build(session)
            return out.refuse(failed[0])
    roots = session.missing_roots()
    out.proposal = proposals.build(session)
    reason = _unusable(session, roots)
    if reason is not None:
        return out.refuse(reason, "unusable")
    for note in out.proposal.notes:
        out.notes.append(note)
    if not args.yes or roots:
        for line in proposals.lines(out.proposal):
            out.say(line)
        for note in out.proposal.notes:
            out.say(f"  note: {note.message}")
        why = "--no-input asks nothing" if args.no_input else "no one to ask"
        if not args.yes:
            out.say(f"caravan init: nothing written: {why}, and --yes was not given")
        else:
            out.say("caravan init: nothing written: an answer has no proposal")
        examples = _missing(session, out, roots)
        out.next = accepting_command(args, examples)
        out.say(f"caravan init: to accept the proposal: {out.next}")
        return out.end("incomplete" if args.yes else "proposed")
    for note in out.proposal.notes:
        out.say(f"caravan init: note: {note.message}")
    taken = [
        item
        for item in out.proposal.items
        if item.source == "proposed" and item.certainty == "uncertain"
    ]
    if taken:
        parts = [
            f"{item.column or item.key.replace('_', ' ')} as {item.value or '-'} "
            f"({_change(item)} to change)"
            for item in taken
        ]
        out.say(
            f"caravan init: took {len(taken)} uncertain proposal"
            f"{'s' if len(taken) != 1 else ''}: {', '.join(parts)}"
        )
        for item, part in zip(taken, parts, strict=True):
            out.note(
                "uncertain-taken", part, key=item.key, column=item.column, example=_change(item)
            )
    code = _write(session, out, dialogue=False)
    assert isinstance(code, int)
    return code


def _change(item: Any) -> str:
    """An option that gives an uncertain item another of the values its data allows."""
    import shlex

    if item.key == "input" or not item.alternatives:
        return item.example
    return f"{item.option} {shlex.quote(str(item.alternatives[0]))}"


def _write(session: Any, out: Run, *, dialogue: bool) -> int | str:
    """Write and report; with a person, the item that owns a finding to ask again (013, R10)."""
    target, findings = session.write()
    name = target.name
    try:
        shown = str(target.relative_to(session.cwd))
    except ValueError:
        shown = str(target)
    if not findings:
        out.written.append(shown)
        out.next = f"caravan build {shown}"
        out.say(f"wrote {shown} — valid")
        if session.guide == "written":
            guide = str(Path(shown).parent / "AGENTS.md")
            out.written.append(guide)
            out.say(f"wrote {guide}")
        elif session.guide == "kept":
            message = "kept AGENTS.md: it exists, and init never changes it"
            out.say(message)
            out.note("agents-md-kept", message, key="agents_md")
        out.say(f"next: {out.next}")
        if not out.json:
            print(shown)
        return out.end("written") if not dialogue else EXIT_OK
    for finding in findings:
        out.say(render_finding(name, finding))
    if not dialogue:
        out.findings.extend(findings)
        out.say("caravan init: nothing was written")
        return out.end("invalid")
    first = findings[0].path
    owner = next((key for prefix, key in OWNERS if first.startswith(prefix)), None)
    if owner is None or owner not in session.asked():
        print("caravan init: an offered choice was refused; this is a defect", file=sys.stderr)
        return EXIT_INTERNAL
    session.answers.pop("review", None)
    return owner
