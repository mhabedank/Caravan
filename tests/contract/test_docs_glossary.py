"""No unexplained abbreviation, and each concept defined in one place (feature 010).

FR-018: an abbreviation is expanded at its **first use on its own page**, because a reader arrives
from a search engine in the middle of the site, not at the front door. "We use abbreviations like
MLP. What is that supposed to be?" was the complaint this answers.

The list below is what the site is allowed to use. Adding an abbreviation means adding it here with
the expansion that must accompany it, which is the point: the list is the decision, and the check
only holds the pages to it.

Abbreviations in such common use that expanding them would read as condescension — CSV, YAML, USB,
CPU, RAM, JSON, HTML, URL, API, CLI — are not in the list. The line is drawn at whether a competent
embedded developer who has never trained a model would know it.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

#: How far after a first use the expansion may still appear: roughly one sentence.
SAME_SENTENCE = 160

#: abbreviation -> a phrase that counts as expanding it, case-insensitively.
EXPANSIONS = {
    "MLP": "multilayer perceptron",
    "CNN": "convolutional neural network",
    "MAE": "mean absolute error",
    "TFLM": "TensorFlow Lite for Microcontrollers",
    "WCAG": "Web Content Accessibility Guidelines",
}

#: Pages are the published ones. docs/design/ and docs/research/ are working records, excluded from
#: the site by conf.py, and are not written for a newcomer.
def pages() -> list[Path]:
    return sorted(
        p
        for p in DOCS.rglob("*.md")
        if "design" not in p.parts and "research" not in p.parts and "_" not in p.parts[-2][:1]
    )


def _strip_code(text: str) -> str:
    """Code is not prose. An abbreviation inside a command or an identifier explains nothing, and
    demanding an expansion beside it would make the check nonsense."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def test_every_abbreviation_is_expanded_at_its_first_use() -> None:
    offenders: list[str] = []
    for page in pages():
        prose = _strip_code(page.read_text(encoding="utf-8"))
        lowered = prose.lower()
        for abbreviation, expansion in EXPANSIONS.items():
            first = re.search(rf"\b{abbreviation}\b", prose)
            if first is None:
                continue
            where = lowered.find(expansion.lower())
            if where == -1:
                offenders.append(
                    f"{page.relative_to(DOCS)} uses {abbreviation} and never expands it "
                    f"(expected {expansion!r})"
                )
            elif where > first.start() + SAME_SENTENCE:
                # Expanding it in the same breath — "CNN, which stands for convolutional neural
                # network" — is how anyone would write it, so the expansion may follow the
                # abbreviation as long as it is right there and not paragraphs later.
                offenders.append(
                    f"{page.relative_to(DOCS)} uses {abbreviation} well before expanding it, at "
                    f"character {first.start()} against {where}"
                )
    assert not offenders, "FR-018 is not met:\n  " + "\n  ".join(offenders)


def test_each_concept_is_defined_on_exactly_one_page() -> None:
    """FR-024: an explanation lives once, and other pages link to it.

    Two copies of an explanation drift, and the reader who finds the stale one has no way to know.
    So each concept page owns its subject, and the check is that no other page sets itself up as a
    second definition of the same thing by carrying the same heading.
    """
    concept_headings: dict[str, Path] = {}
    duplicates: list[str] = []
    for page in (DOCS / "concepts").glob("*.md"):
        for heading in re.findall(r"^## (.+)$", page.read_text(encoding="utf-8"), re.M):
            key = heading.strip().lower()
            if key in concept_headings:
                duplicates.append(
                    f"{heading!r} in both {concept_headings[key].name} and {page.name}"
                )
            concept_headings[key] = page
    assert not duplicates, "a concept is defined twice:\n  " + "\n  ".join(duplicates)


def test_the_concept_pages_are_reachable_from_the_route() -> None:
    """FR-024 again: an explanation nobody is sent to is an explanation nobody reads."""
    route = " ".join(p.read_text(encoding="utf-8") for p in (DOCS / "route").glob("*.md"))
    unlinked = [
        page.name
        for page in sorted((DOCS / "concepts").glob("*.md"))
        if f"concepts/{page.stem}.md" not in route
    ]
    assert not unlinked, (
        f"no leg of the route links to: {', '.join(unlinked)}. A concept page is written for the "
        f"moment a reader needs it, so something has to send them there."
    )
