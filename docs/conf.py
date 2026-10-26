"""The documentation site: Sphinx with MyST, built from docs/ (feature 009, research R1).

Build it with ``uv run --group docs sphinx-build -W -b html docs _site``. ``-W`` turns every warning
into a failed build, which is what makes the checks real: a broken link or anchor, and a page that
is in no table of contents, both stop it.

The version shown on every page comes from ``CARAVAN_VERSION`` when the release workflow builds the
site for a tag, and otherwise from the package's own version, read as text so that building the
documentation never imports Caravan.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


def _package_version() -> str:
    source = Path(__file__).resolve().parent.parent / "src" / "caravan" / "__init__.py"
    match = re.search(r'^__version__ = "([^"]+)"', source.read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else "unknown"


project = "Caravan"
author = "Caravan contributors"
copyright = "Apache-2.0"
release = version = os.environ.get("CARAVAN_VERSION") or _package_version()

extensions = ["myst_parser"]
source_suffix = {".md": "markdown"}
root_doc = "index"
# Working records stay in the repository and are linked as files on GitHub; they are not pages.
exclude_patterns = ["_build", "design/**", "research/**"]

myst_heading_anchors = 3
myst_enable_extensions = ["substitution"]
myst_substitutions = {"release": release}

html_theme = "alabaster"
html_title = f"Caravan {release}"
html_short_title = "Caravan"
html_theme_options = {
    "description": f"Small models onto microcontrollers. This site describes {release}.",
    "github_user": "mhabedank",
    "github_repo": "Caravan",
    "github_button": False,
    "fixed_sidebar": True,
    "show_relbars": True,
    "extra_nav_links": {"Repository on GitHub": "https://github.com/mhabedank/Caravan"},
}
html_show_sourcelink = False
html_copy_source = False
