"""The identity is in the tokens, and the accent is reserved (feature 010).

`contracts/design-tokens.md` makes three promises that are easy to break by accident and
impossible to notice by eye:

- no interface colour is declared outside the token file, so a later change of identity is an edit
  to one file rather than a hunt through the pages (FR-028);
- both colour schemes define the same tokens, so neither is an afterthought (FR-033);
- the single warm accent is reserved for the budget and its verdict, and used nowhere else
  (FR-029, D4).

The last one is the reason this file exists. A reservation that nothing enforces is a preference,
and the first person who wants an emphasis colour will reach for the warm one.
"""

from __future__ import annotations

import re
from pathlib import Path

THEME = Path(__file__).resolve().parents[2] / "docs" / "_themes" / "caravan"
TOKENS = THEME / "static" / "tokens.css"
SITE_CSS = THEME / "static" / "site.css"

#: The accent may be read by these and nothing else. `.budget` is a figure that must fit; `.verdict`
#: is the gate's answer about whether it did.
ACCENT_READERS = {".budget", ".verdict"}

#: Inks shared by both schemes: a printed surface does not turn over, so these are declared once.
SHARED_INKS = {
    "--poster-navy",
    "--poster-cream",
    "--poster-mint",
    "--poster-orange",
    "--mark-accent",
}


def _declarations(block: str) -> dict[str, str]:
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", block))


def schemes() -> tuple[dict[str, str], dict[str, str]]:
    text = TOKENS.read_text(encoding="utf-8")
    light = _declarations(re.search(r":root \{(.*?)\n\}", text, re.S).group(1))
    dark_block = re.search(
        r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(.*?)\n  \}", text, re.S
    )
    assert dark_block, "tokens.css no longer defines a dark scheme"
    return light, _declarations(dark_block.group(1))


def test_no_colour_literal_outside_the_token_file() -> None:
    """FR-028. The stylesheet reads tokens; it does not mint colours of its own."""
    literals = re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(", SITE_CSS.read_text(encoding="utf-8"))
    assert not literals, (
        f"site.css declares colours directly: {literals[:5]}. Every interface colour belongs in "
        f"tokens.css, so that changing the identity is one file."
    )


def test_the_site_serves_no_third_party_stylesheet() -> None:
    """Sphinx links its own pygments.css, fifty-odd literals against an identity with four inks.

    `docs/_ext/identity.py` stops it. Without that, FR-030 is unenforceable: an element would take
    a colour the identity does not have and no check here would see it, because the colour is not
    in our files at all.
    """
    extension = (THEME.parents[1] / "_ext" / "identity.py").read_text(encoding="utf-8")
    assert "_static/pygments.css" in extension, (
        "the identity extension no longer drops pygments.css, so the site serves a stylesheet of "
        "about fifty literal colours that the identity does not contain"
    )


def test_both_schemes_define_the_same_tokens() -> None:
    """FR-033: neither scheme is derived from the other, so neither may be missing a value."""
    light, dark = schemes()
    missing_in_dark = sorted(set(light) - set(dark) - SHARED_INKS)
    extra_in_dark = sorted(set(dark) - set(light))
    assert not missing_in_dark, (
        f"the dark scheme does not define: {missing_in_dark}. A token that falls back to the light "
        f"value is how a dark page ends up with a light surface."
    )
    assert not extra_in_dark, (
        f"the dark scheme defines tokens the light one does not: {extra_in_dark}"
    )


def test_the_accent_is_reserved() -> None:
    """FR-029: the budget and its verdict, and nothing else on the site."""
    css = SITE_CSS.read_text(encoding="utf-8")
    offenders: list[str] = []
    for rule in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        selector, body = rule.group(1).strip(), rule.group(2)
        if "var(--accent-use)" not in body:
            continue
        if not any(reader in selector for reader in ACCENT_READERS):
            offenders.append(selector.splitlines()[-1].strip())
    assert not offenders, (
        f"these rules read the reserved accent: {offenders}. It is reserved for the budget and its "
        f"verdict (contracts/design-tokens.md); an emphasis colour has to come from somewhere else."
    )


def test_no_token_the_stylesheet_reads_is_the_reserved_ink() -> None:
    """The reservation has to hold in both schemes, which is where it nearly did not.

    The copied identity sets its dark `--accent` to the warm ink, and Caravan uses `--accent` for
    the primary button, the skip link and the navigation hover — so in dark mode the reserved
    colour was on every page, most visible exactly where the reservation mattered. A check for
    `--accent-use` could not see it, because the rules read `--accent`.

    The rule is not "no token may hold that value": `--poster-orange` *is* the ink, and `--s-c` is
    an unused series colour the copy came with. What matters is whether a token holding it is
    **read by the stylesheet**, because only then does the colour reach a page.

    `--focus` is the deliberate exception: a focus ring is an accessibility affordance rather than
    content emphasis, and it has to be the most visible thing on the page.
    """
    css = SITE_CSS.read_text(encoding="utf-8")
    read_by_css = set(re.findall(r"var\((--[a-z0-9-]+)", css))
    allowed = {"--accent-use", "--mark", "--focus"}
    light, dark = schemes()
    for name, scheme in (("light", light), ("dark", {**light, **dark})):
        warm = scheme["--mark"]
        offenders = sorted(
            token
            for token, value in scheme.items()
            if token in read_by_css and token not in allowed and value.lower() == warm.lower()
        )
        assert not offenders, (
            f"in the {name} scheme these tokens hold the reserved ink {warm} and are read by "
            f"site.css: {offenders}. Every rule reading one of them puts the budget's colour "
            f"somewhere it does not belong."
        )


def test_the_accent_is_actually_used_for_what_it_is_reserved_for() -> None:
    """A reservation nothing uses is a token nobody will remember the meaning of."""
    css = SITE_CSS.read_text(encoding="utf-8")
    assert "var(--accent-use)" in css, "nothing uses --accent-use, so its reservation means nothing"


def test_the_typefaces_carry_their_notice() -> None:
    """OFL-1.1 permits the copy and requires the notice to travel with it (FR-028)."""
    fonts = THEME / "static" / "fonts"
    assert (fonts / "OFL.txt").is_file(), "the typefaces are copied without their licence notice"
    faces = sorted(p.name for p in fonts.glob("*.woff2"))
    assert len(faces) == 2, f"expected the two typefaces, found {faces}"


def test_the_origin_of_the_identity_is_recorded() -> None:
    """FR-028: where it came from, and that nothing keeps the two in step."""
    header = TOKENS.read_text(encoding="utf-8")[:2000]
    assert "Mobility Model Zoo" in header, "tokens.css does not record where the identity came from"
    assert "drift" in header, (
        "tokens.css does not record that the two identities may drift. Someone will otherwise "
        "treat a divergence as a bug to fix."
    )
