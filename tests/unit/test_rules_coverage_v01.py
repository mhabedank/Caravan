"""Every rule features 006 and 007 added is raised by the code and provoked by a test.

The same shape as the coverage tests of the DS, Q and X rules: a rule nobody raises is a promise
nobody keeps, and a rule no test provokes is a rule nobody has seen fire.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from caravan.manifest import errors

ROOT = Path(__file__).resolve().parents[2]
NEW_RULES = ("CF-9", "CF-10", "CF-11", "DS-11", "DS-12", "F-1", "X-6", "CF-12", "CF-13", "DS-13")


def constant_for(rule: str) -> str:
    return next(
        name for name, value in vars(errors).items() if name.startswith("RULE_") and value == rule
    )


def text_of(directory: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in directory.rglob("*.py"))


@pytest.mark.parametrize("rule", NEW_RULES)
def test_the_rule_is_raised_by_the_code(rule: str) -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src" / "caravan").rglob("*.py")
        if path.name != "errors.py"
    )
    name = constant_for(rule)
    assert name in sources, f"{rule} ({name}) is defined but nothing raises it"


@pytest.mark.parametrize("rule", NEW_RULES)
def test_the_rule_is_provoked_by_a_test(rule: str) -> None:
    tests = text_of(ROOT / "tests")
    fixtures = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "tests" / "fixtures").rglob("*.expected.json")
    )
    name = constant_for(rule)
    provoked = name in tests.replace(Path(__file__).read_text(encoding="utf-8"), "")
    assert provoked or f'"{rule}"' in fixtures, f"no test provokes {rule}"
