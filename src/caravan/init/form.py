"""A template's parameters as a form, built from its parameter model (FR-033, research R14).

Nothing here knows a template by name: the fields, their kinds and bounds come from the pydantic
model the template registers, so a third-party template gets a form too (Principle VII). The value
is a plain mapping; every change is validated by the model itself, and an error is reported at the
field it belongs to.
"""

from __future__ import annotations

import copy
import types
import typing
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

#: Field names whose integers are widths, scaled by the "smaller" and "larger" presets.
WIDTHS = ("hidden", "encoder", "decoder", "filters", "code", "units")


@dataclass
class Kind:
    """What one value is: ``int``, ``float``, ``bool``, ``choice``, ``extent`` or ``text``."""

    name: str
    choices: tuple[Any, ...] = ()
    optional: bool = False
    low: float | None = None
    high: float | None = None
    low_open: bool = False
    high_open: bool = False

    def describe(self) -> str:
        if self.name == "choice":
            return " | ".join(str(choice) for choice in self.choices)
        if self.name == "bool":
            return "yes | no"
        if self.name == "extent":
            return "n, or rows,columns"
        bounds = []
        if self.low is not None:
            bounds.append(f"{'>' if self.low_open else '≥'} {self.low:g}")
        if self.high is not None:
            bounds.append(f"{'<' if self.high_open else '≤'} {self.high:g}")
        text = f"{self.name} {' and '.join(bounds)}".strip()
        return f"{text}, or empty for none" if self.optional else text


@dataclass
class Slot:
    """One top-level parameter: a value, a list of values, or a list of blocks."""

    key: str
    shape: str  # "value", "values" or "blocks"
    kind: Kind | None = None
    #: For ``blocks``: the block's fields in order, each with its kind and default.
    fields: list[tuple[str, Kind, Any]] = field(default_factory=list)
    default: Any = None
    required: bool = True
    min_rows: int = 0
    max_rows: int | None = None
    optional: bool = False


def _strip(annotation: Any) -> tuple[Any, list[Any]]:
    metadata: list[Any] = []
    while typing.get_origin(annotation) is typing.Annotated:
        annotation, *extra = typing.get_args(annotation)
        metadata.extend(extra)
    return annotation, metadata


def _kind(annotation: Any, metadata: list[Any] = ()) -> Kind:  # type: ignore[assignment]
    annotation, more = _strip(annotation)
    metadata = [*metadata, *more]
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        args = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        optional = len(args) < len(typing.get_args(annotation))
        stripped = [_strip(arg)[0] for arg in args]
        if (
            len(args) == 2
            and int in stripped
            and any(typing.get_origin(a) is list for a in stripped)
        ):
            return Kind("extent", optional=optional)
        inner = _kind(args[0], metadata)
        inner.optional = optional
        return inner
    if origin is typing.Literal:
        return Kind("choice", choices=typing.get_args(annotation))
    kind = Kind(
        {bool: "bool", int: "int", float: "float"}.get(annotation, "text")  # type: ignore[arg-type]
    )
    # Read by attribute, so no import of the constraint classes' package is needed.
    for item in metadata:
        for constraint in getattr(item, "metadata", [item]):
            if getattr(constraint, "gt", None) is not None:
                kind.low, kind.low_open = float(constraint.gt), True
            elif getattr(constraint, "ge", None) is not None:
                kind.low = float(constraint.ge)
            elif getattr(constraint, "lt", None) is not None:
                kind.high, kind.high_open = float(constraint.lt), True
            elif getattr(constraint, "le", None) is not None:
                kind.high = float(constraint.le)
    return kind


def _lengths(metadata: list[Any]) -> tuple[int, int | None]:
    low, high = 0, None
    for item in metadata:
        if getattr(item, "min_length", None) is not None:
            low = int(item.min_length)
        if getattr(item, "max_length", None) is not None:
            high = int(item.max_length)
    return low, high


