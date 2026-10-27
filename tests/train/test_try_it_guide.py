"""The guide runs as written (feature 007, User Story 1, SC-002, SC-003).

``docs/try-it.md`` is executed here, block by block, in a directory laid out the way its ``fetch``
block lays it out. The ``install`` and ``fetch`` blocks need the published release, so the release
workflow runs those against it. That they name *this* version is checked in
``tests/contract/test_docs_guide.py``, which needs no framework and so runs everywhere.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support import SYNTHETIC_DATASET
from tests.support_docs import commands
from tests.train.test_console_output import FRAMEWORK_LINE

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "try-it.md"


@pytest.fixture(scope="module")
def tried(tmp_path_factory) -> dict:
    here = tmp_path_factory.mktemp("try-it")
    shutil.copytree(ROOT / "examples", here / "examples")
    shutil.copytree(
        SYNTHETIC_DATASET,
        here / "tests" / "fixtures" / "datasets" / "synthetic",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    path = f"{Path(sys.executable).parent}:/usr/bin:/bin"
    results = {}
    for command in commands(GUIDE, "run"):
        done = subprocess.run(
            ["bash", "-euo", "pipefail", "-c", command],
            cwd=here,
            env={"PATH": path, "HOME": str(here)},
            capture_output=True,
            text=True,
            timeout=900,
        )
        results[command] = done
    return {"dir": here, "results": results}


def test_every_run_command_succeeds(tried) -> None:
    assert tried["results"], "the guide has no run block"
    for command, done in tried["results"].items():
        assert done.returncode == 0, f"{command}\n{done.stdout}\n{done.stderr}"


def test_the_export_step_fits_on_one_screen(tried) -> None:
    (export,) = [c for c in tried["results"] if c.startswith("caravan export")]
    done = tried["results"][export]
    console = done.stdout + done.stderr
    assert len(console.splitlines()) <= 25, console
    assert not FRAMEWORK_LINE.search(console), console


def test_the_files_the_guide_lists_exist(tried) -> None:
    runs = tried["dir"] / "runs"
    run = max(runs.iterdir(), key=lambda p: p.stat().st_mtime)
    section = GUIDE.read_text(encoding="utf-8").split("## What you get", 1)[1].split("\n## ", 1)[0]
    listed = re.findall(r"^- `([^`]+)`", section, re.MULTILINE)
    assert listed, "the guide lists no files"
    for name in listed:
        if "<board>" in name:
            assert list(run.glob(name.replace("<board>", "*"))), name
        else:
            assert (run / name).exists(), name
