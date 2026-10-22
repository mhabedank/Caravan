"""Every shell block in the workflow parses as a shell script.

A stray quote in a ``run:`` block is invisible to the YAML parser and to review, and costs a
whole continuous integration cycle to discover: the job installs its environment, runs most of
the step, and only then does the shell reach the end of the file looking for the closing quote.
``bash -n`` reads a script without running it, which turns that cycle into a second here.

This is a check on the project's own plumbing rather than on caravan, so it asserts nothing about
what the commands *do* — only that a shell would accept them.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def shell_blocks() -> list[tuple[str, str]]:
    """Every ``run:`` script in the workflow, labelled by the job and step it came from."""
    document = YAML(typ="safe").load(WORKFLOW.read_text(encoding="utf-8"))
    blocks: list[tuple[str, str]] = []
    for job_name, job in document["jobs"].items():
        for index, step in enumerate(job.get("steps", [])):
            script = step.get("run")
            if script is None:
                continue
            label = step.get("name") or f"step {index + 1}"
            blocks.append((f"{job_name}: {label}", script))
    return blocks


def test_the_workflow_has_shell_blocks_to_check() -> None:
    # Guards the check itself: a parser change that silently found nothing would make every
    # assertion below pass without reading a line of shell.
    assert len(shell_blocks()) >= 10


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash to parse with")
@pytest.mark.parametrize(("label", "script"), shell_blocks(), ids=lambda value: value[:60])
def test_each_run_block_parses_as_shell(label: str, script: str) -> None:
    result = subprocess.run(
        ["bash", "-n"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{label}:\n{result.stderr}"
