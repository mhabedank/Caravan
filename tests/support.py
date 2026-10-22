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

# Feature 002: the pilot manifest pointed at the one committed dataset.
PILOT_FIXTURE = VALID / "picket-mlp-fixture.yaml"
SYNTHETIC_DATASET = FIXTURES / "datasets" / "synthetic"

#: What the committed fixture is, in numbers, so a test can assert against the shape rather than
#: against whatever the file happens to contain. Changing the generator means changing these.
FIXTURE_RECORDS = 5184
FIXTURE_WINDOWS_KEPT = 80
FIXTURE_WINDOWS_DISCARDED = 1
FIXTURE_FEATURES = 5
FIXTURE_LABELS = ("dos", "fuzzy", "normal", "replay")


def invalid_cases() -> list[tuple[str, Path, dict]]:
    """Every invalid manifest fixture with the result its sibling file expects."""
    cases = []
    for manifest in sorted(INVALID.glob("*.yaml")):
        expected = json.loads(manifest.with_suffix(".expected.json").read_text(encoding="utf-8"))
        cases.append((manifest.stem, manifest, expected))
    return cases
