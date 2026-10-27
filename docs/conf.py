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
import sys
from pathlib import Path


def _package_version() -> str:
    source = Path(__file__).resolve().parent.parent / "src" / "caravan" / "__init__.py"
    match = re.search(r'^__version__ = "([^"]+)"', source.read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else "unknown"


project = "Caravan"
author = "Caravan contributors"
copyright = "Apache-2.0"
release = version = os.environ.get("CARAVAN_VERSION") or _package_version()

extensions = ["myst_parser", "redirects", "identity"]
# The site's own extension lives beside this file rather than in the package: it builds the site and
# is never installed with Caravan (FR-048).
sys.path.insert(0, str(Path(__file__).resolve().parent / "_ext"))
source_suffix = {".md": "markdown"}
root_doc = "index"
# Working records stay in the repository and are linked as files on GitHub; they are not pages.
exclude_patterns = ["_build", "design/**", "research/**"]

myst_heading_anchors = 3
myst_enable_extensions = ["substitution"]
myst_substitutions = {"release": release}

# The identity, copied from the Mobility Model Zoo and carried as a theme of our own (feature 010,
# D1 and research R1). A theme here installs nothing, which Principle XII prefers to a third-party
# theme whose own design decisions would then have to be overridden.
html_theme_path = ["_themes"]
html_theme = "caravan"
html_short_title = "Caravan"
html_title = f"Caravan {release}"
html_show_sourcelink = False
html_copy_source = False
html_favicon = None  # the theme links its own, which turns over with the colour scheme

# The header's links. A curated list, not the table of contents: the contents is thirteen pages and
# a header of thirteen links helps nobody. tests/contract/test_docs_landing.py holds every entry to
# a page that exists, so curating cannot rot silently.
html_context = {
    "nav_pages": [
        ("route/index", "The route"),
        ("concepts/templates", "Concepts"),
        ("reference/manifest", "Reference"),
        ("compatibility", "Verified today"),
        ("roadmap", "Roadmap"),
    ],
}

# Addresses that moved (FR-045). Filled as pages move; the extension refuses a forward whose target
# is not a page, so a typo here fails the build rather than publishing a dead forward.
caravan_redirects: dict[str, str] = {}
