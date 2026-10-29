"""The two messages a user sees when the training extra is not usable.

FR-020 asks for an actionable message rather than a traceback, and the two situations need
different answers: on 3.13 the framework is simply not installed, and on 3.14 or newer there is no
wheel to install, so repeating the install command would send the user in a circle (research R2).
"""

from __future__ import annotations

import sys

from caravan import env


def test_the_installable_case_names_the_install_command() -> None:
    message = env.missing_extra_message("build", version=(3, 13))
    assert 'pip install "caravan-ml[train]"' in message
    assert "not installed" in message


def test_the_unavailable_case_names_the_window_the_reason_and_the_date() -> None:
    message = env.missing_extra_message("train", version=(3, 14))
    assert "Python 3.14" in message
    assert "checked 2026-10-22" in message
    assert "cp310 through cp313" in message
    assert "train on Python 3.13" in message
    # It must not tell the user to run an install command that would install nothing.
    assert "pip install" not in message


def test_a_future_python_gets_the_unavailable_case_too() -> None:
    assert "no wheel" in env.missing_extra_message("build", version=(3, 15))
    assert "no wheel" in env.missing_extra_message("build", version=(4, 0))


def test_neither_message_leaks_an_internal_detail() -> None:
    # The rule of the message form: no module path, no library type name, no traceback. Those
    # belong to exit code 3 alone.
    for version in ((3, 13), (3, 14)):
        message = env.missing_extra_message("build", version=version)
        assert "Traceback" not in message
        assert "caravan." not in message
        assert "importlib" not in message
        assert "ModuleNotFoundError" not in message


def test_the_window_is_stated_in_one_place() -> None:
    # One constant to edit when TensorFlow ships for the current Python, which is the obligation
    # docs/ref/budgets.md carries. A second copy of the date would be a second thing to forget.
    assert env.FRAMEWORK_WHEEL_CEILING == (3, 13)
    assert "2026-10-22" in env.FRAMEWORK_EVIDENCE
    assert env.inside_framework_window((3, 13)) is True
    assert env.inside_framework_window((3, 14)) is False


def test_availability_is_answered_without_importing_anything() -> None:
    # The core may not import a training framework (Principle XII), so the check uses find_spec.
    # If this module imported the framework to find out whether it exists, the layering test it
    # serves would be meaningless.
    before = set(sys.modules)
    env.training_framework_available()
    added = {name.split(".")[0] for name in set(sys.modules) - before}
    assert not added & {"tensorflow", "keras", "numpy"}
