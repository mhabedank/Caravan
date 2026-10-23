"""The one schema version this build implements, and the refusal of every other.

Constitution 4.0.0, Principle IX: before Caravan 1.0.0 the manifest may change without migration.
A manifest that declares a version this build does not implement — an older one, a newer one, or
none at all — is refused with rule V-1, never reinterpreted. The refusal names the implemented
version and the change note that says what to edit by hand.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: The form this build reads: declared inputs and outputs, no compliance layer (feature 006).
SCHEMA_VERSION = "caravan/v0.1"

#: Where each breaking change is described, with the edit an author makes by hand.
CHANGE_NOTE = "docs/manifest-changes.md"


class UnknownSchemaVersion(Exception):
    """The manifest declares no version, or one this build does not implement (rule V-1)."""

    def __init__(self, declared: str | None) -> None:
        self.declared = declared
        self.implemented = SCHEMA_VERSION
        super().__init__(self.problem())

    def problem(self) -> str:
        what = (
            "no schema version declared"
            if self.declared is None
            else "schema version not implemented by this build"
        )
        return (
            f"{what}; this build reads only {SCHEMA_VERSION} and does not migrate older forms "
            f"before Caravan 1.0.0 — {CHANGE_NOTE} says what to edit by hand"
        )


def check_version(data: Mapping[str, Any]) -> str:
    """Return the declared version if this build implements it; raise ``UnknownSchemaVersion``."""
    declared = data.get("apiVersion")
    if declared != SCHEMA_VERSION:
        raise UnknownSchemaVersion(None if declared is None else str(declared))
    return SCHEMA_VERSION
