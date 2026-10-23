"""The README's commands run, and its install lines are the guide's (feature 007, SC-003).

Before this feature the README promised ``pip install caravan-ml``, which has never worked: the name
is not on the package index (checked 2026-10-23). These checks are what would have caught it.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from caravan import __version__
from caravan.cli.main import EXIT_OK, main
from tests.support_docs import commands

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
GUIDE = ROOT / "docs" / "try-it.md"


def test_the_readme_commands_run(monkeypatch, capsys) -> None:
    monkeypatch.chdir(ROOT)
    found = commands(README, "readme")
    assert found, "the README has no block marked '# step: readme'"
    for command in found:
        argv = shlex.split(command)
        assert argv[0] == "caravan"
        extra = [] if "--stdout" in argv else ["--no-report"]
        assert main([*argv[1:], *extra]) == EXIT_OK, command


def test_no_install_line_assumes_the_package_index() -> None:
    text = README.read_text(encoding="utf-8")
    bare = re.findall(r"pip install \"?caravan-ml(\[[^\]]*\])?\"?\s*(#|$)", text, re.MULTILINE)
    assert not bare, "the README installs caravan-ml by name, which is not on the package index"


def test_the_readme_installs_what_the_guide_installs() -> None:
    wheel = f"releases/download/v{__version__}/caravan_ml-{__version__}-py3-none-any.whl"
    assert wheel in README.read_text(encoding="utf-8")
    assert wheel in " ".join(commands(GUIDE, "install"))
