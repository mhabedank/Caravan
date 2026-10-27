"""The site is the project's own face (feature 010, FR-039, FR-043, FR-045).

Three things a reader must not meet, each of which is easy to reintroduce in a sentence:

- the owner's personal development board, which came off the site (D2);
- the project's internal development artifacts — spec directories, feature numbers, plan, task and
  analysis files — which are how Caravan is built and not what a reader came for;
- a dead address, where a page was renamed or removed and nothing forwards from it.

These are checked against the built site where that exists, and against the sources otherwise, so
the check is useful on a laptop and exact in continuous integration.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SITE = ROOT / "_site"

#: The withdrawn board, in every spelling it was ever written in.
BOARD = re.compile(r"lora\s?32|lilygo|ttgo", re.I)

#: How Caravan is built. A reader did not come for this.
INTERNAL = re.compile(
    r"\bfeatures?\s+\d{3}\b"  # "feature 009"
    r"|\bspecs?/\d{3}-"  # "specs/010-website-overhaul/"
    r"|\bresearch\s+R\d+\b"  # "research R5"
    r"|\b(?:FR|SC)-\d{3}\b"  # requirement identifiers
    r"|\bT\d{3}\b"  # task identifiers
    r"|\btasks\.md\b|\bplan\.md\b|\bspec\.md\b|\banalysis\.md\b"
    r"|constitution\s+v?\d+\.\d+",  # "constitution 4.0.0"
    re.I,
)


def published_sources() -> list[Path]:
    """The pages. docs/design/ and docs/research/ are working records, excluded by conf.py."""
    return sorted(
        p
        for p in DOCS.rglob("*.md")
        if "design" not in p.parts and "research" not in p.parts and not p.parts[-2].startswith("_")
    )


def built_pages() -> list[Path]:
    if not SITE.is_dir():
        return []
    return sorted(p for p in SITE.rglob("*.html") if "_static" not in p.parts)


def test_the_withdrawn_board_is_not_on_any_page() -> None:
    """FR-039, SC-010."""
    offenders = []
    for page in published_sources():
        for match in BOARD.finditer(page.read_text(encoding="utf-8")):
            offenders.append(f"{page.relative_to(DOCS)}: {match.group(0)!r}")
    assert not offenders, (
        "the withdrawn board is back on the site:\n  "
        + "\n  ".join(offenders)
        + "\n\nIt stays in the repository (examples/lora32/) and off the site."
    )


def test_the_withdrawn_board_is_not_in_any_built_page() -> None:
    """The same, on the published HTML, which is what a reader and a search engine see.

    The forward from its old address is exempt: its *path* carries the name, its content does not,
    and a zero-second redirect is not a page anybody reads (research R6 of this feature).
    """
    pages = built_pages()
    if not pages:
        import pytest

        pytest.skip("no built site; run sphinx-build first")
    offenders = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        if 'http-equiv="refresh"' in text:
            continue
        for match in BOARD.finditer(text):
            offenders.append(f"{page.relative_to(SITE)}: {match.group(0)!r}")
    assert not offenders, "the built site names the withdrawn board:\n  " + "\n  ".join(offenders)


def test_no_page_references_how_the_project_is_built() -> None:
    """FR-043, SC-011."""
    offenders = []
    for page in published_sources():
        for match in INTERNAL.finditer(page.read_text(encoding="utf-8")):
            offenders.append(f"{page.relative_to(DOCS)}: {match.group(0)!r}")
    assert not offenders, (
        "published pages cite the project's internal artifacts:\n  "
        + "\n  ".join(offenders)
        + "\n\nA reader cannot open these and did not come for them. Say what the site itself can "
        "show instead."
    )


def test_every_address_that_moved_still_resolves() -> None:
    """FR-045, SC-013: a renamed page keeps its old address working."""
    conf = (DOCS / "conf.py").read_text(encoding="utf-8")
    block = re.search(r"caravan_redirects: dict\[str, str\] = \{(.*?)\n\}", conf, re.S)
    assert block, "conf.py no longer defines the redirect map"
    pairs = re.findall(r'"([^"]+)":\s*"([^"]+)"', block.group(1))
    assert pairs, "the redirect map is empty, though pages were renamed"
    for old, new in pairs:
        assert (DOCS / f"{new}.md").is_file(), (
            f"{old!r} forwards to {new!r}, which is not a page. A forward to nothing is worse than "
            f"a dead address: it claims to have been fixed."
        )
        assert not (DOCS / f"{old}.md").is_file(), (
            f"{old!r} both forwards and still exists as a page"
        )


def test_every_forward_is_a_forward_and_nothing_else() -> None:
    """A stub is noindex, carries no content, and is in no navigation."""
    pages = built_pages()
    if not pages:
        import pytest

        pytest.skip("no built site")
    stubs = [p for p in pages if 'http-equiv="refresh"' in p.read_text(encoding="utf-8")]
    assert stubs, "no forwarding stubs were written, though pages were renamed"
    for stub in stubs:
        text = stub.read_text(encoding="utf-8")
        assert "noindex" in text, f"{stub.relative_to(SITE)} is not noindex"
        assert 'rel="canonical"' in text, f"{stub.relative_to(SITE)} has no canonical link"
        assert len(text) < 800, (
            f"{stub.relative_to(SITE)} has grown content. A forward carries none, which is what "
            f"lets one exist from an address naming something the site no longer mentions."
        )
