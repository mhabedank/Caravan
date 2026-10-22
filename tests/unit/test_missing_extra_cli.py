"""Without the training extra: an answer, not a traceback (SC-006, FR-020).

Marked so it runs only where the framework is absent — in the `test` matrix on every Python and in
the `clean-environment` job, which is the environment a new contributor actually has.
"""

from __future__ import annotations

import pytest

from caravan.cli.main import EXIT_ENVIRONMENT, main
from caravan.env import training_framework_available
from tests.support import PILOT_FIXTURE

pytestmark = pytest.mark.skipif(
    training_framework_available(),
    reason="this asserts the absence path; the framework is installed here",
)


@pytest.mark.requires_no_train_extra
@pytest.mark.parametrize("command", ["build", "train"])
def test_the_exit_code_says_the_environment_is_incomplete(command, tmp_path, capsys) -> None:
    code = main(
        [
            command,
            str(PILOT_FIXTURE),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    # Not exit 1: the manifest is fine. Not exit 3: the tool is fine. The *environment* is not.
    assert code == EXIT_ENVIRONMENT


@pytest.mark.requires_no_train_extra
@pytest.mark.parametrize("command", ["build", "train"])
def test_the_message_is_actionable_and_carries_no_traceback(command, tmp_path, capsys) -> None:
    main(
        [
            command,
            str(PILOT_FIXTURE),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "ModuleNotFoundError" not in err
    assert "site-packages" not in err
    # Either the install command or the window and its reason, depending on the interpreter.
    assert ("caravan-ml[train]" in err) or ("no wheel for Python" in err)


@pytest.mark.requires_no_train_extra
@pytest.mark.parametrize("command", ["build", "train"])
def test_no_run_directory_is_left_behind(command, tmp_path) -> None:
    # The user asked for something this installation cannot do. An empty run directory recording
    # that would be a worse answer than none.
    runs = tmp_path / "runs"
    main([command, str(PILOT_FIXTURE), "--runs-dir", str(runs), "--cache-dir", str(tmp_path / "c")])
    assert not runs.exists()


def test_the_verbs_that_need_both_halves_say_so() -> None:
    """The pipeline's own check names what *this* verb needs, not what the first verb needed.

    Added with feature 004. Before it, `caravan quantize` on a machine with neither extra was told
    to install the conversion half, and then refused a second time by the stage that also needs the
    runtime. Two refusals for one missing install is a message that under-reports, which is the
    same category of fault as a number without its provenance.
    """
    import inspect

    from caravan.cli import export as export_command
    from caravan.cli import quantize as quantize_command

    for module in (quantize_command, export_command):
        source = inspect.getsource(module.run)
        assert 'extras=("train", "verify")' in source, module.__name__
