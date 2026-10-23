"""SC-006 of feature 006: nothing a run writes carries a compliance field or a licence claim.

Principle VI (constitution 3.0.0): Caravan carries no compliance layer and never claims to have
checked a licence, a permission or a use. Asserted on the files a whole exported run leaves behind:
no stage may add any of it on its own.

Under ``tests/train`` because producing those files needs the training framework.
"""

from __future__ import annotations

import re

import pytest

from caravan.cli.main import EXIT_OK, main
from tests.support import PILOT_FIXTURE
from tests.train.conftest import latest_run

FORBIDDEN_KEYS = (
    "compliance",
    "eu_ai_act_class",
    "privacy",
    "intended_use",
    "known_limits",
    "license",
    "permitted_use",
)
FORBIDDEN_CLAIMS = re.compile(
    r"licen[cs]e (checked|verified)|permitted for|verified licen[cs]e", re.IGNORECASE
)


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    root = tmp_path_factory.mktemp("no-compliance")
    code = main(
        [
            "export",
            str(PILOT_FIXTURE),
            "--runs-dir",
            str(root / "runs"),
            "--cache-dir",
            str(root / "cache"),
        ]
    )
    assert code == EXIT_OK
    return latest_run(root / "runs")


def test_no_file_of_the_run_carries_a_compliance_key(exported) -> None:
    offenders = []
    for path in exported.rglob("*"):
        if not path.is_file() or path.suffix in {".tflite", ".keras"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        offenders.extend(
            f"{path.name}: {key}"
            for key in FORBIDDEN_KEYS
            if re.search(rf'(^|["\s]){key}["\s]*:', text, re.MULTILINE)
        )
    assert not offenders, offenders


def test_no_file_of_the_run_claims_a_licence_was_checked(exported) -> None:
    for path in exported.rglob("*"):
        if path.is_file() and path.suffix not in {".tflite", ".keras"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert not FORBIDDEN_CLAIMS.search(text), path.name
