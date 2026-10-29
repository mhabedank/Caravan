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
from collections.abc import Callable
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
    #: Optional: given the validated parameters and the window length, return ``None`` when the
    #: configuration fits, or ``(problem, accepted)`` describing what does not.
    #:
    #: The message rather than a boolean, because that is the value of this check — which block
    #: does not fit, how much window was left when it was reached, and what would fit instead —
    #: and the core cannot compose it: it does not know what a kernel is. Two parts because
    #: findings print in two parts, a sentence and an indented line of what is accepted. Optional
    #: because most templates have nothing to check here, and a required field would make every
    #: third-party template carry a stub (feature 005, research R6).
    window_fit: Callable[[BaseModel, int], tuple[str, tuple[str, ...]] | None] | None = None
    #: The output types this template answers (feature 010). A template's last layer is a head for
    #: these, and an autoencoder answers none of them: it reconstructs its input, which only the
    #: ``anomaly`` output knows what to do with. Checked by the manifest (CF-18), so no stage needs
    #: to know which template it is running.
    output_types: tuple[str, ...] = ("category", "binary", "number")
    #: Whether the template takes an image as its plane (feature 010, CF-19).
    takes_images: bool = False
    #: Optional, like ``window_fit``, for a template that convolves a plane of rows by columns:
    #: given the validated parameters and the two axes — either ``None`` when it is not known yet —
    #: ``None`` when the configuration fits, else ``(problem, accepted)``. Called at validation with
    #: what the manifest says and again at build with the built input's shape (feature 010, R3).
    plane_fit: (
        Callable[[BaseModel, int | None, int | None], tuple[str, tuple[str, ...]] | None] | None
    ) = None


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
        # Subpackages are skipped, and that is a layering rule rather than tidiness: a parameter
        # spec is always a module, and ``templates/builders/`` is a package whose modules import
        # the training framework. Importing it from here would pull a framework into the core on
        # every registry build — the exact failure Principle XII forbids. The layering tests prove
        # the consequence; this line is what makes it true.
        if info.ispkg or info.name.startswith("_") or info.name == "registry":
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
