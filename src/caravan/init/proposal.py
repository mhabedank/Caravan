"""The proposal: every item of the manifest at once, with how sure each is (feature 015).

``build`` turns a session into a ``Proposal`` (data-model "Proposal", "Item", "Note"); ``lines``
shows it in at most 24 lines of at most 80 characters (contracts/cli-init.md, "The proposal, as
shown"). The line mode, ``--yes`` and ``--json`` all read the same object, so they cannot disagree
about what was proposed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from caravan.init import memory
from caravan.init.profile import CERTAIN, UNCERTAIN
from caravan.init.session import FIELDS, OPTIONS, Session, flow_text
from caravan.manifest.schema.features import BUDGET_KEYS

#: The order items are shown in; the document keeps the session's order (data-model "Proposal").
SHOWN = (
    "output",
    "output_type",
    "normal_label",
    "inputs",
    "window",
    "template",
    "params",
    "quantization",
    "budget",
    "boards",
    "name",
    "file",
    "agents_md",
)

LABELS = {
    "output": "output",
    "output_type": "kind",
    "normal_label": "normal",
    "inputs": "inputs",
    "window": "window",
    "template": "template",
    "params": "params",
    "quantization": "quantize",
    "budget": "budget",
    "boards": "boards",
    "name": "name",
    "file": "file",
    "agents_md": "AGENTS.md",
}

#: Input types in the order their groups are shown; ``None`` is "left out".
TYPE_ORDER = ("number", "category", "binary", None)

#: Uncertain columns named one per line up to this many; beyond, grouped (SC-007).
SINGLE_UNCERTAIN = 4

LABEL_WIDTH = 10
VALUE_WIDTH = 22


@dataclass
class Item:
    """One entry of the proposal (data-model "Item")."""

    key: str
    field: str
    value: Any
    #: ``given``, ``answered`` or ``proposed``.
    source: str
    #: ``certain``, ``uncertain``, ``convention`` or ``open``; ``None`` unless ``proposed``.
    certainty: str | None
    reason: str
    option: str
    example: str
    column: str | None = None
    alternatives: list[Any] = field(default_factory=list)
    stale: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "column": self.column,
            "field": self.field,
            "value": self.value,
            "source": self.source,
            "certainty": self.certainty,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "option": self.option,
            "example": self.example,
            "stale": self.stale,
        }


@dataclass
class Note:
    """A finding of ``init``'s own (data-model "Note")."""

    #: ``sampled``, ``uncertain-taken``, ``exceeds-board``, ``agents-md-kept`` or ``missing``.
    kind: str
    message: str
    key: str | None = None
    column: str | None = None
    example: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "key": self.key,
            "column": self.column,
            "message": self.message,
            "example": self.example,
        }


@dataclass
class Proposal:
    dataset: dict[str, Any] | None
    items: list[Item]
    memory: list[memory.BoardMemory]
    to_ask: list[str]
    ready: bool
    notes: list[Note]
    #: Why the board figures could not be estimated yet, when boards are chosen but no estimate.
    memory_note: str = ""

    def item(self, key: str, column: str | None = None) -> Item:
        return next(i for i in self.items if i.key == key and i.column == column)


# --- building --------------------------------------------------------------------------------


def _source(session: Session, key: str, column: str | None = None) -> str:
    if column is not None:
        if column in session.given_columns or "inputs" in session.given:
            return "given"
        if column in session.answered_columns:
            return "answered"
        return "proposed"
    if key in session.given:
        return "given"
    if key in session.answered:
        return "answered"
    return "proposed"


def _field(session: Session, key: str) -> str:
    if key == "budget":
        kind = session.value("output_type") or "category"
        return f"output_features[0].{BUDGET_KEYS.get(kind, 'accuracy_drop_max')}"
    if key == "inputs":
        return "input_features"
    return FIELDS.get(key, "")


def _alternatives(session: Session, key: str, value: Any) -> list[Any]:
    if key in ("budget", "name", "file", "params", "dataset", "review"):
        return []
    values = [c.value for c in session.choices(key) if not c.disabled]
    if key == "boards":
        chosen = set(value or [])
        return [v for v in values if v not in chosen]
    return [v for v in values if v != value]