def slots(model: type[BaseModel]) -> list[Slot]:
    """The form's layout, from the model's fields in their order."""
    out: list[Slot] = []
    for key, info in model.model_fields.items():
        annotation = info.annotation
        default = None if info.is_required() else info.get_default(call_default_factory=True)
        bare, _ = _strip(annotation)
        optional = False
        if typing.get_origin(bare) in (typing.Union, types.UnionType):
            args = [arg for arg in typing.get_args(bare) if arg is not type(None)]
            if len(args) == 1 and typing.get_origin(_strip(args[0])[0]) is list:
                bare, optional = _strip(args[0])[0], True
        if typing.get_origin(bare) is list:
            (item,) = typing.get_args(bare)
            low, high = _lengths(list(info.metadata))
            item_bare, item_meta = _strip(item)
            if isinstance(item_bare, type) and issubclass(item_bare, BaseModel):
                fields = []
                for name, sub in item_bare.model_fields.items():
                    sub_default = None if sub.is_required() else sub.get_default()
                    fields.append((name, _kind(sub.annotation, list(sub.metadata)), sub_default))
                out.append(
                    Slot(
                        key,
                        "blocks",
                        fields=fields,
                        default=default,
                        min_rows=low,
                        max_rows=high,
                        required=info.is_required(),
                        optional=optional,
                    )
                )
            else:
                out.append(
                    Slot(
                        key,
                        "values",
                        kind=_kind(item, item_meta),
                        default=default,
                        min_rows=low,
                        max_rows=high,
                        required=info.is_required(),
                        optional=optional,
                    )
                )
            continue
        out.append(
            Slot(
                key,
                "value",
                kind=_kind(annotation, list(info.metadata)),
                default=default,
                required=info.is_required(),
            )
        )
    return out


def parse(kind: Kind, text: str) -> Any:
    """A typed value from what the author typed; ``ValueError`` names what is expected."""
    text = text.strip()
    if text == "" and kind.optional:
        return None
    try:
        if kind.name == "int":
            return int(text)
        if kind.name == "float":
            return float(text)
        if kind.name == "bool":
            if text.lower() in ("yes", "y", "true", "1", "on"):
                return True
            if text.lower() in ("no", "n", "false", "0", "off"):
                return False
            raise ValueError
        if kind.name == "choice":
            for choice in kind.choices:
                if str(choice) == text:
                    return choice
            raise ValueError
        if kind.name == "extent":
            parts = [int(part) for part in text.replace("x", ",").split(",") if part.strip()]
            if len(parts) == 1:
                return parts[0]
            if len(parts) == 2:
                return parts
            raise ValueError
    except ValueError:
        raise ValueError(f"expected {kind.describe()}") from None
    return text


