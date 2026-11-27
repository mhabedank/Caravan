"""The line mode: one proposal, the few questions it needs, one decision (features 013, 015).

The session's proposal and questions on standard error, answers from standard input: no colour, no
cursor movement, one answer per line. An empty line takes the proposal, ``<`` goes back, a number
picks a choice. The flow is research R2 of feature 015: the data, the proposal, the boards and the
open or uncertain items (the uncertain columns as one step), the proposal again, then write, adjust
one item, or stop.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from caravan.init import memory
from caravan.init import proposal as proposals
from caravan.init.form import Form, presets, show
from caravan.init.session import Aborted, Question, Session

Read = Callable[[str], str]
Write = Callable[[str], None]

BACK = "<"


class Back(Exception):
    """The author typed ``<``."""


def _ask(read: Read, prompt: str) -> str:
    try:
        text = read(prompt)
    except (EOFError, KeyboardInterrupt) as stop:
        raise Aborted from stop
    text = text.strip()
    if text == BACK:
        raise Back
    return text


def show_question(
    session: Session, question: Question, write: Write, *, panels: bool = True
) -> None:
    where = f"  ({question.field})" if question.field else ""
    write("")
    write(f"? {question.title}{where}")
    write(f"  {question.help}")
    if panels:
        for section in session.explain(question.key):
            write(f"  — {section.title}")
            for line in section.lines:
                write(f"    {line}")
    if question.key in session.stale:
        write("  ! an earlier answer changed: check this one again")


def _choices(question: Question, write: Write, chosen: Any = None) -> None:
    for number, choice in enumerate(question.choices, start=1):
        marks = []
        if chosen is not None and (
            choice.value == chosen or (isinstance(chosen, list) and choice.value in chosen)
        ):
            marks.append("proposed" if chosen == question.proposal else "chosen")
        detail = f"  {choice.detail}" if choice.detail else ""
        off = f"  (not available: {choice.disabled})" if choice.disabled else ""
        tag = f"  [{', '.join(marks)}]" if marks else ""
        write(f"  {number:>2}) {choice.label}{detail}{tag}{off}")


def _pick(question: Question, text: str) -> Any:
    """A choice by number or by its value as typed."""
    if text.isdigit() and 1 <= int(text) <= len(question.choices):
        choice = question.choices[int(text) - 1]
        if choice.disabled:
            raise ValueError(f"not available: {choice.disabled}")
        return choice.value
    for choice in question.choices:
        if str(choice.value) == text:
            return choice.value
    if question.key == "window":
        return text  # another size, checked by the session
    raise ValueError(f"choose 1 to {len(question.choices)}, or press Enter for the proposal")


def ask_one(session: Session, question: Question, read: Read, write: Write) -> Any:
    _choices(question, write, question.proposal)
    hint = " (Enter: proposal)" if question.proposal is not None else ""
    text = _ask(read, f"choose{hint} > ")
    if not text:
        if question.proposal is None:
            raise ValueError("there is no proposal here: choose one")
        return question.proposal
    return _pick(question, text)


def ask_many(
    session: Session, question: Question, read: Read, write: Write, footer: str = ""
) -> Any:
    _choices(question, write, question.proposal)
    if footer:
        write(f"      {footer}")
    text = _ask(read, "choose one or more, like 1,3 (Enter: as marked) > ")
    if not text:
        if not question.proposal:
            raise ValueError("choose at least one")
        return list(question.proposal)
    return [_pick(question, part.strip()) for part in text.split(",") if part.strip()]


def ask_columns(session: Session, question: Question, read: Read, write: Write) -> Any:
    current: dict[str, Any] = dict(question.proposal or {})
    for name, kind in current.items():
        write(f"    {name:<14} {kind or '-'}")
    text = _ask(read, "Enter to accept, or edits like dlc=number, b2=- > ")
    if not text:
        return current
    for edit in text.split(","):
        if "=" not in edit:
            raise ValueError(f"{edit.strip()!r}: write column=type, or column=- to leave it out")
        name, kind = (part.strip() for part in edit.split("=", 1))
        if name not in current:
            raise ValueError(f"no column {name!r} here")
        current[name] = None if kind in ("-", "") else kind
    return current


def ask_value(session: Session, question: Question, read: Read, write: Write) -> Any:
    shown = f" [{question.proposal}]" if question.proposal is not None else ""
    if question.reason:
        write(f"  proposed: {question.proposal} — {question.reason}")
    text = _ask(read, f"{question.title.split('?')[0].lower()}{shown} > ")
    if not text:
        if question.proposal is None:
            raise ValueError("there is no proposal here: type an answer")
        return question.proposal
    return text


def ask_form(session: Session, question: Question, read: Read, write: Write) -> Any:
    spec = session._spec()
    assert spec is not None
    start = presets(spec.starter.params if spec.starter else None)
    current = question.proposal or {}
    write(f"  now: {session.describe('params') or '—'}")
    for number, (label, value) in enumerate(start, start=1):
        write(f"  {number:>2}) {label}: {Form(spec.parameters, value).params()}")
    write("   e) edit the values one by one")
    text = _ask(read, "choose (Enter: keep as now) > ")
    if not text:
        if not current:
            raise ValueError("there is no proposal here: choose e to enter the values")
        return current
    if text.isdigit() and 1 <= int(text) <= len(start):
        return Form(spec.parameters, start[int(text) - 1][1]).params()
    if text.lower() != "e":
        raise ValueError("a preset's number, or e")
    form = Form(spec.parameters, current)
    for slot in form.slots:
        if slot.shape == "value":
            assert slot.kind is not None
            now = show(form.get(slot.key))
            answer = _ask(read, f"  {slot.key} ({slot.kind.describe()}) [{now}] > ")
            if answer:
                form.set(slot.key, answer)
            continue
        rows = _ask(read, f"  {slot.key}: how many rows? [{form.rows(slot.key)}] > ")
        if rows:
            wanted = int(rows)
            while form.rows(slot.key) < wanted and form.add(slot.key):
                pass
            while form.rows(slot.key) > wanted and form.remove(slot.key, form.rows(slot.key) - 1):
                pass
        for row in range(form.rows(slot.key)):
            if slot.shape == "values":
                assert slot.kind is not None
                now = show(form.get(slot.key, row))
                answer = _ask(read, f"  {slot.key} {row + 1} ({slot.kind.describe()}) [{now}] > ")
                if answer:
                    form.set(slot.key, answer, row=row)
                continue
            for name, kind, _ in slot.fields:
                now = show(form.get(slot.key, row, name))
                answer = _ask(read, f"  {slot.key} {row + 1} {name} ({kind.describe()}) [{now}] > ")
                if answer:
                    form.set(slot.key, answer, row=row, name=name)
    errors = form.errors()
    if errors:
        where, problem = next(iter(errors.items()))
        raise ValueError(f"{where}: {problem}")
    return form.params()


ASK = {
    "one": ask_one,
    "review": ask_one,
    "many": ask_many,
    "columns": ask_columns,
    "number": ask_value,
    "text": ask_value,
    "form": ask_form,
}


# --- the flow of feature 015 ------------------------------------------------------------------

DATA_TITLE = "Where is the data?"
COLUMNS_TITLE = "These columns could be read more than one way"


def ask_dataset(session: Session, read: Read, write: Write) -> None:
    """The one question before the proposal; data in the current directory is offered."""
    found = session.candidates()
    write("")
    write(f"? {DATA_TITLE}  (dataset)")
    write(f"  {session.help('dataset')}")
    for number, name in enumerate(found, start=1):
        write(f"  {number:>2}) {name}")
    while True:
        try:
            text = _ask(read, "a number, or a path > " if found else "a path > ")
        except Back:
            write("  this is the first question")
            continue
        if not text:
            write("  ✗ the data comes first: type a path")
            continue
        value = found[int(text) - 1] if text.isdigit() and 1 <= int(text) <= len(found) else text
        problem = session.take("dataset", value)
        if problem:
            write(f"  ✗ {problem}")
            continue
        return


def ask_boards(session: Session, read: Read, write: Write) -> str | None:
    question = session.question("boards")
    show_question(session, question, write, panels=False)
    footer = memory.SHORT_LABEL if session.board_bounds() else ""
    return session.take("boards", ask_many(session, question, read, write, footer))


def ask_uncertain_columns(session: Session, read: Read, write: Write) -> str | None:
    """All uncertain input columns in one step (spec FR-007, FR-008)."""
    assert session.data is not None
    names = session.uncertain_columns()
    current: dict[str, Any] = dict(session.value("inputs") or {})
    write("")
    write(f"? {COLUMNS_TITLE}  (input_features)")
    for name in names:
        column = session.data.column(name)
        now = current.get(name)
        others = ", ".join(a or "-" for a in column.alternatives if a != now)
        write(f"    {name:<14} {now or '-':<9} {column.reason}   or: {others}")
    text = _ask(read, "Enter to accept as shown, or edits like dlc=number, can_id=- > ")
    for edit in filter(None, (part.strip() for part in text.split(","))):
        if "=" not in edit:
            raise ValueError(f"{edit!r}: write column=type, or column=- to leave it out")
        name, kind = (part.strip() for part in edit.split("=", 1))
        if name not in current:
            raise ValueError(f"no column {name!r} here")
        current[name] = None if kind in ("-", "") else kind
    problem = session.take("inputs", current)
    if problem is None:
        session.answered_columns.update(names)
    return problem


def ask_item(session: Session, key: str, read: Read, write: Write, *, every: bool = False) -> None:
    """Ask one item until it is answered; ``every`` shows all columns rather than the uncertain."""
    while True:
        try:
            if key == "dataset":
                ask_dataset(session, read, write)
                return
            if key == "boards":
                problem = ask_boards(session, read, write)
            elif key == "inputs" and not every:
                problem = ask_uncertain_columns(session, read, write)
            else:
                question = session.question(key)
                show_question(session, question, write)
                problem = session.take(key, ASK[question.kind](session, question, read, write))
                if problem is None and key == "inputs" and session.data is not None:
                    session.answered_columns.update(session.data.names)
        except ValueError as error:
            problem = str(error)
        if not problem:
            return
        write(f"  ✗ {problem}")


def ask_open(session: Session, read: Read, write: Write) -> None:
    """The boards and every open or uncertain item not given, in order; ``<`` goes back."""
    history: list[str] = []
    while True:
        pending = session.to_ask()
        if not pending:
            return
        key = pending[0]
        try:
            ask_item(session, key, read, write)
        except Back:
            if not history:
                write("  this is the first question")
                continue
            session.answered.discard(history.pop())
            continue
        history.append(key)


def show_proposal(session: Session, write: Write) -> proposals.Proposal:
    made = proposals.build(session)
    write("")
    for line in proposals.lines(made):
        write(line)
    for note in made.notes:
        write(f"  note: {note.message}")
    return made


def adjustable(session: Session) -> list[str]:
    keys = session.keys()
    shown = [k for k in proposals.SHOWN if k in keys and k not in session.given]
    return ["dataset", *shown] if "dataset" not in session.given else shown


def adjust(session: Session, read: Read, write: Write, key: str | None = None) -> None:
    """Pick one item and answer it with its full question (spec FR-010)."""
    if key is None:
        keys = adjustable(session)
        write("")
        write("? Which item?")
        for number, item in enumerate(keys, start=1):
            label = "data" if item == "dataset" else proposals.LABELS[item]
            write(f"  {number:>2}) {label:<10} {session.describe(item)}")
        while True:
            try:
                text = _ask(read, "a number or a name (Enter: back to the proposal) > ")
            except Back:
                return
            if not text:
                return
            names = {proposals.LABELS.get(k, k): k for k in keys} | {k: k for k in keys}
            names["data"] = "dataset"
            if text.isdigit() and 1 <= int(text) <= len(keys):
                key = keys[int(text) - 1]
                break
            if text in names and names[text] in keys:
                key = names[text]
                break
            write(f"  ✗ choose 1 to {len(keys)}, or an item's name")
    try:
        ask_item(session, key, read, write, every=True)
    except Back:
        return


def decide(session: Session, read: Read, write: Write) -> None:
    """Show the proposal and offer exactly: write, adjust, stop (spec FR-009, FR-011)."""
    while True:
        made = show_proposal(session, write)
        if made.ready:
            prompt = f"Enter: write {session.value('file')} · a: adjust · q: stop > "
        else:
            write("  not ready to write:")
            for blocker in session.blockers():
                write(f"    - {blocker}")
            prompt = "a: adjust · q: stop > "
        try:
            text = _ask(read, prompt).lower()
        except Back:
            text = "a"
        if not text and made.ready:
            return
        if text in ("q", "stop"):
            raise Aborted
        if text in ("a", "adjust"):
            adjust(session, read, write)
            ask_open(session, read, write)
            continue
        if text:
            write("  ✗ Enter to write, a to adjust, q to stop")


def run(session: Session, read: Read, write: Write, start: str | None = None) -> None:
    """Until the person accepts; ``Aborted`` on stop, interrupt or end of input.

    ``start`` names an item to ask first, as after a finding that item owns (feature 013, R10).
    """
    if session.data is None:
        ask_dataset(session, read, write)
    if start is not None:
        adjust(session, read, write, start)
    else:
        show_proposal(session, write)
    ask_open(session, read, write)
    decide(session, read, write)
