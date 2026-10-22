"""The template registry — the core half of a template.

A template is two things (research R7). The **parameter spec** lives here: an identifier, a typed
parameter model that validates itself, and the dataset requirement it declares. The **builder**,
which constructs an actual model, lives in the training extra and is never imported by the core —
building needs a training framework, and Principle XII keeps that out of the core.

Adding a template must not require editing a central list (FR-021), so built-ins are discovered
by walking this package and third-party templates by the ``caravan.templates`` entry point group.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import entry_points

from pydantic import BaseModel


@dataclass(frozen=True)
class TemplateParameterSpec:
    """What the core knows about a template, without knowing how to build one."""

    identifier: str
    parameters: type[BaseModel]
    consumes_window: bool
    summary: str


class TemplateRegistry:
    """Identifier to parameter spec. An instance, so a test can build its own."""

    def __init__(self) -> None:
        self._specs: dict[str, TemplateParameterSpec] = {}

    def register(self, spec: TemplateParameterSpec) -> None:
        if spec.identifier in self._specs:
            raise ValueError(f"a template is already registered as {spec.identifier!r}")
        self._specs[spec.identifier] = spec

    def get(self, identifier: str) -> TemplateParameterSpec | None:
        return self._specs.get(identifier)

    @property
    def identifiers(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self):
        return iter(self._specs[name] for name in self.identifiers)


def _discover_builtin(registry: TemplateRegistry) -> None:
    package = importlib.import_module(__package__)
    for info in pkgutil.iter_modules(package.__path__):
        if info.name.startswith("_") or info.name == "registry":
            continue
        module = importlib.import_module(f"{__package__}.{info.name}")
        spec = getattr(module, "SPEC", None)
        if isinstance(spec, TemplateParameterSpec):
            registry.register(spec)


def _discover_third_party(registry: TemplateRegistry) -> None:
    for entry in entry_points(group="caravan.templates"):
        spec = entry.load()
        if callable(spec) and not isinstance(spec, TemplateParameterSpec):
            spec = spec()
        if isinstance(spec, TemplateParameterSpec):
            registry.register(spec)


def build_registry() -> TemplateRegistry:
    registry = TemplateRegistry()
    _discover_builtin(registry)
    _discover_third_party(registry)
    return registry


@lru_cache(maxsize=1)
def default_registry() -> TemplateRegistry:
    """The registry this build ships, discovered once."""
    return build_registry()