def show(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ",".join(str(part) for part in value)
    return str(value)


class Form:
    """The parameters being edited: a value, its layout and its errors."""

    def __init__(self, model: type[BaseModel], value: Mapping[str, Any] | None = None) -> None:
        self.model = model
        self.slots = slots(model)
        self.value: dict[str, Any] = copy.deepcopy(dict(value or {}))
        for slot in self.slots:
            if slot.key in self.value:
                continue
            if slot.shape == "blocks" and slot.required:
                self.value[slot.key] = [
                    {name: default for name, _, default in slot.fields if default is not None}
                    for _ in range(max(slot.min_rows, 1))
                ]
            elif slot.shape == "values" and slot.required:
                self.value[slot.key] = [1] * max(slot.min_rows, 1)

    def slot(self, key: str) -> Slot:
        return next(slot for slot in self.slots if slot.key == key)

    # --- reading -------------------------------------------------------------------------------

    def get(self, key: str, row: int | None = None, name: str | None = None) -> Any:
        slot = self.slot(key)
        if slot.shape == "value":
            return self.value.get(key, slot.default)
        rows = self.value.get(key) or []
        if row is None:
            return rows
        if slot.shape == "values":
            return rows[row]
        block = rows[row]
        default = next(d for n, _, d in slot.fields if n == name)
        return block.get(name, default)

    def rows(self, key: str) -> int:
        return len(self.value.get(key) or [])

    def errors(self) -> dict[str, str]:
        """``{"blocks.2.kernel": "..."}``: each problem at the path of its field."""
        try:
            self.model.model_validate(self.value)
        except ValidationError as error:
            out: dict[str, str] = {}
            for item in error.errors():
                path = ".".join(
                    str(part)
                    for part in item["loc"]
                    if not str(part).startswith(("function-", "constrained"))
                )
                out.setdefault(path or "", item["msg"].removeprefix("Value error, "))
            return out
        return {}

    def params(self) -> dict[str, Any]:
        """What the manifest writes: what the author has, without values equal to their default.

        Taken from the form's own value rather than the model's dump, so a value the model derives
        (the autoencoder's mirrored decoder) is not written as if the author had stated it.
        """
        self.model.model_validate(self.value)
        out: dict[str, Any] = {}
        for slot in self.slots:
            if slot.key not in self.value:
                continue
            value = self.value[slot.key]
            if slot.shape == "blocks":
                defaults = {name: default for name, _, default in slot.fields}
                value = [
                    {k: v for k, v in block.items() if defaults.get(k, object()) != v}
                    for block in value
                ]
            elif value == slot.default and not slot.required:
                continue
            out[slot.key] = copy.deepcopy(value)
        return out

    # --- changing ------------------------------------------------------------------------------

    def set(self, key: str, text: str, row: int | None = None, name: str | None = None) -> None:
        """Set one value from text. ``ValueError`` when the text is not of the field's kind."""
        slot = self.slot(key)
        if slot.shape == "value":
            assert slot.kind is not None
            value = parse(slot.kind, text)
            if value is None:
                self.value.pop(key, None)
            else:
                self.value[key] = value
            return
        assert row is not None
        rows = self.value.setdefault(key, [])
        if slot.shape == "values":
            assert slot.kind is not None
            rows[row] = parse(slot.kind, text)
            return
        kind = next(k for n, k, _ in slot.fields if n == name)
        value = parse(kind, text)
        if value is None:
            rows[row].pop(name, None)
        else:
            rows[row][name] = value

    def add(self, key: str) -> bool:
        """A row like the last one; ``False`` at the model's maximum."""
        slot = self.slot(key)
        rows = self.value.setdefault(key, [])
        if slot.max_rows is not None and len(rows) >= slot.max_rows:
            return False
        if rows:
            rows.append(copy.deepcopy(rows[-1]))
        elif slot.shape == "blocks":
            rows.append({n: d for n, _, d in slot.fields if d is not None})
        else:
            rows.append(16)
        return True

    def remove(self, key: str, row: int) -> bool:
        """Drop one row; ``False`` at the model's minimum. An optional list may become empty."""
        slot = self.slot(key)
        rows = self.value.get(key) or []
        floor = 0 if slot.optional else max(slot.min_rows, 1 if slot.required else 0)
        if len(rows) <= floor or not 0 <= row < len(rows):
            return False
        del rows[row]
        if not rows and slot.optional:
            self.value.pop(key, None)
        return True


def scaled(value: Mapping[str, Any], factor: float) -> dict[str, Any]:
    """The same parameters with every width scaled, at least 1: the presets' "smaller"/"larger"."""

    def walk(key: str | None, item: Any) -> Any:
        if isinstance(item, dict):
            return {k: walk(k, v) for k, v in item.items()}
        if isinstance(item, list):
            return [walk(key, v) for v in item]
        if key in WIDTHS and isinstance(item, int) and not isinstance(item, bool):
            return max(1, round(item * factor))
        return item

    return walk(None, copy.deepcopy(dict(value)))


def presets(starter: Mapping[str, Any] | None) -> list[tuple[str, dict[str, Any]]]:
    """Where to start: the template's starter, half its widths, double its widths."""
    if starter is None:
        return []
    base = copy.deepcopy(dict(starter))
    return [
        ("as proposed", base),
        ("smaller (half the widths)", scaled(base, 0.5)),
        ("larger (double the widths)", scaled(base, 2.0)),
    ]
