"""Level 2 of the layering rule: the core works while a framework is *unimportable*.

Level 1 inspects the loaded module table, which a lazy import inside a function would slip past.
This test makes importing a framework raise and then runs the commands end to end, so a lazy
import fails the build instead of shipping.
"""

from __future__ import annotations

import importlib
import sys

import pytest

from caravan.cli.main import EXIT_OK, main
from tests.layering.test_no_framework_imported import FRAMEWORKS
from tests.support import MINIMAL, PILOT


class RefuseFrameworks:
    """A meta path finder that refuses every framework import."""

    def find_module(self, fullname, path=None):  # pragma: no cover - legacy protocol
        return None

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in FRAMEWORKS:
            raise ImportError(f"{fullname} is unimportable in this test: the core must not need it")
        return None


@pytest.fixture
def frameworks_unimportable(monkeypatch) -> None:
    for framework in FRAMEWORKS:
        for name in [m for m in list(sys.modules) if m.split(".")[0] == framework]:
            monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(sys, "meta_path", [RefuseFrameworks(), *sys.meta_path])


def test_the_hook_really_refuses(frameworks_unimportable) -> None:
    with pytest.raises(ImportError):
        importlib.import_module("tensorflow")


def test_validate_works_with_every_framework_unimportable(
    frameworks_unimportable, tmp_path, capsys
) -> None:
    assert main(["validate", str(PILOT), "--runs-dir", str(tmp_path / "runs")]) == EXIT_OK


def test_render_works_with_every_framework_unimportable(
    frameworks_unimportable, tmp_path, capsys
) -> None:
    assert main(["render", str(MINIMAL), "--runs-dir", str(tmp_path / "runs")]) == EXIT_OK
    assert next((tmp_path / "runs").glob("*/resolved-manifest.yaml")).exists()


def test_the_listings_work_with_every_framework_unimportable(
    frameworks_unimportable, capsys
) -> None:
    assert main(["templates"]) == EXIT_OK
    assert main(["boards"]) == EXIT_OK
