"""Paths and helpers shared by the test suites."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "manifests" / "valid"
INVALID = FIXTURES / "manifests" / "invalid"
BOARDS = FIXTURES / "boards"

PILOT = VALID / "picket-mlp.yaml"
MINIMAL = VALID / "pilot-min.yaml"
NO_VERSION = VALID / "v-2-no-version.yaml"


def invalid_cases() -> list[tuple[str, Path, dict]]:
    """Every invalid manifest fixture with the result its sibling file expects."""
    cases = []
    for manifest in sorted(INVALID.glob("*.yaml")):
        expected = json.loads(manifest.with_suffix(".expected.json").read_text(encoding="utf-8"))
        cases.append((manifest.stem, manifest, expected))
    return cases
