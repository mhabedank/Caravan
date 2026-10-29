"""Forwarding stubs for addresses that moved, anchors included.

The site is published as static files, so a forward is a small HTML file. Sphinx has no redirect of
its own and a third-party extension exists, but the whole mechanism is the lines below and the
site's build tools are pinned exactly — under Principle XII, owning this is the cheaper trade.

The map lives in ``conf.py`` as ``caravan_redirects``. The key is the address as it was published,
without a suffix. The value is either the docname to forward to, or, for a page whose anchors
changed as well as its address::

    {"to": "ref/cli", "anchors": {"caravan-export": "ref/cli#cli-caravan-export", ...}}

What a stub does:

1. A script runs first. If the reader arrived with an anchor the map knows, it goes to the mapped
   page and anchor; otherwise to the target with the reader's anchor unchanged, so a page that
   moved whole keeps every deep link into it with no map at all. ``location.replace`` keeps the
   stub out of the browser's history.
2. Without scripts, a meta refresh inside ``<noscript>`` goes to the target page. It sits inside
   ``<noscript>`` so that it can never race the script and drop the anchor.
3. ``noindex`` and a canonical link keep the stub out of search engines; it carries no content of
   its own, so it is in no navigation and the site's search never finds it.

What fails the build, because each one publishes a forward that claims to work and does not:

- a forward to a page that does not exist;
- a forward to an address that is itself a forward (a chain);
- an anchor-map entry whose page or anchor the new build does not contain.
"""

from __future__ import annotations

import json
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
<link rel="canonical" href="{target}">
<title>Moved</title>
<script>(function(){{var m={anchors},h=location.hash.slice(1),
t=m[h]||"{target}"+location.hash;location.replace(t);}})();</script>
<noscript><meta http-equiv="refresh" content="0; url={target}"></noscript>
</head>
<body><p>This page moved to <a href="{target}">{target}</a>.</p></body>
</html>
"""


def _split(value: str | dict[str, Any]) -> tuple[str, dict[str, str]]:
    if isinstance(value, str):
        return value, {}
    return value["to"], dict(value.get("anchors", {}))


def _relative(old: str, docname: str, anchor: str = "") -> str:
    path = posixpath.relpath(f"{docname}.html", posixpath.dirname(old) or ".")
    return f"{path}#{anchor}" if anchor else path


def _write_stubs(app: Sphinx, exception: Exception | None) -> None:
    if exception is not None:
        return
    redirects: dict[str, str | dict[str, Any]] = app.config.caravan_redirects
    if not redirects:
        return
    out = Path(app.outdir)
    ids_of: dict[str, str] = {}

    def has_anchor(docname: str, anchor: str) -> bool:
        if docname not in ids_of:
            ids_of[docname] = (out / f"{docname}.html").read_text(encoding="utf-8")
        return f'id="{anchor}"' in ids_of[docname]

    for old, value in sorted(redirects.items()):
        new_docname, anchors = _split(value)
        if new_docname in redirects:
            raise ValueError(
                f"caravan_redirects: {old!r} forwards to {new_docname!r}, which is itself a "
                f"forward. Point it at the final page."
            )
        if new_docname not in app.env.all_docs:
            # A forward to a page that does not exist is worse than none: it turns a dead address
            # into a dead address that claims to have been fixed.
            raise ValueError(
                f"caravan_redirects: {old!r} forwards to {new_docname!r}, which is not a page. "
                f"Either the target is misspelled or the page was not written."
            )
        resolved: dict[str, str] = {}
        for old_anchor, new in sorted(anchors.items()):
            docname, _, anchor = new.partition("#")
            if docname not in app.env.all_docs or (anchor and not has_anchor(docname, anchor)):
                raise ValueError(
                    f"caravan_redirects: {old}#{old_anchor} maps to {new!r}, which the build does "
                    f"not contain. A map entry that lands on nothing sends the reader to the top "
                    f"of a page, which is the failure the map exists to prevent."
                )
            resolved[old_anchor] = _relative(old, docname, anchor)
        stub = out / f"{old}.html"
        stub.parent.mkdir(parents=True, exist_ok=True)
        target = _relative(old, new_docname)
        stub.write_text(
            STUB.format(target=target, anchors=json.dumps(resolved, separators=(",", ":"))),
            encoding="utf-8",
        )
        logger.info("forwarding %s.html to %s.html (%d anchors)", old, new_docname, len(resolved))


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value("caravan_redirects", {}, "html")
    app.connect("build-finished", _write_stubs)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
