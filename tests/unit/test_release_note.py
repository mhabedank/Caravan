"""The release note says what the release is, where it runs and where it stops (feature 007, US3)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTE = ROOT / "docs" / "releases" / "0.1.0.md"
SECTIONS = (
    "What it does",
    "Where it runs",
    "Known limits",
    "Change notes",
    "Release gate",
    "The pace-cnn port",
)


def sections() -> dict[str, str]:
    text = NOTE.read_text(encoding="utf-8")
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def test_every_section_is_there() -> None:
    assert list(sections()) == list(SECTIONS)


def test_at_least_four_known_limits() -> None:
    limits = re.findall(r"^- ", sections()["Known limits"], re.MULTILINE)
    assert len(limits) >= 4


def test_the_change_note_is_linked() -> None:
    assert "docs/manifest-changes.md" in sections()["Change notes"]
