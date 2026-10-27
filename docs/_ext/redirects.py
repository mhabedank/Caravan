"""Forwarding stubs for addresses that moved (feature 010, FR-045).

The site is published as static files, so a forward is a small HTML file: a meta refresh, a
canonical link to the target, and ``noindex`` so the stub never competes in a search index with the
page it points at. Sphinx has no redirect of its own and a third-party extension exists, but the
whole mechanism is the thirty lines below and the site's build tools are pinned exactly — under
Principle XII, owning this is the cheaper trade.

The map lives in ``conf.py`` as ``caravan_redirects``: ``{"old/address": "new/docname"}``. The key
is the address as it was published, without a suffix; the value is the docname to forward to.

A stub carries no content of its own. That is what lets a forward exist from an address whose path
names something the site no longer mentions: FR-039 is about what a reader reads, and a reader
never reads a stub (research R6).
"""

from __future__ import annotations

import posixpath
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.util import logging

logger = logging.getLogger(__name__)

STUB = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
<title>Moved</title>
</head>
<body><p>This page moved to <a href="{target}">{target}</a>.</p></body>
</html>
"""


def _write_stubs(app: Sphinx, exception: Exception | None) -> None:
    if exception is not None:
        return
    redirects: dict[str, str] = app.config.caravan_redirects
    if not redirects:
        return
    out = Path(app.outdir)
    for old, new_docname in sorted(redirects.items()):
        if new_docname not in app.env.all_docs:
            # A forward to a page that does not exist is worse than none: it turns a dead address
            # into a dead address that claims to have been fixed.
            raise ValueError(
                f"caravan_redirects: {old!r} forwards to {new_docname!r}, which is not a page. "
                f"Either the target is misspelled or the page was not written."
            )
        stub = out / f"{old}.html"
        stub.parent.mkdir(parents=True, exist_ok=True)
        target = posixpath.relpath(f"{new_docname}.html", posixpath.dirname(old) or ".")
        stub.write_text(STUB.format(target=target), encoding="utf-8")
        logger.info("forwarding %s.html to %s.html", old, new_docname)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value("caravan_redirects", {}, "html")
    app.connect("build-finished", _write_stubs)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
