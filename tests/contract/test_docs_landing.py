"""The landing page keeps its promises, and the header's links go somewhere (feature 010).

The landing page is the one page with a measurable job: a reader who sees it for five seconds should
know what Caravan produces, what it costs them, and what to do next (SC-001, SC-002). None of that
can be asserted here — it needs readers. What *can* be held is the structure the job rests on, and
these are the parts that would quietly rot:

- exactly one primary call to action, labelled with a duration (FR-003);
- the install's weight stated before a reader commits to it (FR-002);
- the supported platforms named on the way in, so a reader on Windows learns it here (FR-002);
- scope after the benefit rather than before it (FR-004);
- the header's curated links each resolving to a page that exists.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
LANDING = DOCS / "index.md"


def landing() -> str:
    return LANDING.read_text(encoding="utf-8")


def test_exactly_one_primary_call_to_action() -> None:
    """`.btn` is the primary style. Two primary steps are no primary step."""
    text = landing()
    buttons = re.findall(r"\{\.btn[^}]*\}", text)
    assert len(buttons) == 1, (
        f"the landing page has {len(buttons)} primary calls to action; FR-003 allows exactly one"
    )


def test_the_call_to_action_names_a_duration() -> None:
    text = landing()
    assert re.search(r"\{\.btn[^}]*\}[^\n]*", text), "no primary call to action found"
    # The duration may sit beside the button rather than inside it; what matters is that a reader
    # sees how long the way in takes before taking it.
    assert re.search(r"\b15 minutes\b", text), (
        "the landing page does not say how long the first leg takes (FR-003)"
    )


def test_the_install_weight_is_stated() -> None:
    """FR-002: the 2 GB download is the longest wait in the half hour and must not be a surprise."""
    text = landing()
    assert re.search(r"\b2 GB\b", text), (
        "the landing page does not state the install's download weight. The fifteen-minute claim "
        "is measured with the install already done, so hiding its size would make the claim a lie."
    )


def test_the_platforms_are_named() -> None:
    """FR-002 and the Windows edge case: a reader learns this before spending anything."""
    text = landing()
    assert "Linux" in text and "macOS" in text, "the landing page does not name the platforms"
    assert "Windows" in text, (
        "the landing page does not mention Windows. A reader there must learn it on the way in, "
        "not after a failed install."
    )


def test_python_version_is_stated() -> None:
    assert "3.13" in landing(), "the landing page does not say which Python training needs"


def test_scope_comes_after_the_benefit() -> None:
    """FR-004: the first thing stated emphatically must not be what Caravan refuses to do."""
    text = landing()
    benefit = text.index("## What you bring")
    scope = text.index("## What Caravan is for")
    assert benefit < scope, (
        "the scope section comes before the benefit. FR-004 puts it after: a visitor should learn "
        "what Caravan does for them before what it declines to do."
    )


def test_every_header_link_resolves() -> None:
    """The header is curated in conf.py, which is a list that can rot. This is why it cannot."""
    conf = (DOCS / "conf.py").read_text(encoding="utf-8")
    block = re.search(r'"nav_pages":\s*\[(.*?)\]', conf, re.S)
    assert block, "conf.py no longer defines nav_pages for the theme's header"
    pages = re.findall(r'\(\s*"([^"]+)"\s*,\s*"[^"]*"\s*\)', block.group(1))
    assert pages, "nav_pages is empty"
    for docname in pages:
        assert (DOCS / f"{docname}.md").is_file(), (
            f"the header links {docname!r}, which is not a page. Either the page was renamed or "
            f"the list in conf.py was not updated with it."
        )
