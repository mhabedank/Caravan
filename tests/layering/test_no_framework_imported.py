"""Level 1 of the layering rule: nothing in the core loads a training framework.

Principle XII. Checking and resolving a manifest does not need a machine-learning framework, so
the core must not reach one — and that has to be a property the build enforces, not a convention
somebody remembers.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys

import caravan

FRAMEWORKS = (
    "tensorflow",
    "tensorflow_lite",
    "ai_edge_litert",
    "torch",
    "jax",
    "keras",
    "sklearn",
    "onnx",
    "onnxruntime",
    "numpy",
)


def core_module_names() -> list[str]:
    names = [caravan.__name__]
    for info in pkgutil.walk_packages(caravan.__path__, prefix="caravan."):
        names.append(info.name)
    return names


def test_importing_the_whole_core_loads_no_framework() -> None:
    for name in core_module_names():
        importlib.import_module(name)

    loaded = {
        framework
        for framework in FRAMEWORKS
        if framework in sys.modules or any(m.startswith(f"{framework}.") for m in sys.modules)
    }
    assert not loaded, (
        f"the core must not load a training framework (Principle XII); loaded: {sorted(loaded)}"
    )


def test_the_core_has_more_than_one_module_so_the_check_means_something() -> None:
    # A guard against the check passing because nothing was imported at all.
    names = core_module_names()
    assert len(names) > 10, names
