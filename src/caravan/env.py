"""Is the training framework here, and what to say when it is not.

The core may not import a training framework (Principle XII), so this module answers the question
with ``importlib.util.find_spec`` and never imports anything. The layering tests depend on that:
a module that imported the framework in order to report its absence would defeat the rule it
exists to serve.

The two messages are different on purpose (research R2). On Python 3.13 the framework is simply
not installed and the install command is the answer. On 3.14 and newer there is no wheel to
install, so ``pip install "caravan-ml[train]"`` succeeds and installs no framework — a message
that only repeated the install command would send the user in a circle.
"""

from __future__ import annotations

import importlib.util
import sys

#: The modules a stage needs before it can build, train or convert. ``keras`` is what the builder
#: half imports; ``tensorflow`` is what carries it and what the conversion stage needs.
REQUIRED_MODULES = ("tensorflow", "keras", "numpy")

#: What reading or running an exported model needs. A different extra on purpose: it has no
#: training framework in its graph and weighs 114 MiB against the conversion half's 1,971, so the
#: stages that only read a model are not dragged along by the conversion's weight.
REQUIRED_RUNTIME_MODULES = ("ai_edge_litert",)

#: The highest Python minor the runtime publishes a wheel for, with the evidence. Wider than the
#: conversion half's window and still not every version this project supports — which is a
#: correction to what this file first claimed, made after checking the index rather than after
#: assuming that a package shipping cp314 also ships cp315.
RUNTIME_WHEEL_CEILING = (3, 14)
RUNTIME_EVIDENCE = "checked 2026-10-22: ai-edge-litert 2.3.0 ships cp310 through cp314"


def install_command(*extras: str) -> str:
    """How to install exactly the extras a command needs, and no more.

    Per command rather than one constant, because the commands need different things: building and
    training need the conversion half only, and telling someone who wants to train to install the
    runtime as well would be asking for 114 MiB they have no use for. Quantizing needs both.
    """
    return f'pip install "caravan-ml[{",".join(extras)}]"'


#: The extra that carries the training framework, as a user would type it.
EXTRA_INSTALL_COMMAND = install_command("train")
RUNTIME_INSTALL_COMMAND = install_command("verify")

#: The highest Python minor the framework publishes a stable wheel for, with the evidence. One
#: place to edit when the window closes: see docs/ref/budgets.md for the obligation.
FRAMEWORK_WHEEL_CEILING = (3, 13)
FRAMEWORK_EVIDENCE = "checked 2026-10-22: tensorflow 2.21.0 ships cp310 through cp313"


class EnvironmentIncomplete(Exception):
    """A required part is not installed. Neither a broken rule nor a defect — its own exit code.

    Carried as an exception so a programmatic caller gets the same actionable text the command
    line prints, instead of an ``ImportError`` from somewhere inside a stage.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _importable(name: str) -> bool:
    """Whether a module could be imported, without importing it.

    ``find_spec`` does not only return ``None`` for something that is absent — it raises when a
    parent package is missing, and an import hook may raise anything at all. Every one of those
    answers means the same thing here: the module is not available. Letting one through would turn
    "the extra is not installed" into a traceback, which is the one outcome FR-020 forbids.
    """
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def missing_modules() -> tuple[str, ...]:
    """Which required modules are not importable, without importing any of them."""
    return tuple(name for name in REQUIRED_MODULES if not _importable(name))


def training_framework_available() -> bool:
    return not missing_modules()


def missing_runtime_modules() -> tuple[str, ...]:
    return tuple(name for name in REQUIRED_RUNTIME_MODULES if not _importable(name))


def model_runtime_available() -> bool:
    return not missing_runtime_modules()


def inside_framework_window(version: tuple[int, int] | None = None) -> bool:
    """Whether this interpreter is one the framework publishes a wheel for."""
    minor = version if version is not None else sys.version_info[:2]
    return minor <= FRAMEWORK_WHEEL_CEILING


def inside_runtime_window(version: tuple[int, int] | None = None) -> bool:
    """Whether this interpreter is one the model runtime publishes a wheel for."""
    minor = version if version is not None else sys.version_info[:2]
    return minor <= RUNTIME_WHEEL_CEILING


def missing_runtime_message(command: str, *, version: tuple[int, int] | None = None) -> str:
    """What to say when the part that reads and runs a model is absent.

    Two cases again, for the same reason as the conversion half: on a Python the runtime publishes
    for, the install command is the answer; above it, no amount of installing helps and saying so
    is the only useful thing. The window is wider here — through 3.14 rather than 3.13 — which is
    worth stating rather than rounding to "everywhere".
    """
    minor = version if version is not None else sys.version_info[:2]
    if inside_runtime_window(minor):
        return (
            f"{command} needs the verify extra to read and measure a model, which is not "
            f"installed\n    install it with: {RUNTIME_INSTALL_COMMAND}"
        )
    running = f"{minor[0]}.{minor[1]}"
    return (
        f"{command} needs a model runtime, which publishes no wheel for Python {running}\n"
        f"    {RUNTIME_EVIDENCE}\n"
        f"    read and measure a model on Python "
        f"{RUNTIME_WHEEL_CEILING[0]}.{RUNTIME_WHEEL_CEILING[1]} or below; validate and render "
        "run here"
    )


def missing_extra_message(
    command: str,
    *,
    version: tuple[int, int] | None = None,
    extras: tuple[str, ...] = ("train",),
) -> str:
    """The two-line answer of ``contracts/cli.md``, chosen by which situation this is.

    ``extras`` is what *this* command needs: ``("train",)`` for building and training,
    ``("train", "verify")`` for quantizing, which converts and measures.
    """
    minor = version if version is not None else sys.version_info[:2]
    running = f"{minor[0]}.{minor[1]}"
    if inside_framework_window(minor):
        return (
            f"{command} needs the train extra, which is not installed\n"
            f"    install it with: {install_command(*extras)}"
        )
    return (
        f"{command} needs TensorFlow, which publishes no wheel for Python {running}\n"
        f"    {FRAMEWORK_EVIDENCE}\n"
        f"    train on Python {FRAMEWORK_WHEEL_CEILING[0]}.{FRAMEWORK_WHEEL_CEILING[1]}; "
        "validate, render and the analysis stages run here"
    )
