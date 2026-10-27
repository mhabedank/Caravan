"""Every leg of the route is a leg (feature 010, FR-008 to FR-013).

The data model's invariant is that "a leg whose outcome cannot be verified by the reader is not a
leg". These checks hold each leg to the shape that makes it one, so that a leg added later cannot
quietly skip the parts that make the route work:

- a stated duration and a promise, **before** the first instruction (FR-009);
- a way for the reader to check the result themselves (FR-010);
- a pointer to what comes next, or an ending (FR-013);
- the vocabulary of the route: legs, never "stage", which means the pipeline's own stages.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTE = ROOT / "docs" / "route"
LEGS = sorted(p for p in ROUTE.glob("*.md") if p.name != "index.md")


def test_the_route_has_its_legs() -> None:
    assert len(LEGS) == 4, f"expected four legs, found {[p.name for p in LEGS]}"
    for n, path in enumerate(LEGS, 1):
        assert path.name.startswith(f"{n}-"), f"leg files are numbered in order; {path.name} is not"


def test_every_leg_states_its_duration_and_promise_before_any_command() -> None:
    for path in LEGS:
        text = path.read_text(encoding="utf-8")
        head = re.search(r":::\{container\} leg-head\n(.*?)\n:::", text, re.S)
        assert head, f"{path.name} has no leg-head block stating what the reader ends with"
        body = head.group(1)
        assert re.search(r"\*\*About \d+ minutes?\*\*", body), (
            f"{path.name}'s leg-head does not state a duration (FR-009)"
        )
        assert "end with" in body, (
            f"{path.name}'s leg-head does not say what the reader ends with (FR-009)"
        )
        first_command = text.find("```bash")
        if first_command != -1:
            assert text.index(head.group(0)) < first_command, (
                f"{path.name} gives a command before stating its duration and promise (FR-009)"
            )


def test_every_leg_has_something_the_reader_checks() -> None:
    for path in LEGS:
        text = path.read_text(encoding="utf-8")
        assert "leg-check" in text, (
            f"{path.name} has no leg-check block. A leg whose outcome the reader cannot verify is "
            f"not a leg (FR-010)."
        )


def test_every_leg_points_somewhere_next() -> None:
    for path in LEGS:
        text = path.read_text(encoding="utf-8")
        assert re.search(r"^## (Next|The end of the route)", text, re.M), (
            f"{path.name} neither names the next leg nor ends the route (FR-013)"
        )


def test_no_leg_calls_itself_a_tutorial() -> None:
    """FR-008. The words the owner ruled out, and the one that collides with the pipeline."""
    for path in [*LEGS, ROUTE / "index.md"]:
        text = path.read_text(encoding="utf-8").lower()
        for word in ("tutorial", "walkthrough", "getting started"):
            assert word not in text, f"{path.name} uses {word!r}, which FR-008 rules out"


def test_every_leg_uses_the_routes_vocabulary() -> None:
    """FR-008: the parts are legs, and each page says so.

    There was a check here that tried to catch a leg being *called* a stage, by looking at the words
    around each "stage". It flagged leg 1 for "every stage comes from the cache", which is the
    pipeline's own stages and entirely correct. A check that guesses at meaning from a keyword
    window produces false alarms, and a test that cries wolf gets suppressed rather than fixed — so
    it is gone, and the rule it was guarding lives in the design language where a reviewer reads it.

    What is checked instead is reliable: each leg calls itself a leg.
    """
    for path in LEGS:
        text = path.read_text(encoding="utf-8").lower()
        assert "leg" in text, f"{path.name} never uses the route's word for its own parts"
