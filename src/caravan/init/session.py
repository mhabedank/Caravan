"""The question engine of ``caravan init`` (features 013 and 015).

A session holds the answers so far and knows, for every item, its choices, its proposal with the
reason and the certainty of the rule that made it, whether an answer is acceptable, and what to
show beside it (``explain``). The line mode and ``--yes`` only ask it and show what it says, so
both write the same file. Answers given as options are never asked.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from caravan.init import drawing, memory, windows
from caravan.init.form import Form
from caravan.init.profile import (
    NORMAL,
    DataProfile,
    ProfileError,
    output_types,
    profile,
    proposed_output,
    read_column,
)
from caravan.manifest._yaml import DocumentError, dump_commented, flow
from caravan.manifest.schema.export import MINIMUM_REPRESENTATIVE_SAMPLES
from caravan.manifest.schema.features import BUDGET_KEYS, NAME_PATTERN
from caravan.manifest.schema.model import NAME_PATTERN as MODEL_NAME_PATTERN
from caravan.manifest.version import SCHEMA_VERSION
from caravan.targets.registry import BoardRegistry
from caravan.targets.registry import default_registry as default_boards
from caravan.templates.registry import TemplateParameterSpec, TemplateRegistry
from caravan.templates.registry import default_registry as default_templates

#: The questions, in the order FR-027 fixes.
ORDER = (
    "dataset",
    "boards",
    "quantization",
    "output",
    "output_type",
    "normal_label",
    "inputs",
    "window",
    "template",
    "params",
    "budget",
    "name",
    "file",
    "review",
)

TITLES = {
    "dataset": "Where is the data?",
    "boards": "Which boards must the model run on?",
    "quantization": "How are the weights stored?",
    "output": "Which column should the model predict?",
    "output_type": "What kind of answer is it?",
    "normal_label": "Which value means normal?",
    "inputs": "Which columns may the model read, and as what?",
    "window": "How many rows go into each prediction?",
    "template": "Which kind of network?",
    "params": "How large is the network?",
    "budget": "How much may int8 cost?",
    "name": "What is the model called?",
    "file": "Where is the manifest written?",
    "review": "Write the manifest?",
}

FIELDS = {
    "dataset": "dataset",
    "boards": "export.targets",
    "quantization": "export.quantization",
    "output": "output_features[0].name",
    "output_type": "output_features[0].type",
    "normal_label": "output_features[0].preprocessing.normal_label",
    "inputs": "input_features",
    "window": "preprocessing.window_size",
    "template": "model.template",
    "params": "model.params",
    "budget": "output_features[0].<budget>",
    "name": "model.name",
    "file": "",
    "review": "",
}

#: The command-line option that answers each question (contracts/cli-init.md).
OPTIONS = {
    "dataset": "--dataset",
    "boards": "--board",
    "quantization": "--quantization",
    "output": "--output",
    "output_type": "--output-type",
    "normal_label": "--normal-label",
    "inputs": "--input",
    "window": "--window",
    "template": "--template",
    "params": "--params",
    "budget": "--budget",
    "name": "--name",
    "file": "<manifest>",
}

OUTPUT_MEANING = {
    "category": "one of several classes",
    "binary": "one of two values, as a probability",
    "number": "a number, in the column's own unit",
    "anomaly": "how unusual a window is, learned from normal data only",
}

BUDGET_HELP = {
    "accuracy_drop_max": (
        "The accuracy int8 may lose against the float model on the test part, as a fraction "
        "(0.02 = two points). Above it, the export stops."
    ),
    "mae_increase_max": (
        "How much int8 may raise the mean absolute error on the test part, in the column's unit. "
        "Above it, the export stops."
    ),
    "auc_drop_max": (
        "The area under the ROC curve int8 may lose against the float model on the test part. "
        "Above it, the export stops."
    ),
}
BUDGET_PROPOSALS = {
    "accuracy_drop_max": (0.02, "the value examples/picket-mlp.yaml uses, not a recommendation"),
    "auc_drop_max": (
        0.05,
        "the value examples/anomaly-autoencoder.yaml uses, not a recommendation",
    ),
}

QUANTIZATIONS = (
    (
        "int8",
        "int8",
        "weights and activations in 8 bits: 4 times smaller, accelerated on the boards",
    ),
    ("none", "none", "float32 as trained: for comparison; 4 times the flash, no acceleration"),
)


@dataclass
class Choice:
    value: Any
    label: str
    detail: str = ""
    #: Why it cannot be chosen now; empty when it can.
    disabled: str = ""


@dataclass
class Section:
    title: str
    lines: list[str]


@dataclass
class Question:
    key: str
    title: str
    field: str
    help: str
    #: ``one``, ``many``, ``columns``, ``number``, ``text``, ``form`` or ``review``.
    kind: str
    choices: list[Choice] = field(default_factory=list)
    proposal: Any = None
    reason: str = ""
    option: str = ""


class Aborted(Exception):
    """The author stopped the session; nothing is written."""


@dataclass
class Written:
    path: Path
    text: str


class Session:
    """Answers so far, and what each question offers given them."""

    def __init__(
        self,
        given: Mapping[str, Any] | None = None,
        *,
        cwd: Path | None = None,
        overwrite: bool = False,
        templates: TemplateRegistry | None = None,
        boards: BoardRegistry | None = None,
    ) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()
        self.overwrite = overwrite
        self.templates = templates or default_templates()
        self.boards = boards or default_boards()
        self.answers: dict[str, Any] = {}
        self.given: set[str] = set()
        #: Answers that no longer fit an earlier one: kept, marked to check again (FR-035).
        self.stale: set[str] = set()
        self.data: DataProfile | None = None
        self._labels: tuple[list[str], list[tuple[str, int]]] | None = None
        self._windows: dict[tuple[str, str, tuple[int, ...]], windows.WindowTable] = {}
        self.position = 0
        for key, value in (given or {}).items():
            if value is None:
                continue
            problem = self.accept(key, value)
            if problem:
                raise ValueError(f"{OPTIONS.get(key, key)}: {problem}")
            self.given.add(key)

    # --- the order -----------------------------------------------------------------------------

    def keys(self) -> list[str]:
        """The questions that apply now, in order."""
        out = []
        for key in ORDER:
            if key == "normal_label" and not self._needs_normal_label():
                continue
            if key == "window" and not self._consumes_window():
                continue
            out.append(key)
        return out

    def asked(self) -> list[str]:
        """The questions a person is asked: those not answered by an option."""
        return [key for key in self.keys() if key not in self.given]

    def current(self) -> Question:
        keys = self.asked()
        self.position = min(self.position, len(keys) - 1)
        return self.question(keys[self.position])

    def back(self) -> bool:
        if self.position == 0:
            return False
        self.position -= 1
        return True

    def go(self, key: str) -> None:
        self.position = self.asked().index(key)

    @property
    def done(self) -> bool:
        return self.answers.get("review") == "write"

    # --- values ---------------------------------------------------------------------------------

    def value(self, key: str) -> Any:
        """The answer, or the proposal where there is none yet."""
        if key in self.answers:
            return self.answers[key]
        return self.proposal(key)[0]

    def _needs_normal_label(self) -> bool:
        if self.value("output_type") != "anomaly" or self.data is None:
            return False
        output = self.value("output")
        if output not in self.data.names:
            return False
        return NORMAL not in self.data.column(output).distinct

    def _spec(self) -> TemplateParameterSpec | None:
        template = self.value("template")
        return self.templates.get(template) if template else None

    def _consumes_window(self) -> bool:
        spec = self._spec()
        return spec is None or spec.consumes_window

    def features(self) -> list[memory.Feature]:
        inputs = self.value("inputs") or {}
        out = []
        for name, kind in inputs.items():
            if kind is None:
                continue
            vocabulary = self.data.column(name).values if self.data and kind == "category" else 0
            out.append(memory.Feature(name, kind, vocabulary))
        return out

    def classes(self) -> int:
        output = self.value("output")
        if self.data is None or output not in self.data.names:
            return 2
        return self.data.column(output).values

    # --- proposals ------------------------------------------------------------------------------

    def proposal(self, key: str) -> tuple[Any, str]:
        """The proposed answer and the reason shown with it; ``(None, "")`` when there is none."""
        data = self.data
        if key == "quantization":
            return "int8", "accelerated on every registered board"
        if key == "output" and data is not None:
            name = proposed_output(data)
            return (name, "a column named like an answer") if name else (None, "")
        if key == "output_type" and data is not None:
            output = self.value("output")
            if output in data.names:
                offered = output_types(data.column(output))
                if offered:
                    return offered[0], data.column(output).summary()
        if key == "inputs" and data is not None:
            output = self.value("output")
            return (
                {c.name: c.proposal for c in data.columns if c.name != output},
                "every column but the output, as its values suggest",
            )
        if key == "window":
            table = self.window_table()
            if table is not None and table.proposal is not None:
                return table.proposal, table.reason
            spec = self._spec()
            if spec is not None and spec.starter is not None and spec.starter.window:
                return spec.starter.window, "the template's own starting window"
        if key == "template":
            offered = [c for c in self.choices("template") if not c.disabled]
            if offered:
                return offered[0].value, "the first that answers this output"
        if key == "params":
            spec = self._spec()
            if spec is not None and spec.starter is not None:
                return Form(spec.parameters, spec.starter.params).params(), spec.starter.note
        if key == "budget":
            budget_key = BUDGET_KEYS.get(self.value("output_type") or "category", "")
            proposed = BUDGET_PROPOSALS.get(budget_key)
            if proposed:
                return proposed
        if key == "name" and data is not None:
            base = re.sub(r"[^a-z0-9-]+", "-", f"{data.root.name}-{self.value('template')}".lower())
            base = base.strip("-") or "model"
            return (
                base if len(base) >= 3 else f"{base}-model"
            ), "the data's directory and template"
        if key == "file":
            name = self.value("name") or "model"
            return f"{name}.yaml", "the model's name, in the current directory"
        if key == "review":
            return "write", ""
        return None, ""

    # --- choices --------------------------------------------------------------------------------

    def choices(self, key: str) -> list[Choice]:
        data = self.data
        if key == "boards":
            return [
                Choice(
                    board.board,
                    board.board,
                    f"RAM {board.ram_kb:g} KB · flash {board.flash_kb:g} KB · {board.core} "
                    f"{board.clock_mhz:g} MHz",
                )
                for board in self.boards
            ]
        if key == "quantization":
            return [Choice(value, label, detail) for value, label, detail in QUANTIZATIONS]
        if key == "output" and data is not None:
            out = []
            for column in data.columns:
                problem = ""
                if not NAME_PATTERN.match(column.name):
                    problem = "the name cannot name a feature"
                elif not output_types(column):
                    problem = "one value only"
                out.append(Choice(column.name, column.name, column.summary(), problem))
            return out
        if key == "output_type" and data is not None:
            output = self.value("output")
            if output not in data.names:
                return []
            return [
                Choice(kind, kind, OUTPUT_MEANING[kind])
                for kind in output_types(data.column(output))
            ]
        if key == "normal_label" and data is not None:
            output = self.value("output")
            return [Choice(value, value) for value in data.column(output).distinct]
        if key == "window":
            table = self.window_table()
            if table is None:
                return []
            out = []
            for row in table.rows:
                if row.refused:
                    out.append(Choice(row.size, f"{row.size} rows", "", row.refused))
                    continue
                per_class = ", ".join(
                    f"{name} {count}" if name else f"{count}" for name, count in row.test.items()
                )
                out.append(
                    Choice(
                        row.size,
                        f"{row.size} rows",
                        f"test windows: {per_class} · lost {row.lost_share:.0%}",
                        "" if row.kept else "no windows",
                    )
                )
            return out
        if key == "template":
            kind = self.value("output_type")
            # The answered window only: the window's proposal itself depends on the template.
            window = self.answers.get("window")
            out = []
            for spec in self.templates:
                if kind not in spec.output_types:
                    continue
                note = spec.starter.note if spec.starter else spec.summary
                problem = ""
                if spec.starter is not None and window and spec.window_fit is not None:
                    fit = spec.window_fit(
                        spec.parameters.model_validate(dict(spec.starter.params)), window
                    )
                    if fit is not None:
                        problem = f"its starting parameters need a longer window: {fit[1][-1]}"
                out.append(Choice(spec.identifier, spec.identifier, note, problem))
            rank = {s.identifier: (s.starter.rank if s.starter else 99) for s in self.templates}
            out.sort(key=lambda c: (bool(c.disabled), rank[c.value], c.value))
            return out
        if key == "review":
            target = self.value("file")
            out = [Choice("write", f"write {target}", "then check it as caravan validate does")]
            for other in self.asked():
                if other == "review":
                    continue
                out.append(Choice(other, other.replace("_", " "), self.describe(other)))
            return out
        return []

    def describe(self, key: str) -> str:
        """An answer in a few words, for the list of answers and the review."""
        value = self.value(key)
        if value is None:
            return "—"
        if key == "inputs":
            used = [f"{name}:{kind}" for name, kind in value.items() if kind]
            return ", ".join(used)
        if key == "boards":
            return ", ".join(value)
        if key == "params":
            return " · ".join(f"{k} {v}" for k, v in value.items())
        return str(value)

    # --- the question ---------------------------------------------------------------------------

    def question(self, key: str) -> Question:
        proposal, reason = self.proposal(key)
        if key in self.answers:
            proposal = self.answers[key]
        kind = {
            "dataset": "text",
            "boards": "many",
            "inputs": "columns",
            "params": "form",
            "budget": "number",
            "name": "text",
            "file": "text",
            "review": "review",
        }.get(key, "one")
        field = FIELDS[key]
        if key == "budget":
            field = f"output_features[0].{BUDGET_KEYS.get(self.value('output_type') or 'category')}"
        return Question(
            key=key,
            title=TITLES[key],
            field=field,
            help=self.help(key),
            kind=kind,
            choices=self.choices(key),
            proposal=proposal,
            reason=reason,
            option=OPTIONS.get(key, ""),
        )

    def help(self, key: str) -> str:
        if key == "dataset":
            return "A directory of .csv, .tsv or .txt files with a header row, or one such file."
        if key == "boards":
            return "Every board the model must fit. Nothing is proposed: you know your hardware."
        if key == "quantization":
            return "int8 is what the boards accelerate; none keeps float32 to compare against."
        if key == "output":
            return "The column whose value the model answers. It is never also an input."
        if key == "output_type":
            return "Only the kinds this column's values allow are offered."
        if key == "normal_label":
            return "An anomaly model learns from normal windows only; which value marks them?"
        if key == "inputs":
            return "Each column becomes one input of the type chosen, or is left out."
        if key == "window":
            return (
                "The model does not judge one row on its own: it takes this many consecutive "
                "rows, makes one prediction, then takes the next rows. Windows never span two "
                "recordings."
            )
        if key == "template":
            return "Only templates that answer this kind of output are offered."
        if key == "params":
            return "Start from a preset and change any value; the drawing and memory follow."
        if key == "budget":
            return BUDGET_HELP[
                BUDGET_KEYS.get(self.value("output_type") or "category", "accuracy_drop_max")
            ]
        if key == "name":
            return "Lower case letters, digits and -, at least 3 characters."
        if key == "file":
            return "The manifest is a new file; an existing one is never changed without asking."
        return "Nothing is written until you choose to write."

    # --- answering ------------------------------------------------------------------------------

    def answer(self, value: Any) -> str | None:
        """Answer the current question; ``None`` and on to the next, or the problem."""
        key = self.asked()[self.position]
        if key == "review" and value != "write" and value in self.asked():
            self.go(value)
            return None
        problem = self.accept(key, value)
        if problem:
            return problem
        if key != "review":
            self.position = min(self.position + 1, len(self.asked()) - 1)
        return None

    def accept(self, key: str, value: Any) -> str | None:
        """Check and store one answer; later answers that no longer fit are marked (FR-035)."""
        problem = self.check(key, value)
        if problem:
            return problem
        if key == "dataset":
            value = str(value)
        if key == "params" and isinstance(value, Form):
            value = value.params()
        changed = self.answers.get(key) != value
        self.answers[key] = value
        self.stale.discard(key)
        if changed:
            if key in ("output", "dataset"):
                self._labels = None
            later = ORDER[ORDER.index(key) + 1 :]
            for other in later:
                kept = other in self.answers and other not in self.given and other != "review"
                if kept and self.check(other, self.answers[other]):
                    self.stale.add(other)
            # Parameters of another template mean nothing here: start from its starter.
            replaced = key == "template" and "params" in self.answers and "params" not in self.given
            if replaced and self.check("params", self.answers["params"]):
                del self.answers["params"]
                self.stale.discard("params")
        if key != "review":
            self.answers.pop("review", None)
        return None

    def check(self, key: str, value: Any) -> str | None:
        """Why ``value`` cannot answer ``key``, or ``None``."""
        if key == "dataset":
            path = Path(value).expanduser()
            path = path if path.is_absolute() else self.cwd / path
            try:
                self.data = profile(path)
            except ProfileError as error:
                return str(error)
            if not any(c.proposal for c in self.data.columns) and len(self.data.columns) < 2:
                return "the data has no column a model could read"
            images = [c.name for c in self.data.columns if c.image_like]
            if images and len(self.data.columns) <= 2:
                return (
                    f"the column {images[0]} names image files: init does not set up image "
                    "inputs yet; see docs/ref/manifest/input-features.md"
                )
            return None
        if self.data is None and key in ("output", "output_type", "inputs", "normal_label"):
            return "answer the data first"
        if key == "boards":
            if isinstance(value, str):
                value = [value]
            if not value:
                return "choose at least one board"
            unknown = [board for board in value if self.boards.get(board) is None]
            if unknown:
                return (
                    f"unknown board {unknown[0]}; registered: {', '.join(self.boards.identifiers)}"
                )
            if len(set(value)) != len(value):
                return "a board is named twice"
            return None
        if key == "quantization":
            return None if value in ("int8", "none") else "int8 or none"
        if key == "output":
            choice = next((c for c in self.choices("output") if c.value == value), None)
            if choice is None:
                return f"no column {value!r} in the data; columns: {', '.join(self.data.names)}"
            return choice.disabled or None
        if key == "output_type":
            offered = [c.value for c in self.choices("output_type")]
            return None if value in offered else f"this column allows {', '.join(offered)}"
        if key == "normal_label":
            return (
                None
                if value in self.data.column(self.value("output")).distinct
                else "not a value of the column"
            )
        if key == "inputs":
            output = self.value("output")
            if not isinstance(value, Mapping):
                return "a mapping of column to type"
            for name, kind in value.items():
                if name not in self.data.names:
                    return f"no column {name!r} in the data"
                if name == output and kind:
                    return f"{name} is the output, so it cannot also be an input"
                if kind not in (None, "number", "category", "binary"):
                    return f"{name}: number, category, binary, or left out"
                if kind and not NAME_PATTERN.match(name):
                    return f"{name}: the name cannot name a feature"
            if not any(value.values()):
                return "choose at least one input"
            return None
        if key == "window":
            try:
                window = int(value)
            except (TypeError, ValueError):
                return "a whole number of rows"
            if window < 1:
                return "at least one row"
            return self._fits(self.value("template"), self.value("params"), window)
        if key == "template":
            spec = self.templates.get(value)
            if spec is None:
                return f"unknown template; registered: {', '.join(self.templates.identifiers)}"
            if self.value("output_type") not in spec.output_types:
                answering = [
                    s.identifier
                    for s in self.templates
                    if self.value("output_type") in s.output_types
                ]
                return (
                    f"{value} does not answer a {self.value('output_type')} output; "
                    f"{', '.join(answering)} does"
                )
            return None
        if key == "params":
            spec = self._spec()
            if spec is None:
                return "choose the template first"
            params = value.params() if isinstance(value, Form) else value
            try:
                spec.parameters.model_validate(dict(params))
            except ValidationError as error:
                first = error.errors()[0]
                where = ".".join(str(p) for p in first.get("loc", ()))
                message = str(first["msg"]).removeprefix("Value error, ")
                return f"{where}: {message}" if where else message
            return self._fits(spec.identifier, params, self.value("window"))
        if key == "budget":
            try:
                budget = float(value)
            except (TypeError, ValueError):
                return "a number"
            budget_key = BUDGET_KEYS.get(self.value("output_type") or "category")
            if budget < 0 or (budget_key != "mae_increase_max" and budget > 1):
                return "between 0 and 1" if budget_key != "mae_increase_max" else "0 or more"
            return None
        if key == "name":
            text = str(value)
            if len(text) < 3 or not MODEL_NAME_PATTERN.match(text):
                return (
                    "lower case letters, digits and -, at least 3 characters, starting with a "
                    "letter or digit"
                )
            return None
        if key == "file":
            text = str(value).removesuffix("!")
            path = self._path(text)
            if not path.parent.is_dir():
                return f"no directory {path.parent}"
            if path.exists() and not (self.overwrite or str(value).endswith("!")):
                return f"{text} exists; choose another name, or end it with ! to replace it"
            return None
        if key == "review":
            return None
        return f"unknown question {key}"

    def _fits(self, template: str | None, params: Any, window: int | None) -> str | None:
        spec = self.templates.get(template) if template else None
        if spec is None or params is None or window is None or spec.window_fit is None:
            return None
        try:
            model = spec.parameters.model_validate(dict(params))
        except Exception:
            return None
        fit = spec.window_fit(model, int(window))
        return f"{fit[0]}; would fit: {', '.join(fit[1])}" if fit else None

    # --- what goes beside the question ----------------------------------------------------------

    def window_table(self) -> windows.WindowTable | None:
        data = self.data
        output = self.value("output")
        kind = self.value("output_type")
        if data is None or output not in data.names or not kind:
            return None
        if self._labels is None:
            self._labels = read_column(data, output)
        labels, files = self._labels
        spec = self._spec() or next(
            (s for s in self.templates if kind in s.output_types and s.starter), None
        )
        extra = (
            (spec.starter.window,)
            if spec is not None and spec.starter and spec.starter.window
            else ()
        )
        # Once the template is chosen, a size its parameters do not fit is not offered.
        template = self.answers.get("template")
        params = self.answers.get("params") or self.proposal("params")[0] if template else None
        fits = None
        if template:

            def fits(size: int) -> str | None:
                problem = self._fits(template, params, size)
                return "too short for the template's parameters" if problem else None

        cache = (output, kind, extra, template, repr(params))
        if cache not in self._windows:
            self._windows[cache] = windows.table(labels, files, kind, extra=extra, fits=fits)
        return self._windows[cache]

    def estimate(self) -> memory.Estimate | None:
        spec = self._spec()
        params = self.value("params")
        boards = [self.boards.get(b) for b in (self.value("boards") or [])]
        if spec is None or params is None or not boards or not self.features():
            return None
        return memory.estimate(
            self.features(),
            self.value("window") if spec.consumes_window else None,
            spec,
            params,
            self.value("output_type") or "category",
            self.classes(),
            self.value("quantization") or "int8",
            boards,
        )

    def explain(self, key: str | None = None) -> list[Section]:
        """What the side panel shows for a question (FR-030 to FR-032)."""
        key = key or self.asked()[self.position]
        data = self.data
        out: list[Section] = []
        if key in ("output", "output_type", "inputs", "normal_label") and data is not None:
            lines = [f"{data.sample_note()} from {len(data.files)} file(s)"]
            inputs = self.value("inputs") or {}
            for column in data.columns:
                role = (
                    "output"
                    if column.name == self.value("output")
                    else (inputs.get(column.name) or "left out")
                )
                lines.append(f"{column.name:<14} {role:<9} {column.reason}")
            out.append(Section("the columns", lines))
        if key == "boards":
            out.append(
                Section(
                    "the registered boards",
                    [
                        f"{b.board:<10} RAM {b.ram_kb:>6g} KB  flash {b.flash_kb:>6g} KB  "
                        f"{b.core}, {b.accel}  [{b.sources.get('ram_kb', '')}]"
                        for b in self.boards
                    ],
                )
            )
        if key == "window":
            table = self.window_table()
            if table is not None:
                lines = [
                    "rows  "
                    + "  ".join(f"{c or 'windows':>8}" for c in table.classes)
                    + "     lost"
                ]
                for row in table.rows:
                    mark = ">" if row.size == self.value("window") else " "
                    if row.refused:
                        lines.append(f"{mark}{row.size:>4}  {row.refused[:60]}")
                        continue
                    counts = "  ".join(f"{row.test.get(c, 0):>8}" for c in table.classes)
                    lines.append(f"{mark}{row.size:>4}  {counts}  {row.lost_share:>6.0%}")
                lines.append(
                    f"test windows per class, split by {table.rows[0].split or 'block'}; "
                    "lost = labels differ inside"
                )
                lines.append(f"proposed {table.proposal}: {table.reason}")
                out.append(Section("what your data allows", lines))
                labels, _ = self._labels or ([], [])
                size = self.value("window") or table.proposal or 8
                out.append(
                    Section(
                        f"your data cut into windows of {size}",
                        windows.strip(
                            labels, int(size), number=self.value("output_type") == "number"
                        ),
                    )
                )
        if key in ("template", "params", "window") and self.features():
            spec = self._spec()
            params = self.value("params")
            if spec is not None and params is not None:
                out.append(
                    Section(
                        f"the network ({spec.identifier})",
                        drawing.draw(
                            self.features(),
                            self.value("window") if spec.consumes_window else None,
                            spec,
                            params,
                            self.value("output_type") or "category",
                            self.classes(),
                        ),
                    )
                )
        if key in ("quantization", "window", "template", "params", "review"):
            estimate = self.estimate()
            if estimate is not None:
                boards = [self.boards.get(b) for b in self.value("boards")]
                out.append(Section("memory on your boards", memory.panel(estimate, boards)))
        if key == "budget":
            out.append(Section("what it gates", [self.help("budget")]))
        if key in ("review", "name", "file"):
            try:
                out.append(Section("the file", self.document().splitlines()))
            except Exception as error:  # an answer is still missing
                out.append(Section("the file", [f"not complete yet: {error}"]))
        return out

    # --- writing --------------------------------------------------------------------------------

    def missing(self) -> list[str]:
        """Questions with neither an answer nor a proposal."""
        return [k for k in self.keys() if k != "review" and self.value(k) is None]

    def fill(self) -> list[str]:
        """Take every proposal (``--no-input``); returns the questions left without an answer."""
        for key in self.keys():
            if key == "review" or key in self.answers:
                continue
            proposal = self.value(key)
            if proposal is None:
                continue
            problem = self.accept(key, proposal)
            if problem:
                return [f"{key}: {problem}"]
        return self.missing()

    def _path(self, text: str) -> Path:
        path = Path(text).expanduser()
        return path if path.is_absolute() else self.cwd / path

    def _relative(self, path: Path) -> str:
        path = path if path.is_absolute() else self.cwd / path
        target = self._path(str(self.value("file") or "x.yaml").removesuffix("!")).parent
        return os.path.relpath(path.resolve(), target.resolve())

    def document(self) -> str:
        """The manifest these answers make (contracts/manifest-output.md)."""
        data = self.data
        if data is None:
            raise ValueError("no data yet")
        spec = self._spec()
        assert spec is not None
        output = self.value("output")
        kind = self.value("output_type")
        inputs = self.value("inputs") or {}
        dataset = self._relative(Path(self.value("dataset")))
        output_feature: dict[str, Any] = {"name": output, "type": kind}
        if kind == "anomaly" and self._needs_normal_label():
            output_feature["preprocessing"] = flow({"normal_label": self.value("normal_label")})
        output_feature[BUDGET_KEYS[kind]] = float(self.value("budget"))
        params = {
            key: flow(value)
            if isinstance(value, list) and all(not isinstance(v, dict) for v in value)
            else [flow(v) for v in value]
            if isinstance(value, list)
            else value
            for key, value in (self.value("params") or {}).items()
        }
        export: dict[str, Any] = {}
        if self.value("quantization") != "int8":
            export["quantization"] = self.value("quantization")
        export["targets"] = flow(list(self.value("boards")))
        if self.value("quantization") == "int8":
            export["representative_samples"] = MINIMUM_REPRESENTATIVE_SAMPLES
        left_out = [c for c in data.columns if c.name != output and not inputs.get(c.name)]
        input_comments = ["The columns the model reads, one feature each."]
        input_comments += [f"left out: {c.name} ({c.reason})" for c in left_out]
        sections: list[tuple[str, Any, list[str]]] = [
            ("apiVersion", SCHEMA_VERSION, []),
            (
                "model",
                {
                    "name": self.value("name"),
                    "version": "0.1.0",
                    "template": spec.identifier,
                    "params": params,
                },
                ["What is built, and from which template."],
            ),
            (
                "input_features",
                [flow({"name": name, "type": t}) for name, t in inputs.items() if t],
                input_comments,
            ),
            (
                "output_features",
                [output_feature],
                ["The column the model predicts, and what int8 may cost it."],
            ),
        ]
        if spec.consumes_window:
            sections.append(
                (
                    "preprocessing",
                    {"window_size": int(self.value("window"))},
                    ["How many rows form one window."],
                )
            )
        sections += [
            ("dataset", dataset, ["The data, relative to this file."]),
            ("export", export, ["The boards it must fit, and how the weights are stored."]),
        ]
        header = [
            f"Set up by caravan init from {dataset}.",
            "Every field: docs/ref/manifest/index.md",
            "Every resolved value: caravan render <this file>",
        ]
        return dump_commented(sections, header)

    def write(self) -> tuple[Path, list[Any]]:
        """Write to a temporary file, validate it as ``caravan validate`` does, then move it."""
        from caravan.manifest.load import load_manifest

        text = self.document()
        target = self._path(str(self.value("file")).removesuffix("!"))
        handle, temporary = tempfile.mkstemp(
            prefix=".caravan-init-", suffix=".yaml", dir=target.parent
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(text)
            # Validated where it will live, so the dataset path resolves as it will.
            outcome = load_manifest(Path(temporary))
            if outcome.findings:
                return target, outcome.findings
            os.replace(temporary, target)
            return target, []
        except DocumentError:
            raise
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
