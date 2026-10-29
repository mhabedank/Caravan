"""The install step and part 1's fetch step name this version (feature 007, SC-003; feature 010).

Checking the version strings needs no training framework: it reads the guide and compares text
with ``caravan.__version__``. It lived in ``tests/train`` next to the tests that *execute* the
guide, which means it was collected only where Keras is installed — so a documentation-only change
that left a stale version behind was caught by the heaviest job in the pipeline, or by nothing.

It is core, so it runs on every Python in the ``test`` job and in the documentation checks, and
``tests/train`` keeps the tests that genuinely need the framework: the ones that run the guide.
"""

from __future__ import annotations

from pathlib import Path

from caravan import __version__
from tests.support_docs import commands

ROOT = Path(__file__).resolve().parents[2]
#: The install block lives on the installation page; part 1 of the tutorial fetches the example.
INSTALL = ROOT / "docs" / "intro" / "install.md"
GUIDE = ROOT / "docs" / "intro" / "tutorial01.md"
WHEEL = (
    f"https://github.com/mhabedank/Caravan/releases/download/v{__version__}/"
    f"caravan_ml-{__version__}-py3-none-any.whl"
)


def test_the_install_and_fetch_steps_name_this_version() -> None:
    install = " ".join(commands(INSTALL, "install"))
    fetch = " ".join(commands(GUIDE, "fetch"))
    assert WHEEL in install
    assert f"/archive/refs/tags/v{__version__}.tar.gz" in fetch
    assert f"Caravan-{__version__}/examples" in fetch
