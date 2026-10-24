"""The identifiers feature 006 retired stay retired.

CF-3, CF-5, CF-7, CF-8 and DS-9 belonged to the compliance layer or to the section of a stage that
does not exist yet. V-2 read a manifest without a version as the oldest known one, which
constitution 4.0.0 forbids. CF-10 allowed one input and one output; feature 008 allows several
input features and gives the single output its own rule, CF-17. Reusing one would make an old run report mean something it never
meant, so the identifiers are reserved: in no rule group, in no fixture's expectation, raised by no
module.
"""

from __future__ import annotations

import json
from pathlib import Path

from caravan.manifest import errors
from caravan.manifest.errors import ALL_RULES, RETIRED_RULES

ROOT = Path(__file__).resolve().parents[2]


def test_the_seven_identifiers_are_retired() -> None:
    assert {"CF-3", "CF-5", "CF-7", "CF-8", "CF-10", "DS-9", "V-2"} == RETIRED_RULES


def test_no_retired_identifier_is_in_a_rule_group() -> None:
    assert not RETIRED_RULES & ALL_RULES


def test_no_rule_constant_carries_a_retired_identifier() -> None:
    constants = {
        name: value
        for name, value in vars(errors).items()
        if name.startswith("RULE_") and isinstance(value, str)
    }
    assert not {name for name, value in constants.items() if value in RETIRED_RULES}


def test_no_fixture_expects_a_retired_identifier() -> None:
    expectations = (ROOT / "tests" / "fixtures").rglob("*.expected.json")
    claimed = {
        path.name: json.loads(path.read_text(encoding="utf-8")).get("rule") for path in expectations
    }
    assert not {name for name, rule in claimed.items() if rule in RETIRED_RULES}


def test_no_source_module_names_a_retired_identifier() -> None:
    offenders = []
    for path in (ROOT / "src" / "caravan").rglob("*.py"):
        if path.name == "errors.py":
            continue  # the reservation itself
        text = path.read_text(encoding="utf-8")
        offenders.extend(f"{path.name}: {rule}" for rule in RETIRED_RULES if f'"{rule}"' in text)
    assert not offenders, offenders
