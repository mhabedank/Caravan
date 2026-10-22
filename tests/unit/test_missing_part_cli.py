"""Two parts, two answers, and neither is a traceback (FR-025, SC-009)."""

from __future__ import annotations

import pytest

from caravan.cli.main import EXIT_ENVIRONMENT, main
from caravan.env import (
    install_command,
    model_runtime_available,
    training_framework_available,
)
from tests.support import PILOT_FIXTURE


def quantize(tmp_path):
    return main(
        [
            "quantize",
            str(PILOT_FIXTURE),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )


@pytest.mark.skipif(
    training_framework_available() and model_runtime_available(),
    reason="both parts are installed here, so there is no absence to assert",
)
def test_a_missing_part_exits_with_the_environment_code(tmp_path) -> None:
    assert quantize(tmp_path) == EXIT_ENVIRONMENT


@pytest.mark.skipif(
    training_framework_available() and model_runtime_available(),
    reason="both parts are installed here",
)
def test_no_run_directory_is_left_behind(tmp_path) -> None:
    runs = tmp_path / "runs"
    quantize(tmp_path)
    assert not runs.exists()


@pytest.mark.skipif(
    training_framework_available() and model_runtime_available(),
    reason="both parts are installed here",
)
def test_the_message_names_a_part_and_carries_no_traceback(tmp_path, capsys) -> None:
    quantize(tmp_path)
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "ModuleNotFoundError" not in err
    assert "site-packages" not in err
    assert ("train extra" in err) or ("verify extra" in err) or ("no wheel for Python" in err)


def test_the_runtime_message_names_its_own_window() -> None:
    """The runtime has a window too — wider than the conversion half's, and not unlimited.

    This test first asserted the sentence "installs on every Python caravan supports", which was
    not true: the runtime publishes no cp315 wheel. Both branches are asserted here so the next
    person reads the window rather than a reassurance.
    """
    from caravan.env import missing_runtime_message

    inside = missing_runtime_message("quantize", version=(3, 14))
    assert install_command("verify") in inside
    assert "train" not in inside.split("install it with:")[1]

    outside = missing_runtime_message("quantize", version=(3, 15))
    assert "no wheel for Python 3.15" in outside
    assert "cp310 through cp314" in outside
    assert "pip install" not in outside  # installing cannot help, so it is not suggested


def test_each_command_asks_for_only_the_extras_it_needs() -> None:
    # Building and training do not read a model, so telling someone who wants to train to install
    # the runtime as well would be asking for 114 MiB they have no use for. Quantizing needs both.
    from caravan.env import missing_extra_message

    for command in ("build", "train"):
        text = missing_extra_message(command, version=(3, 13))
        assert install_command("train") in text
        assert "verify" not in text

    quantize_text = missing_extra_message("quantize", version=(3, 13), extras=("train", "verify"))
    assert install_command("train", "verify") in quantize_text
