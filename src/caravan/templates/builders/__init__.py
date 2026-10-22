"""The builder half of a template — the half that needs a training framework.

A template is two things (research R7 of feature 001). The parameter spec lives in
``caravan/templates/`` and is core: it validates what the manifest wrote. The builder lives here
and constructs an actual model, which needs the framework Principle XII keeps out of the core.

Nothing here imports a framework. A builder module does, and it is imported by name only when a
stage asks for it — which is why this package is skipped by the core's template discovery walk.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

#: What a builder is: parameters, the input shape and the labels in, a model out. The return type
#: is deliberately untyped here — naming the framework's model class would mean importing it.
Builder = Callable[..., Any]

ENTRY_POINT_GROUP = "caravan.template_builders"


class UnknownBuilder(Exception):
    """No builder is registered for this template identifier."""


def builtin_identifiers() -> tuple[str, ...]:
    """The builders this build ships, by module name, without importing any of them."""
    package = importlib.import_module(__package__)
    return tuple(
        sorted(
            info.name
            for info in pkgutil.iter_modules(package.__path__)
            if not info.ispkg and not info.name.startswith("_")
        )
    )


def third_party_identifiers() -> tuple[str, ...]:
    return tuple(sorted(entry.name for entry in entry_points(group=ENTRY_POINT_GROUP)))


def known_identifiers() -> tuple[str, ...]:
    return tuple(sorted(set(builtin_identifiers()) | set(third_party_identifiers())))


def load_builder(identifier: str) -> Builder:
    """The builder for a template, imported now and not before.

    Adding a template must not require editing a central list (FR-021 of feature 001), so this
    looks for a module of that name first and an entry point second. Both are discovery, neither
    is an enumeration.
    """
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        if entry.name == identifier:
            return entry.load()

    if identifier in builtin_identifiers():
        module = importlib.import_module(f"{__package__}.{identifier}")
        builder = getattr(module, "build", None)
        if builder is None:
            raise UnknownBuilder(f"the builder module for {identifier!r} defines no build function")
        return builder

    known = known_identifiers()
    raise UnknownBuilder(
        f"no builder is registered for template {identifier!r}; "
        f"known builders: {', '.join(known) if known else 'none'}"
    )