def _item(session: Session, key: str) -> Item:
    value = session.value(key)
    source = _source(session, key)
    certainty, reason = session.certainty(key)
    if source == "given":
        reason = f"given as {OPTIONS.get(key, key)}"
    elif source == "answered":
        reason = "answered"
    return Item(
        key=key,
        field=_field(session, key),
        value=value,
        source=source,
        certainty=certainty if source == "proposed" else None,
        reason=reason,
        option=OPTIONS.get(key, f"--{key.replace('_', '-')}"),
        example=session.example(key),
        alternatives=_alternatives(session, key, value),
        stale=key in session.stale,
    )


def _input_items(session: Session) -> list[Item]:
    data = session.data
    if data is None:
        return []
    output = session.value("output")
    inputs = session.value("inputs") or {}
    out = []
    for column in data.columns:
        if column.name == output:
            continue
        value = inputs.get(column.name, column.proposal)
        source = _source(session, "inputs", column.name)
        reason = column.reason
        if source == "given":
            reason = "given as --input"
        elif source == "answered":
            reason = "answered"
        out.append(
            Item(
                key="input",
                column=column.name,
                field="input_features",
                value=value,
                source=source,
                certainty=column.certainty if source == "proposed" else None,
                reason=reason,
                option="--input",
                example=session.example("inputs", column.name),
                alternatives=[a for a in column.alternatives if a != value],
                stale="inputs" in session.stale,
            )
        )
    return out


def build(session: Session) -> Proposal:
    """Everything the session would write, with certainty and source (spec FR-001, FR-002)."""
    data = session.data
    items: list[Item] = []
    order = session.keys()  # the session's question order, not a mapping
    for key in order:
        if key in ("dataset", "review"):
            continue
        if key == "inputs":
            items.extend(_input_items(session))
            continue
        items.append(_item(session, key))
    notes: list[Note] = []
    dataset = None
    if data is not None:
        dataset = {
            "path": str(session.value("dataset")),
            "rows_read": data.rows_read,
            "complete": data.complete,
        }
        if not data.complete:
            notes.append(Note("sampled", f"the proposal rests on {data.sample_note()}"))
    records: list[memory.BoardMemory] = []
    memory_note = ""
    chosen = session.value("boards") or []
    if chosen:
        try:
            estimate = session.estimate()
        except Exception as error:  # a parameter the template refuses: no figure, not a crash
            estimate, memory_note = None, f"not estimated: {error}"
        if estimate is not None:
            records = memory.board_memory(estimate, [session.boards.get(b) for b in chosen])
        elif not memory_note:
            memory_note = "not estimated yet: no inputs, template or parameters"
        for record in records:
            if record.fits:
                continue
            notes.append(
                Note(
                    "exceeds-board",
                    f"{record.board}: {_shortfall(record)}; caravan build will stop before "
                    "training",
                    key="boards",
                )
            )
    return Proposal(
        dataset=dataset,
        items=items,
        memory=records,
        to_ask=session.to_ask(),
        ready=session.ready,
        notes=notes,
        memory_note=memory_note,
    )


def _shortfall(record: memory.BoardMemory) -> str:
    parts = []
    for resource, verdict in (("flash", record.flash_verdict), ("RAM", record.ram_verdict)):
        if verdict == "exceeds":
            parts.append(f"the {resource} lower bound already exceeds the board")
        elif verdict == "unknown":
            parts.append(f"the board states no {resource} figure")
    return " and ".join(parts)


# --- showing ---------------------------------------------------------------------------------


