"""Every figure about hardware carries its provenance (Principle IV, FR-006, SC-016).

The constitution is explicit and makes no exception for a marketing page: a number about a model's
behaviour on hardware carries exactly one of `estimated`, `emulated` or `measured`, the label
appears wherever the number appears, and *a number without a label must not be rendered*. A landing
page is a published table for this purpose.

This is a shallow check and says so. It cannot tell a figure about hardware from any other number,
so it holds the pages to the parts that can be checked mechanically: the three labels are used with
their meanings, no page claims a timing measurement, and the pages that carry hardware figures
carry labels beside them.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

LABELS = ("estimated", "emulated", "measured")

#: Pages that state figures about hardware, and must therefore label them.
MUST_LABEL = (
    "compatibility.md",
    "route/3-onto-a-board.md",
    "board-runs/index.md",
)


def pages() -> list[Path]:
    return sorted(
        p
        for p in DOCS.rglob("*.md")
        if "design" not in p.parts and "research" not in p.parts and not p.parts[-2].startswith("_")
    )


def test_the_pages_with_hardware_figures_carry_labels() -> None:
    for name in MUST_LABEL:
        text = (DOCS / name).read_text(encoding="utf-8")
        assert any(label in text for label in LABELS), (
            f"{name} states figures about hardware and uses none of {LABELS}. Principle IV: a "
            f"number without a label must not be rendered."
        )


def test_no_page_claims_a_measured_timing() -> None:
    """Principle IV: latency, throughput and energy are `measured` only from a physical board.

    Caravan has no benchmark yet, so the honest state is that no timing figure appears at all. The
    check is for the day somebody adds one from an emulator or an estimate.
    """
    offenders = []
    timing = re.compile(
        r"(\d[\d.,]*\s*(?:ms|µs|us|microseconds?|milliseconds?|fps|inferences?/s|Hz))", re.I
    )
    for page in pages():
        text = page.read_text(encoding="utf-8")
        for match in timing.finditer(text):
            window = text[max(0, match.start() - 200) : match.end() + 200]
            if "measured" in window:
                offenders.append(f"{page.relative_to(DOCS)}: {match.group(0)!r} near 'measured'")
    assert not offenders, (
        "a timing figure is presented as measured:\n  "
        + "\n  ".join(offenders)
        + "\n\nTiming comes from a hardware benchmark following a public protocol, and Caravan has "
        "none yet."
    )


def test_the_linker_figures_are_estimated() -> None:
    """Leg 3 prints the linker's RAM and flash. A linker is not a board."""
    text = (DOCS / "route" / "3-onto-a-board.md").read_text(encoding="utf-8")
    assert "RAM:" in text and "Flash:" in text, "leg 3 no longer shows the build's figures"
    where = text.index("RAM:")
    window = text[where : where + 900]
    assert "estimated" in window, (
        "leg 3 shows the linker's figures without labelling them estimated. They are not a "
        "measurement on a board, and the page has to say so where the numbers are."
    )


def test_the_arena_figure_is_the_one_measurement() -> None:
    """The runtime's own report of what it used is `measured`, because it ran on the device."""
    text = (DOCS / "route" / "3-onto-a-board.md").read_text(encoding="utf-8")
    assert "arena" in text, "leg 3 no longer reports the working memory the runtime used"
    assert re.search(r"arena[^\n]*measured", text), (
        "the arena figure is not labelled measured. It comes from the runtime on the board, which "
        "is what makes it the one measurement in the leg."
    )


# A check was here that tried to hold every use of "emulated" and "measured" to being a provenance
# claim, by looking at the words around it. It flagged budgets.md for "a development container
# measured 2,017 MiB" — the ordinary English verb, about install size, nothing to do with hardware.
#
# "Measured" is a common word and a context window cannot tell the two apart. A check that cries
# wolf gets suppressed rather than fixed, so it is gone. What replaces it is narrower and exact:
# the four checks above hold the pages that actually carry hardware figures, and the rendered
# labels are `<span class="prov ...">`, which the accessibility audit sees as real elements.
