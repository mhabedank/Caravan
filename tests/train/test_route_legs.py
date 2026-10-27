"""The route's legs run as written (feature 010, FR-017, SC-005).

Three of the four legs are executed here against the working tree:

- **leg 1**'s ``run`` block, command by command, in a directory laid out the way its ``fetch`` block
  lays it out. ``install`` and ``fetch`` need the published release, so the release workflow runs
  those against it; that they name *this* version is checked in
  ``tests/contract/test_docs_guide.py``, which needs no framework and so runs everywhere.
- **leg 2**'s ``own-columns`` blocks, which build a small table, write a manifest and export it. Leg
  2 is executable on purpose: it makes its own data, so the whole leg runs anywhere and a check can
  prove the instructions still work rather than assume it.
- **leg 4**'s ``tighten`` blocks, which set a budget no model can meet and must therefore *fail*.
  A gate that stopped refusing would otherwise be the quietest possible regression.

Leg 3 needs a board and a cross-compiler. Its firmware is built by the firmware workflow instead.

Why legs 2 and 4 run as whole blocks rather than command by command: both use heredocs and both
``cd``, and ``commands()`` splits a block into lines, which destroys a heredoc and loses the
directory between lines. ``blocks()`` keeps each block whole, and concatenating a leg's blocks into
one script is also how the release workflow runs leg 1.
"""

from __future__ import annotations

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
    leg2 = _run("".join(blocks(LEG2, "own-columns")), here, here)
    # Leg 4 continues from leg 2's directory, so it only runs if leg 2 got there.
    leg4 = _run("".join(blocks(LEG4, "tighten")), here, here) if leg2.returncode == 0 else None
    return {"dir": here, "leg1": leg1, "leg2": leg2, "leg4": leg4}


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


def test_leg_four_makes_the_gate_refuse(walked) -> None:
    """A budget of zero cannot be met, so the run must fail and export nothing."""
    done = walked["leg4"]
    assert done is not None, "leg 4 did not run because leg 2 failed"
    assert done.returncode == 0, f"leg 4's own script failed:\n{done.stdout}\n{done.stderr}"
    assert "exit code:" in done.stdout, (
        "leg 4 set a budget of zero and the export did not fail. Either the gate stopped "
        f"refusing, or the leg no longer provokes it:\n{done.stdout}\n{done.stderr}"
    )