def _cut(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _row(label: str, value: str, tail: str, width: int) -> str:
    value = _cut(value, VALUE_WIDTH)
    return _cut(f"  {label:<{LABEL_WIDTH}}  {value:<{VALUE_WIDTH}}  {tail}".rstrip(), width)


def _tail(item: Item) -> str:
    if item.stale:
        return "check again: an earlier answer changed"
    if item.source != "proposed":
        return item.source
    return f"{item.certainty}: {item.reason}" if item.reason else str(item.certainty)


def _value(item: Item, proposal: Proposal) -> str:
    value = item.value
    if item.key == "agents_md":
        return "written" if value else "not written"
    if value is None or value == []:
        return "—"
    if item.key == "window":
        return f"{value} rows"
    if item.key == "params":
        return " · ".join(f"{k} {flow_text(v)}" for k, v in value.items())
    if item.key == "budget":
        return f"{item.field.rsplit('.', 1)[-1]} {float(value):g}"
    if item.key == "boards":
        return ", ".join(value)
    return str(value)


def _type_name(kind: str | None) -> str:
    return kind or "left out"


def _input_rows(items: list[Item], width: int) -> list[str]:
    rows: list[tuple[str, str]] = []
    unsure = [i for i in items if i.source == "proposed" and i.certainty == UNCERTAIN]
    settled = [i for i in items if i not in unsure]
    groups: dict[tuple[Any, str], list[Item]] = {}
    for item in settled:
        groups.setdefault((item.value, _tail_kind(item)), []).append(item)
    for kind in TYPE_ORDER:
        for (value, tail_kind), members in groups.items():
            if value != kind:
                continue
            names = ", ".join(i.column or "" for i in members)
            if tail_kind == CERTAIN:
                count = len(members)
                tail = f"certain: {count} column{'s' if count != 1 else ''}, as the values show"
            else:
                tail = tail_kind
            rows.append((f"{_type_name(kind)}: {names}", tail))
    if len(unsure) <= SINGLE_UNCERTAIN:
        for item in unsure:
            rows.append((f"{_type_name(item.value)}: {item.column}", f"uncertain: {item.reason}"))
    else:
        for kind in TYPE_ORDER:
            members = [i for i in unsure if i.value == kind]
            if members:
                names = ", ".join(i.column or "" for i in members)
                count = len(members)
                rows.append((f"{_type_name(kind)}: {names}", f"uncertain: {count} columns"))
    return [
        _row(LABELS["inputs"] if n == 0 else "", value, tail, width)
        for n, (value, tail) in enumerate(rows)
    ]


def _tail_kind(item: Item) -> str:
    if item.stale:
        return "check again"
    if item.source != "proposed":
        return item.source
    return item.certainty or ""


def lines(proposal: Proposal, width: int = 80) -> list[str]:
    """The proposal as text: at most 24 lines of at most ``width`` characters (SC-007)."""
    out: list[str] = []
    if proposal.dataset is not None:
        rows = proposal.dataset["rows_read"]
        note = (
            f"all {rows:,} rows read"
            if proposal.dataset["complete"]
            else f"the first {rows:,} rows sampled"
        )
        out.append(_cut(f"caravan init — proposal from {proposal.dataset['path']}, {note}", width))
        out.append("")
    by_key: dict[str, list[Item]] = {}
    for item in proposal.items:
        by_key.setdefault("inputs" if item.key == "input" else item.key, []).append(item)
    for key in SHOWN:
        if key not in by_key:
            continue
        if key == "inputs":
            out.extend(_input_rows(by_key[key], width))
            continue
        item = by_key[key][0]
        out.append(_row(LABELS[key], _value(item, proposal), _tail(item), width))
        if key == "boards" and (proposal.memory or proposal.memory_note):
            out.extend(_memory_rows(proposal, width))
    return out


def _memory_rows(proposal: Proposal, width: int) -> list[str]:
    if not proposal.memory:
        return [_cut(f"  {'memory':<{LABEL_WIDTH}}  {proposal.memory_note}", width)]
    rows = [
        _cut(f"  {'memory' if n == 0 else '':<{LABEL_WIDTH}}  {memory.line(record)}", width)
        for n, record in enumerate(proposal.memory)
    ]
    rows.append(_cut(f"  {'':<{LABEL_WIDTH}}  {memory.SHORT_LABEL}", width))
    return rows
