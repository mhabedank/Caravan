"""A Textual front end over the ``caravan init`` session (feature 013, US4, research R11).

The app holds no knowledge of its own: it asks the session for the current question, shows its
choices as a list, checkboxes, a column table, a field or a form, and hands the answer back. The
side panel shows what ``Session.explain`` returns. Nothing is written here; when the author
chooses to write, the app closes and ``caravan init`` writes and validates, as for the dialogue.
"""

from __future__ import annotations

from typing import Any, ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Input, OptionList, Select, SelectionList, Static
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection

from caravan.init.form import Form, presets, show
from caravan.init.session import Question, Session

COLUMN_TYPES = ("number", "category", "binary", None)


class Checks(SelectionList):
    """Checkboxes: space toggles, Enter goes on."""

    BINDINGS: ClassVar = [
        Binding("space", "select", "toggle"),
        Binding("enter", "submit", "continue"),
    ]

    def action_submit(self) -> None:
        self.app.submit(list(self.selected))  # type: ignore[attr-defined]


class InitApp(App[bool]):
    """caravan init, full screen."""

    TITLE = "caravan init"
    CSS = """
    Screen { layout: vertical; }
    #top { height: 1; background: $panel; padding: 0 1; }
    #main { height: 1fr; }
    #left { width: 1fr; min-width: 50; }
    #steps { height: auto; max-height: 16; padding: 0 1; border-bottom: solid $panel; }
    #question { height: auto; padding: 1 1 0 1; }
    #problem { height: auto; padding: 0 1; color: $error; }
    #answer { height: 1fr; padding: 0 1; }
    #answer OptionList, #answer SelectionList { height: auto; max-height: 100%; }
    #right { width: 1fr; border-left: solid $panel; padding: 0 1; }
    .row { height: auto; }
    .row Input { width: 14; }
    .row Select { width: 18; }
    .row Static { width: auto; padding: 0 1 0 0; }
    .slot { height: auto; padding: 0 0 1 0; }
    Button { min-width: 5; }
    """
    BINDINGS: ClassVar = [
        Binding("escape", "back", "back"),
        Binding("ctrl+q", "quit_init", "quit"),
        Binding("ctrl+s", "submit_form", "continue", show=False),
    ]

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.form: Form | None = None
        self.values: list[Any] = []
        self.columns: dict[str, Any] = {}

    # --- layout --------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(id="top")
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Static(id="steps")
                yield Static(id="question")
                yield Static(id="problem")
                yield VerticalScroll(id="answer")
            yield VerticalScroll(Static(id="explain"), id="right")
        yield Footer()

    def on_mount(self) -> None:
        self.show()

    # --- showing a question --------------------------------------------------------------------

    def show(self, problem: str = "") -> None:
        session = self.session
        question = session.current()
        asked = session.asked()
        step = asked.index(question.key) + 1
        top = Text()
        top.append("caravan init", style="bold")
        top.append(f" · step {step} of {len(asked)} · {question.key.replace('_', ' ')}")
        top.append("   nothing written yet", style="dim")
        self.query_one("#top", Static).update(top)

        steps = Text()
        for key in session.keys():  # noqa: SIM118 - a method of the session, not a dict
            if key in session.given:
                mark, style = "=", "dim"
            elif key == question.key:
                mark, style = "▸", "bold"
            elif key in session.stale:
                mark, style = "!", "yellow"
            elif key in session.answers:
                mark, style = "✓", "green"
            else:
                mark, style = "·", "dim"
            steps.append(f"{mark} {key.replace('_', ' '):<14}", style=style)
            if key in session.answers or key in session.given:
                steps.append(session.describe(key)[:60], style="dim")
            steps.append("\n")
        self.query_one("#steps", Static).update(steps)

        head = Text()
        head.append(f"? {question.title}", style="bold")
        if question.field:
            head.append(f"  ({question.field})", style="dim")
        head.append(f"\n{question.help}", style="dim")
        if question.reason and question.proposal is not None and question.kind != "review":
            head.append(f"\nproposed: {question.reason}", style="italic")
        self.query_one("#question", Static).update(head)
        self.query_one("#problem", Static).update(Text(f"✗ {problem}" if problem else ""))
        self.show_explain()
        self.call_later(self.mount_answer, question)

    def show_explain(self) -> None:
        text = Text()
        for section in self.session.explain():
            text.append(f"{section.title}\n", style="bold")
            for line in section.lines:
                style = "red" if line.rstrip().endswith("✗") else ""
                text.append(f"{line}\n", style=style)
            text.append("\n")
        self.query_one("#explain", Static).update(text)

    async def mount_answer(self, question: Question) -> None:
        area = self.query_one("#answer", VerticalScroll)
        await area.remove_children()
        widget: Any
        if question.kind in ("one", "review"):
            self.values = [choice.value for choice in question.choices]
            options = []
            for choice in question.choices:
                label = Text(
                    choice.label, style="bold" if choice.value == question.proposal else ""
                )
                if choice.detail:
                    label.append(f"  {choice.detail}", style="dim")
                if choice.value == question.proposal and question.kind == "one":
                    label.append("  (proposed)", style="italic")
                if choice.disabled:
                    label.append(f"  — {choice.disabled}", style="dim")
                options.append(Option(label, disabled=bool(choice.disabled)))
            widget = OptionList(*options, id="one")
            await area.mount(widget)
            if question.proposal in self.values:
                widget.highlighted = self.values.index(question.proposal)
        elif question.kind == "many":
            chosen = question.proposal or []
            widget = Checks(
                *(
                    Selection(
                        Text(f"{c.label}  ").append(c.detail, style="dim"),
                        c.value,
                        c.value in chosen,
                    )
                    for c in question.choices
                ),
                id="many",
            )
            await area.mount(
                widget, Static(Text("space: tick or untick · enter: go on", style="dim"))
            )
        elif question.kind == "columns":
            self.columns = dict(question.proposal or {})
            widget = OptionList(id="columns")
            await area.mount(
                widget,
                Static(
                    Text("enter on a column: change its type · enter on → : go on", style="dim")
                ),
            )
            self.fill_columns()
            # The proposal is one keystroke away (FR-012): the cursor starts on "go on".
            widget.highlighted = len(self.columns)
        elif question.kind in ("number", "text"):
            value = "" if question.proposal is None else str(question.proposal)
            widget = Input(value=value, id="value")
            await area.mount(widget, Static(Text("enter: go on", style="dim")))
        else:
            await self.mount_form(question)
            return
        widget.focus()

    def fill_columns(self) -> None:
        widget = self.query_one("#columns", OptionList)
        keep = widget.highlighted or 0
        widget.clear_options()
        data = self.session.data
        for name, kind in self.columns.items():
            reason = data.column(name).reason if data else ""
            label = Text(f"{name:<14}", style="bold" if kind else "dim")
            label.append(f"{kind or 'left out':<10}", style="" if kind else "dim")
            label.append(reason[:50], style="dim")
            widget.add_option(Option(label))
        widget.add_option(Option(Text("→ go on with these inputs", style="bold")))
        widget.highlighted = keep

    # --- the parameter form --------------------------------------------------------------------

    async def mount_form(self, question: Question) -> None:
        spec = self.session._spec()
        assert spec is not None
        self.form = Form(spec.parameters, question.proposal or {})
        area = self.query_one("#answer", VerticalScroll)
        starts = presets(spec.starter.params if spec.starter else None)
        if starts:
            await area.mount(
                Static(Text("start from", style="bold")),
                Horizontal(
                    *(
                        Button(label, id=f"preset-{n}", compact=True)
                        for n, (label, _) in enumerate(starts)
                    ),
                    classes="row",
                ),
            )
        await self.mount_slots()
        await area.mount(
            Horizontal(
                Button("go on", id="form-done", variant="primary", compact=True), classes="row"
            ),
            Static(Text("tab: next field · ctrl+s: go on", style="dim")),
        )

    async def mount_slots(self) -> None:
        assert self.form is not None
        area = self.query_one("#answer", VerticalScroll)
        for old in area.query(".slot"):
            await old.remove()
        form = self.form
        mounted = []
        for slot in form.slots:
            box = Vertical(classes="slot", id=f"slot-{slot.key}")
            children: list[Any] = [Static(Text(slot.key, style="bold"))]
            if slot.shape == "value":
                assert slot.kind is not None
                children.append(
                    Horizontal(
                        self.field(slot.kind, form.get(slot.key), f"f--{slot.key}"),
                        Static(Text(slot.kind.describe(), style="dim")),
                        classes="row",
                    )
                )
            elif slot.shape == "values":
                assert slot.kind is not None
                for row in range(form.rows(slot.key)):
                    children.append(
                        Horizontal(
                            Static(f"{row + 1}"),
                            self.field(slot.kind, form.get(slot.key, row), f"f--{slot.key}--{row}"),
                            Button("-", id=f"del--{slot.key}--{row}", compact=True),
                            classes="row",
                        )
                    )
                children.append(
                    Horizontal(
                        Button(f"+ {slot.key}", id=f"add--{slot.key}", compact=True), classes="row"
                    )
                )
            else:
                for row in range(form.rows(slot.key)):
                    parts: list[Any] = [Static(f"{row + 1}")]
                    for name, kind, _ in slot.fields:
                        parts.append(Static(Text(name, style="dim")))
                        parts.append(
                            self.field(
                                kind, form.get(slot.key, row, name), f"f--{slot.key}--{row}--{name}"
                            )
                        )
                    parts.append(Button("-", id=f"del--{slot.key}--{row}", compact=True))
                    children.append(Horizontal(*parts, classes="row"))
                children.append(
                    Horizontal(
                        Button(
                            f"+ {slot.key[:-1] if slot.key.endswith('s') else slot.key}",
                            id=f"add--{slot.key}",
                            compact=True,
                        ),
                        classes="row",
                    )
                )
            mounted.append((box, children))
        anchor = area.query("#form-done")
        for box, children in mounted:
            if anchor:
                await area.mount(box, before=anchor.first().parent)
            else:
                await area.mount(box)
            await box.mount(*children)
        self.form_errors()

    def field(self, kind: Any, value: Any, ident: str) -> Any:
        if kind.name == "choice":
            options = [(str(c), c) for c in kind.choices]
            return Select(
                options,
                value=value if value in kind.choices else Select.BLANK,
                id=ident,
                allow_blank=kind.optional,
                compact=True,
            )
        if kind.name == "bool":
            return Select(
                [("yes", True), ("no", False)],
                value=bool(value),
                id=ident,
                allow_blank=False,
                compact=True,
            )
        return Input(value=show(value), id=ident, compact=True)

    def form_errors(self) -> None:
        assert self.form is not None
        errors = self.form.errors()
        if not errors:
            problem = self.session._fits(
                self.session.value("template"), self.form.value, self.session.value("window")
            )
            if problem is None:
                self.session.accept("params", self.form.params())
                self.show_explain()
            self.query_one("#problem", Static).update(Text(f"✗ {problem}" if problem else ""))
            return
        where, problem = next(iter(errors.items()))
        self.query_one("#problem", Static).update(Text(f"✗ {where}: {problem}"))

    def _form_set(self, ident: str, text: str) -> None:
        assert self.form is not None
        parts = ident.split("--")[1:]
        try:
            if len(parts) == 1:
                self.form.set(parts[0], text)
            elif len(parts) == 2:
                self.form.set(parts[0], text, row=int(parts[1]))
            else:
                self.form.set(parts[0], text, row=int(parts[1]), name=parts[2])
        except ValueError as problem:
            self.query_one("#problem", Static).update(Text(f"✗ {'.'.join(parts)}: {problem}"))
            return
        self.form_errors()

    # --- events --------------------------------------------------------------------------------

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "columns":
            names = list(self.columns)
            if event.option_index == len(names):
                self.submit(dict(self.columns))
                return
            name = names[event.option_index]
            now = (
                COLUMN_TYPES.index(self.columns[name]) if self.columns[name] in COLUMN_TYPES else 3
            )
            self.columns[name] = COLUMN_TYPES[(now + 1) % len(COLUMN_TYPES)]
            self.fill_columns()
            return
        self.submit(self.values[event.option_index])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "value":
            self.submit(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id and event.input.id.startswith("f--"):
            self._form_set(event.input.id, event.value)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id and event.select.id.startswith("f--"):
            value = "" if event.value is Select.BLANK else show(event.value)
            self._form_set(event.select.id, value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        ident = event.button.id or ""
        if ident == "form-done":
            self.action_submit_form()
            return
        assert self.form is not None
        if ident.startswith("preset-"):
            spec = self.session._spec()
            assert spec is not None
            value = presets(spec.starter.params if spec.starter else None)[
                int(ident.split("-")[1])
            ][1]
            self.form = Form(spec.parameters, value)
        elif ident.startswith("add--"):
            self.form.add(ident.split("--")[1])
        elif ident.startswith("del--"):
            _, key, row = ident.split("--")
            self.form.remove(key, int(row))
        await self.mount_slots()

    def action_submit_form(self) -> None:
        if self.form is None or self.session.current().kind != "form":
            return
        if self.form.errors():
            self.form_errors()
            return
        self.submit(self.form.params())

    def submit(self, value: Any) -> None:
        problem = self.session.answer(value)
        if problem:
            self.query_one("#problem", Static).update(Text(f"✗ {problem}"))
            return
        if self.session.done:
            self.exit(True)
            return
        self.form = None
        self.show()

    def action_back(self) -> None:
        if self.session.back():
            self.form = None
            self.show()

    def action_quit_init(self) -> None:
        self.exit(False)


def run_app(session: Session) -> bool:
    """Run until the author chooses to write (``True``) or quits (``False``)."""
    return bool(InitApp(session).run())
