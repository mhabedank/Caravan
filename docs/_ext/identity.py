"""Every colour on this site comes from the identity (feature 010, FR-030).

Sphinx writes its own ``pygments.css`` for syntax highlighting and links it on every page. That
file carries about fifty literal colours — a full syntax rainbow — and the identity has four inks.
FR-030 says no element may use a colour absent from the identity, and
``contracts/design-tokens.md`` says no interface colour is declared outside the token set. A
stylesheet we neither wrote nor can express in tokens breaks both.

So it is not linked. ``site.css`` colours the four distinctions worth making — a comment recedes, a
string and a keyword take the two cool inks, everything else is body text — and anything it does
not name inherits the body colour, which is the intended result rather than a gap.

After this the only stylesheets the site serves are ``tokens.css`` and ``site.css``, which is what
makes "every colour comes from the tokens" a statement about the whole site rather than about the
parts we wrote.
"""

from __future__ import annotations

from typing import Any

from docutils import nodes
from sphinx.application import Sphinx


def _drop_pygments(app: Sphinx, pagename, templatename, context, doctree) -> None:
    files = context.get("css_files")
    if not files:
        return
    context["css_files"] = [
        css for css in files if getattr(css, "filename", str(css)) != "_static/pygments.css"
    ]


def _pick_template(app: Sphinx, pagename, templatename, context, doctree) -> str | None:
    """A page may ask for the landing shape in its own front matter (feature 010, research R8).

    The landing page is the one page whose shape is not an article: no measure cap and no running
    text, but sections. Returning a template name here overrides the one Sphinx chose, which keeps
    the choice with the page that needs it instead of in a list of exceptions in the configuration.
    """
    meta = (context or {}).get("meta") or {}
    if meta.get("layout") == "landing":
        return "landing.html"
    return None


def _drop_landing_title(app: Sphinx, doctree, docname: str) -> None:
    """The landing page keeps its title in the document and shows it in the hero.

    Without a single top-level heading, every ``##`` on the page is a top-level section, and
    Sphinx renders each of them as an ``<h1>``: seven first-level headings on one page, and a
    heading scale that no longer distinguishes a section from the page. With one, the sections
    nest where they belong and render as ``<h2>``.

    But the title would then be printed twice — once by the hero, which takes its words from the
    same page's front matter, and once at the top of the body. So the title node is removed here,
    after Sphinx has read it for the browser tab, the navigation and the toctree, and before the
    writer turns it into a heading. The sections keep their depth, so the headings keep their
    levels; only the duplicate disappears.
    """
    if app.env.metadata.get(docname, {}).get("layout") != "landing":
        return
    for section in doctree.findall(nodes.section):
        for child in section.children:
            if isinstance(child, nodes.title):
                section.remove(child)
                return
        return


def setup(app: Sphinx) -> dict[str, Any]:
    app.connect("doctree-resolved", _drop_landing_title)
    app.connect("html-page-context", _drop_pygments)
    app.connect("html-page-context", _pick_template)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
