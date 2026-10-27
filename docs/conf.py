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

# The landing page's h1 is shown in the theme, inside the hero's dark panel, because the panel is
# structure rather than content. It is still WRITTEN in `index.md`, as that page's `# ` title, and
# `_ext/identity.py` drops the title node before the writer turns it into a heading.
#
# The roundabout route is there to keep a check. With no title in the source, every `##` on the
# page is a top-level section and Sphinx renders each as an `<h1>`: seven first-level headings on
# one page. Silencing MyST's complaint about the missing h1 — the first thing tried here — also
# silenced the heading-order check that had caught the manifest reference skipping H2 to H4
# forty-three times. With the title where it belongs, nothing is suppressed and that check is back.
# colon_fence lets a layout wrapper use `:::` so that code blocks inside it keep ```, which is how
# a leg frames the card at its head and the check at its foot.
# attrs_block puts a class on the SECTION a heading opens — `{.band .band-3}` on the line above a
# `##` — which is what gives the landing page its grids.
#
# attrs_block rather than a container directive, and the reason is worth keeping: a heading inside
# a `container` becomes `<p class="rubric">`, not a heading, because docutils does not treat it as
# a document section. The landing page's first draft was built that way and looked right while
# having no structure under it at all. Found by reading the rendered HTML; the accessibility audit
# did not catch it, because its heading rules check the order of the headings that exist.
myst_enable_extensions = ["substitution", "colon_fence", "attrs_block"]
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
caravan_redirects: dict[str, str] = {
    # The single entry page became the route's first two legs.
    "try-it": "route/index",
    # The own-project guide was folded into leg 2 and the concept pages it needed.
    "guides/own-project": "route/2-your-columns",
    # The owner's personal board came off the site (feature 010, D2). The forward stays because the
    # address was published and is linked from elsewhere; the stub is noindex and carries no
    # content, so nothing a reader reads mentions that board.
    "guides/lora32": "route/3-onto-a-board",
}
