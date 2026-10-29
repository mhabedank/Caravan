"""The route's legs run as written (feature 010, FR-017, SC-005).

Three of the four legs are executed here against the working tree:

- **leg 1**'s ``run`` block, command by command, in a directory laid out the way its ``fetch`` block
  lays it out. ``install`` and ``fetch`` need the published release, so the release workflow runs
  those against it; that they name *this* version is checked in
  ``tests/contract/test_docs_guide.py``, which needs no framework and so runs everywhere.
- **leg 2**'s ``own-columns`` blocks, which fetch a small table, write a manifest and export it. The
  download is swapped for a copy of the file in ``docs/_static/data`` (see ``_offline``); the rest
  runs as written, so a check proves the instructions still work rather than assumes it.
- **leg 4**'s ``tighten`` blocks, which ask for a model far too large for the board and must
  therefore *fail* the fit check. A check that stopped refusing would otherwise be the quietest
  possible regression.

  Leg 4 provokes the **fit** check rather than the quantization gate, and running it is how that was
  found out: leg 2's model loses nothing to int8, so even a budget of zero passes it. The leg says
  so rather than pretending otherwise.

Leg 3 needs a board and a cross-compiler. Its firmware is built by the firmware workflow instead.

Why legs 2 and 4 run as whole blocks rather than command by command: both use heredocs and both
``cd``, and ``commands()`` splits a block into lines, which destroys a heredoc and loses the
directory between lines. ``blocks()`` keeps each block whole, and concatenating a leg's blocks into
one script is also how the release workflow runs leg 1.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support import SYNTHETIC_DATASET
from tests.support_docs import blocks, commands
from tests.train.test_console_output import FRAMEWORK_LINE

ROOT = Path(__file__).resolve().parents[2]
LEG1 = ROOT / "docs" / "route" / "1-first-model.md"
LEG2 = ROOT / "docs" / "route" / "2-your-columns.md"
LEG4 = ROOT / "docs" / "route" / "4-when-it-does-not-fit.md"
READINGS = ROOT / "docs" / "_static" / "data" / "readings.csv"


def _offline(script: str) -> str:
    """Leg 2 downloads readings.csv from the published site, which a test run cannot reach.

    The ``curl -L -o <dest> <url>`` line becomes a copy of the same file from the working tree into
    the same destination; every other line runs unchanged.
    """
    swapped, count = re.subn(
        r"^curl -L -o (\S+) https://\S+/readings\.csv$",
        lambda m: f"cp {READINGS} {m[1]}",
        script,
        flags=re.MULTILINE,
    )
    assert count == 1, "leg 2 no longer has the curl line the test substitutes"
    return swapped


def _run(script: str, cwd: Path, env_home: Path) -> subprocess.CompletedProcess:
    path = f"{Path(sys.executable).parent}:/usr/bin:/bin"
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        cwd=cwd,
        env={"PATH": path, "HOME": str(env_home)},
        capture_output=True,
        text=True,
        timeout=1800,
    )


@pytest.fixture(scope="module")
def walked(tmp_path_factory) -> dict:
    """Legs 1, 2 and 4 walked in order, in one directory, as a reader would."""
    here = tmp_path_factory.mktemp("route")
    shutil.copytree(ROOT / "examples", here / "examples")
    shutil.copytree(
        SYNTHETIC_DATASET,
        here / "tests" / "fixtures" / "datasets" / "synthetic",
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    leg1 = {command: _run(command, here, here) for command in commands(LEG1, "run")}
    # Leg 1's own check runs as one block: it holds a heredoc and carries a shell variable from one
    # line to the next, and `commands()` splitting it into lines would destroy both.
    leg1_check = _run("".join(blocks(LEG1, "check")), here, here)
    leg2 = _run(_offline("".join(blocks(LEG2, "own-columns"))), here, here)
    # Leg 4 continues from leg 2's directory, so it only runs if leg 2 got there.
    leg4 = _run("".join(blocks(LEG4, "tighten")), here, here) if leg2.returncode == 0 else None
    return {"dir": here, "leg1": leg1, "leg1_check": leg1_check, "leg2": leg2, "leg4": leg4}


def test_leg_one_every_run_command_succeeds(walked) -> None:
    assert walked["leg1"], "leg 1 has no run block"
    for command, done in walked["leg1"].items():
        assert done.returncode == 0, f"{command}\n{done.stdout}\n{done.stderr}"


def test_leg_one_export_output_fits_on_one_screen(walked) -> None:
    (export,) = [c for c in walked["leg1"] if c.startswith("caravan export")]
    done = walked["leg1"][export]
    console = done.stdout + done.stderr
    assert len(console.splitlines()) <= 25, console
    assert not FRAMEWORK_LINE.search(console), console


def test_leg_one_leaves_what_it_promised(walked) -> None:
    run = max((walked["dir"] / "runs").iterdir(), key=lambda p: p.stat().st_mtime)
    for name in ("model/model.tflite", "model/model_data.h", "quantization.json"):
        assert (run / name).exists(), name


def test_leg_one_check_runs_and_prints_the_verdict(walked) -> None:
    """The block that tells the reader to verify the result has to work when they run it."""
    done = walked["leg1_check"]
    assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
    for phrase in ("trained model:", "int8 model:", "verdict:"):
        assert phrase in done.stdout, f"{phrase!r} missing:\n{done.stdout}"


def test_leg_two_runs_and_leaves_a_model_of_the_readers_own(walked) -> None:
    done = walked["leg2"]
    assert done.returncode == 0, f"{done.stdout}\n{done.stderr}"
    runs = walked["dir"] / "machine" / "runs"
    assert runs.is_dir(), "leg 2 wrote no run directory of its own"
    run = max(runs.iterdir(), key=lambda p: p.stat().st_mtime)
    for name in ("metrics.json", "quantization.json", "model/model_data.h"):
        assert (run / name).exists(), name


def test_leg_two_promised_numbers_are_printed(walked) -> None:
    """The leg promises an accuracy figure, the figure after shrinking, and the verdict."""
    out = walked["leg2"].stdout
    for phrase in ("accuracy on the test part", "after making it 8-bit", "gate verdict"):
        assert phrase in out, f"{phrase!r} missing from leg 2's output:\n{out}"


def test_leg_four_makes_the_fit_check_refuse(walked) -> None:
    """A model far larger than the board's flash cannot fit, so the run fails before training."""
    done = walked["leg4"]
    assert done is not None, "leg 4 did not run because leg 2 failed"
    assert done.returncode == 0, f"leg 4's own script failed:\n{done.stdout}\n{done.stderr}"
    assert "exit code:" in done.stdout, (
        "leg 4 asked for a model too big for the board and the export did not fail. Either the fit "
        f"check stopped refusing, or the leg no longer provokes it:\n{done.stdout}\n{done.stderr}"
    )
    assert "outcome: error" in done.stdout, f"the report did not record the failure:\n{done.stdout}"
    assert "never written" in done.stdout, (
        f"a model was written for a run that failed its fit check:\n{done.stdout}"
    )
