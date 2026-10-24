"""Level 2 of the layering rule: the core works while a framework is *unimportable*.

Level 1 inspects the loaded module table, which a lazy import inside a function would slip past.
This test makes importing a framework raise and then runs the commands end to end, so a lazy
import fails the build instead of shipping.
"""

from __future__ import annotations

import importlib
import sys

import pytest

from caravan.cli.main import EXIT_ENVIRONMENT, EXIT_OK, main
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


def test_building_the_template_registry_reaches_no_builder(frameworks_unimportable) -> None:
    # Feature 002. The registry's discovery walks ``caravan.templates``, and the builder half of
    # every template lives in a subpackage of it. If that walk ever stopped skipping subpackages,
    # a framework would be imported here — on an installation that may not have one.
    from caravan.templates.registry import build_registry

    registry = build_registry()
    assert "mlp" in registry.identifiers
    assert "caravan.templates.builders.mlp" not in sys.modules


def test_the_stage_modules_import_with_every_framework_unimportable(
    frameworks_unimportable,
) -> None:
    # A stage loads its framework-bearing parts by name when it runs, so importing the stage
    # itself has to work where no framework exists — otherwise ``caravan validate`` would break
    # the moment the command line grew a stage verb.
    for name in (
        "caravan.stages.build",
        "caravan.stages.train",
        "caravan.stages.cache",
        # Feature 006: the two internal stages, the fit arithmetic, the interface emitters and the
        # schema's new modules — all core, all importable where no framework can be.
        "caravan.stages.data",
        "caravan.stages.fit",
        "caravan.targets.fit",
        "caravan.export.interface",
        "caravan.manifest.schema.removed",
        "caravan.manifest.version",
        # Feature 008: the typed features, the fitting and the regression metrics are core too.
        "caravan.manifest.schema.features",
        "caravan.manifest.schema.preprocessing",
        "caravan.manifest.schema.trainer",
        "caravan.data.fit",
        "caravan.data.reader_bridge",
        "caravan.metrics.regression",
    ):
        monkey = importlib.import_module(name)
        assert monkey is not None


def test_the_quantize_stage_answers_rather_than_failing_to_import(
    frameworks_unimportable, tmp_path, capsys
) -> None:
    # Feature 003. Quantizing needs two separately installed parts, so there are two ways for the
    # environment to be incomplete and neither may arrive as an ImportError.
    code = main(
        [
            "quantize",
            str(PILOT),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == EXIT_ENVIRONMENT
    err = capsys.readouterr().err
    assert "Traceback" not in err
    # Which of the two messages appears depends on the interpreter the suite runs on: on a Python
    # a part publishes for, the install command; above it, the window and the reason. Asserting
    # only the first would make this test pass on 3.13 and fail on 3.15 for being right.
    assert ("extra" in err) or ("no wheel for Python" in err)


def test_the_runtime_modules_import_with_every_framework_unimportable(
    frameworks_unimportable,
) -> None:
    # ``caravan.runtime.inspect`` imports its runtime inside a function, which is what lets a
    # stage reference it without a guard. If that ever became a module-level import, importing a
    # stage in a default installation would break — and the layering tests would say so here.
    import importlib

    for name in ("caravan.runtime.inspect", "caravan.stages.quantize"):
        assert importlib.import_module(name) is not None


def test_the_stage_verbs_answer_rather_than_fail_to_import(
    frameworks_unimportable, tmp_path, capsys
) -> None:
    # The whole point of exit code 4: with the framework not merely absent but *unimportable*,
    # the user gets a sentence and a status, never an ImportError.
    for verb in ("build", "train"):
        code = main(
            [
                verb,
                str(PILOT),
                "--runs-dir",
                str(tmp_path / verb),
                "--cache-dir",
                str(tmp_path / "cache"),
            ]
        )
        assert code == EXIT_ENVIRONMENT
    err = capsys.readouterr().err
    assert "Traceback" not in err
