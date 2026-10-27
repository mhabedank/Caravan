"""Every colour on this site comes from the identity (feature 010, FR-030).

Sphinx writes its own ``pygments.css`` for syntax highlighting and links it on every page. That
file carries about fifty literal colours — a full syntax rainbow — and the identity has four inks.
FR-030 says no element may use a colour absent from the identity, and
``contracts/design-tokens.md`` says no interface colour is declared outside the token set. A
stylesheet we neither wrote nor can express in tokens breaks both.

So it is not linked. ``site.css`` colours the four distinctions worth making — a comment recedes, a
string and a keyword take the two cool inks, everything else is body text — and anything it does
not name inherits the body colour, which is the intended result rather than a gap.

This is also why the check in ``tests/contract/test_docs_tokens.py`` can be absolute about colour
literals: after this, the only stylesheets the site serves are ``tokens.css`` and ``site.css``.
"""

from __future__ import annotations

from typing import Any

from sphinx.application import Sphinx


def _drop_pygments(app: Sphinx, pagename, templatename, context, doctree) -> None:
    files = context.get("css_files")
    if not files:
        return
    context["css_files"] = [
        css for css in files if getattr(css, "filename", str(css)) != "_static/pygments.css"
    ]


def setup(app: Sphinx) -> dict[str, Any]:
    app.connect("html-page-context", _drop_pygments)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
