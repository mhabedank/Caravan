"""The accessibility claim, measured on the rendered page (feature 010, FR-034, SC-012).

SC-012 asks for an audit "measured on the rendered page, not computed from the palette", and the
reason is in the zoo's own identity work: a palette table cannot see text over an image, a focus
ring, a control whose contrast comes from a border, or a heading level skipped in the middle of a
long page. Those are where real failures are.

So the built site is driven in a headless browser, a vendored ruleset is injected into each page,
and every page is checked at the A and AA levels **in both colour schemes**. Dark mode is not an
afterthought here and is not allowed to be an untested one either.

Skipped, rather than failed, when the browser or the built site is absent: this needs a browser
binary and `_site/`, and a contributor running the unit tests on a laptop should not be told their
checkout is broken. Continuous integration builds both, so the check is real where it matters
(`.github/workflows/docs-checks.yml`).

The browser binary: by default Playwright finds its own. ``CARAVAN_CHROMIUM`` overrides the path,
which is what a sandbox with a preinstalled browser needs — a Playwright that installed its own
copy will not find one placed elsewhere.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "_site"
AXE = Path(__file__).resolve().parent / "vendor" / "axe.min.js"

#: WCAG 2.0 and 2.1, levels A and AA. The same set the zoo checks against.
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

#: Both schemes, because the identity defines both and neither is derived from the other.
SCHEMES = ["light", "dark"]


def pages() -> list[Path]:
    """Every page a reader reads.

    The forwarding stubs are excluded, and not for convenience: each one carries a zero-second meta
    refresh, so the browser navigates away before a ruleset can be injected — "Execution context
    was destroyed" is what auditing one looks like. There is also nothing to audit. A stub has no
    content by design, which is the same property that lets a forward exist from the withdrawn
    board's address without that board appearing on the site. That they *are* forwards, and are
    noindex and in no navigation, is checked in ``tests/contract/test_docs_hygiene.py``.
    """
    out = []
    for path in sorted(SITE.rglob("*.html")):
        if "_static" in path.parts:
            continue
        if 'http-equiv="refresh"' in path.read_text(encoding="utf-8"):
            continue
        out.append(path)
    return out


def _browser_kwargs() -> dict:
    override = os.environ.get("CARAVAN_CHROMIUM")
    return {"executable_path": override} if override else {}


@pytest.fixture(scope="module")
def findings() -> dict[str, list[dict]]:
    """Every page, in both schemes, audited once."""
    if not SITE.is_dir() or not pages():
        pytest.skip(f"no built site at {SITE}; run sphinx-build first")
    playwright = pytest.importorskip("playwright.sync_api", reason="the site-checks group")
    axe = AXE.read_text(encoding="utf-8")

    out: dict[str, list[dict]] = {}
    with playwright.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(**_browser_kwargs())
        except Exception as error:
            pytest.skip(f"no usable chromium: {error}")
        try:
            for scheme in SCHEMES:
                context = browser.new_context(color_scheme=scheme)
                page = context.new_page()
                for path in pages():
                    page.goto(path.resolve().as_uri(), wait_until="load")
                    page.add_script_tag(content=axe)
                    result = page.evaluate(
                        "tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})"
                        ".then(r => r.violations)",
                        TAGS,
                    )
                    key = f"{path.relative_to(SITE)} [{scheme}]"
                    out[key] = result
                context.close()
        finally:
            browser.close()
    return out


def test_every_page_passes_at_a_and_aa_in_both_schemes(findings) -> None:
    broken = {where: v for where, v in findings.items() if v}
    if not broken:
        return
    report = []
    for where, violations in sorted(broken.items()):
        for violation in violations:
            targets = ", ".join(str(node.get("target")) for node in violation.get("nodes", [])[:3])
            report.append(
                f"{where}\n    {violation['id']} ({violation['impact']}): "
                f"{violation['help']}\n    at {targets}"
            )
    pytest.fail(
        "the rendered site has accessibility violations at level A or AA:\n"
        + "\n".join(report)
        + f"\n\n{len(broken)} of {len(findings)} page/scheme combinations affected."
    )


def test_both_schemes_were_actually_audited(findings) -> None:
    """A check that silently audited one scheme twice would pass while proving half of nothing."""
    for scheme in SCHEMES:
        assert any(f"[{scheme}]" in key for key in findings), f"{scheme} was never audited"


def test_the_ruleset_is_the_vendored_one(findings) -> None:
    """Pinned on purpose: a ruleset that moves under the check changes the answer on an unchanged
    page, and then nobody can tell a regression from an upgrade."""
    assert AXE.is_file(), "the vendored ruleset is missing"
    head = AXE.read_text(encoding="utf-8")[:400]
    assert "axe-core 4.14.0" in head, (
        "the vendored ruleset is not the pinned version. Upgrading it is a deliberate change of "
        "its own, because a new version can report findings the previous one did not."
    )


def test_no_page_scrolls_sideways_at_phone_width(findings) -> None:
    """FR-035 and SC-012: nothing clipped and no sideways scroll at phone width or 200% zoom.

    Measured as the document being wider than the viewport, which is what a reader experiences as
    the page sliding under their thumb. 390x844 is a common phone; the 200% case is modelled by
    halving the viewport, which is what a browser's page zoom does to the layout.
    """
    if not SITE.is_dir() or not pages():
        pytest.skip("no built site")
    playwright = pytest.importorskip("playwright.sync_api")
    offenders: list[str] = []
    with playwright.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(**_browser_kwargs())
        except Exception as error:
            pytest.skip(f"no usable chromium: {error}")
        try:
            for width, label in ((390, "phone"), (195, "phone at 200% zoom")):
                context = browser.new_context(viewport={"width": width, "height": 844})
                page = context.new_page()
                for path in pages():
                    page.goto(path.resolve().as_uri(), wait_until="load")
                    overflow = page.evaluate(
                        "() => document.documentElement.scrollWidth - "
                        "document.documentElement.clientWidth"
                    )
                    if overflow > 1:  # a pixel of rounding is not a sideways scroll
                        offenders.append(
                            f"{path.relative_to(SITE)} at {label} ({width}px): "
                            f"{overflow}px too wide"
                        )
                context.close()
        finally:
            browser.close()
    assert not offenders, "pages scroll sideways:\n  " + "\n  ".join(offenders)


def test_findings_are_reportable(findings) -> None:
    """The audit must produce something a person can read, not only a pass or fail."""
    assert json.dumps(findings) is not None
