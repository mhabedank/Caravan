"""The line dialogue: the session's questions on standard error, answers from standard input.

Works in any terminal and with no terminal at all (FR-022): no colour, no cursor movement, one
answer per line. An empty line takes the proposal, ``<`` goes back, a number picks a choice.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

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


def show_question(session: Session, question: Question, write: Write) -> None:
    step = session.asked().index(question.key) + 1
    total = len(session.asked())
    where = f"  ({question.field})" if question.field else ""
    write("")
    write(f"[{step}/{total}] ? {question.title}{where}")
    write(f"  {question.help}")
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


def ask_many(session: Session, question: Question, read: Read, write: Write) -> Any:
    _choices(question, write, question.proposal)
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


def run(session: Session, read: Read, write: Write) -> None:
    """Ask until the author chooses to write; ``Aborted`` on interrupt or end of input."""
    while not session.done:
        question = session.current()
        show_question(session, question, write)
        try:
            value = ASK[question.kind](session, question, read, write)
        except Back:
            if not session.back():
                write("  this is the first question")
            continue
        except ValueError as problem:
            write(f"  ✗ {problem}")
            continue
        problem_text = session.answer(value)
        if problem_text:
            write(f"  ✗ {problem_text}")
