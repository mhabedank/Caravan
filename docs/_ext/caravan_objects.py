"""The four kinds of thing a page can link to by name.

A manifest field, a CLI command, a validation rule and a board each have one entry, on their
reference page, and every other page links to that entry by the thing's name, the way Django's
documentation links ``django.db.models.Model``. Sphinx has this built in: ``add_object_type``
gives a kind its declaring directive, its role, its anchor and its line in the generated index.

Declared on a reference page::

    :::{manifest-field} export.targets
    **Type** list of board identifiers · **Default** required
    ...
    :::

Linked from running text with ``{mf}`export.targets```. With ``nitpicky`` on and ``-W``, a name
that has no entry fails the build and names the page, so a link cannot rot silently.

Owning these lines rather than adding a domain package is Principle XII: the whole mechanism is the
table below.
"""

from __future__ import annotations

from typing import Any

from sphinx.application import Sphinx

#: kind (directive), role, what the generated index calls it
KINDS = [
    ("manifest-field", "mf", "manifest field"),
    ("cli", "cmd", "CLI command"),
    ("rule", "rule", "validation rule"),
    ("board", "board", "board"),
]


def setup(app: Sphinx) -> dict[str, Any]:
    for directive, role, label in KINDS:
        app.add_object_type(
            directive,
            role,
            indextemplate=f"single: %s ({label})",
            objname=label,
        )
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
