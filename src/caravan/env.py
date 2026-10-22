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

#: The modules a stage needs before it can build or train. ``keras`` is what the builder half
#: imports; ``tensorflow`` is what carries it and what the conversion stage will need.
REQUIRED_MODULES = ("tensorflow", "keras", "numpy")

#: The extra that carries them, as a user would type it.
EXTRA_INSTALL_COMMAND = 'pip install "caravan-ml[train]"'

#: The highest Python minor the framework publishes a stable wheel for, with the evidence. One
#: place to edit when the window closes: see docs/budgets.md for the obligation.
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


def inside_framework_window(version: tuple[int, int] | None = None) -> bool:
    """Whether this interpreter is one the framework publishes a wheel for."""
    minor = version if version is not None else sys.version_info[:2]
    return minor <= FRAMEWORK_WHEEL_CEILING


def missing_extra_message(
    command: str,
    *,
    version: tuple[int, int] | None = None,
) -> str:
    """The two-line answer of ``contracts/cli.md``, chosen by which situation this is."""
    minor = version if version is not None else sys.version_info[:2]
    running = f"{minor[0]}.{minor[1]}"
    if inside_framework_window(minor):
        return (
            f"{command} needs the train extra, which is not installed\n"
            f"    install it with: {EXTRA_INSTALL_COMMAND}"
        )
    return (
        f"{command} needs TensorFlow, which publishes no wheel for Python {running}\n"
        f"    {FRAMEWORK_EVIDENCE}\n"
        f"    train on Python {FRAMEWORK_WHEEL_CEILING[0]}.{FRAMEWORK_WHEEL_CEILING[1]}; "
        "validate, render and the analysis stages run here"
    )
