"""Level 1 of the layering rule: nothing in the core loads a training framework.

Principle XII. Checking and resolving a manifest does not need a machine-learning framework, so
the core must not reach one — and that has to be a property the build enforces, not a convention
somebody remembers.
"""

from __future__ import annotations

import ast
import json
import pkgutil
import subprocess
import sys
from pathlib import Path

import caravan

FRAMEWORKS = (
    "tensorflow",
    "tensorflow_lite",
    "ai_edge_litert",
    "torch",
    "jax",
    "keras",
    "sklearn",
    "onnx",
    "onnxruntime",
    "numpy",
)


#: The modules that are *allowed* to import a training framework, because they are only ever
#: reachable with the ``train`` extra installed. Added by feature 002, and deliberately a short
#: explicit list: a new framework-importing module in the core fails the test below rather than
#: joining this set quietly.
EXTRA_ONLY_MODULES = frozenset(
    {
        # the train extra
        "caravan.data.reader",
        "caravan.metrics.classification",
        "caravan.templates.builders.mlp",
        "caravan.templates.builders.conv1d",
        # Feature 010: the two new builders, and reading images, which decodes with the framework
        # the train extra brings (research R7).
        "caravan.templates.builders.autoencoder",
        "caravan.templates.builders.conv2d",
        "caravan.data.images",
        # The preprocessing layers and the front-end of feature 008.
        "caravan.templates.builders.preprocessing",
        "caravan.templates.builders.frontend",
        "caravan.convert.tflite",
        "caravan.convert.debugger",
        # Feature 004: cloning a trained model onto a batch of one needs the framework that owns
        # the model. The *arithmetic* of the export does not, which is why only this one module of
        # the feature is here and `caravan.export.*` is not.
        "caravan.convert.batch",
        # the verify extra
        "caravan.runtime.measure",
    }
)


def all_module_names() -> list[str]:
    names = [caravan.__name__]
    for info in pkgutil.walk_packages(caravan.__path__, prefix="caravan."):
        names.append(info.name)
    return names


#: The subset of FRAMEWORKS that *trains* a model. The distinction matters from feature 003 on:
#: the core must import nothing in FRAMEWORKS at all, while the verify extra may carry a model
#: runtime — that is what it is for — and must still carry no trainer.
TRAINING_FRAMEWORKS = frozenset({"tensorflow", "torch", "jax", "keras", "sklearn"})


def core_module_names() -> list[str]:
    # Feature 002: the extra-only modules are excluded here and checked by their own test below.
    # Importing them would load a framework by design, which is what the extra is for.
    return [name for name in all_module_names() if name not in EXTRA_ONLY_MODULES]


def module_level_imports(path: Path) -> set[str]:
    """The root packages a module imports at module level, read without importing it."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in tree.body:  # module level only: a function-level import loads nothing on import
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


CHILD = """
import importlib, json, pkgutil, sys
import caravan

FRAMEWORKS = {frameworks}
EXTRA_ONLY = {extra_only}

names = [caravan.__name__] + [
    info.name for info in pkgutil.walk_packages(caravan.__path__, prefix="caravan.")
]
for name in names:
    if name not in EXTRA_ONLY:
        importlib.import_module(name)

loaded = sorted(
    framework
    for framework in FRAMEWORKS
    if framework in sys.modules or any(m.startswith(framework + ".") for m in sys.modules)
)
print(json.dumps({{"imported": len(names), "loaded": loaded}}))
"""


def test_importing_the_whole_core_loads_no_framework() -> None:
    # In a **fresh interpreter**, changed by feature 002 from an in-process check. The check reads
    # the module table, and once the suite also contains tests that legitimately use the framework
    # (``tests/train/``), the module table in this process is no longer evidence of anything. A
    # subprocess is also the honest shape of the claim: what matters is what a user's process
    # loads when it imports Caravan, not what this one happens to have lying around.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            CHILD.format(frameworks=set(FRAMEWORKS), extra_only=set(EXTRA_ONLY_MODULES)),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)

    assert not report["loaded"], (
        f"the core must not load a training framework (Principle XII); loaded: {report['loaded']}"
    )
    assert report["imported"] > 10, report


def test_the_core_has_more_than_one_module_so_the_check_means_something() -> None:
    # A guard against the check passing because nothing was imported at all.
    names = core_module_names()
    assert len(names) > 10, names


def test_exactly_the_declared_modules_import_a_framework_at_module_level() -> None:
    # Feature 002. The dynamic check above cannot see a framework import inside a function, and
    # it must not: ``caravan.stages.train`` imports Keras inside its stage function on purpose,
    # which is how a stage uses a framework the core never loads. What must stay true is that no
    # module *outside* the declared set imports one at module level, where the import would run
    # the moment anything touched it. Read with the parser rather than by importing, so the test
    # is just as meaningful in an environment where the framework is not installed at all.
    root = Path(caravan.__file__).parent
    offenders: dict[str, list[str]] = {}
    found: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).with_suffix("")
        parts = [part for part in relative.parts if part != "__init__"]
        name = ".".join(["caravan", *parts])
        frameworks = sorted(module_level_imports(path) & set(FRAMEWORKS))
        if not frameworks:
            continue
        found.add(name)
        if name not in EXTRA_ONLY_MODULES:
            offenders[name] = frameworks

    assert not offenders, (
        "these modules import a training framework at module level but are not declared "
        f"extra-only: {offenders}"
    )
    assert found == set(EXTRA_ONLY_MODULES), (
        "the declared extra-only set must match reality; declared but framework-free: "
        f"{sorted(set(EXTRA_ONLY_MODULES) - found)}"
    )


def test_inspecting_a_model_is_importable_everywhere() -> None:
    # Feature 003. ``caravan.runtime.inspect`` is deliberately *not* extra-only: it imports the
    # runtime inside its one function, so the module itself is importable in a default
    # installation. That is what lets a stage reference it without a guard, and it is why it is
    # absent from the set above rather than forgotten.
    import caravan.runtime.inspect as inspect_module

    assert inspect_module.INTEGER_DTYPES
    assert "caravan.runtime.inspect" not in EXTRA_ONLY_MODULES


def test_no_core_module_imports_an_extra_only_module_at_module_level() -> None:
    # The other direction: a core module that imported ``caravan.data.reader`` at module level
    # would load numpy through the back door and the check above would not see it.
    root = Path(caravan.__file__).parent
    extra_paths = {name.rsplit(".", 1)[-1] for name in EXTRA_ONLY_MODULES}
    offenders: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).with_suffix("")
        name = ".".join(["caravan", *[p for p in relative.parts if p != "__init__"]])
        if name in EXTRA_ONLY_MODULES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module in EXTRA_ONLY_MODULES:
                    hits.append(node.module)
                if node.module.startswith("caravan") and any(
                    alias.name in extra_paths for alias in node.names
                ):
                    hits.append(f"{node.module}.{node.names[0].name}")
            elif isinstance(node, ast.Import):
                hits.extend(alias.name for alias in node.names if alias.name in EXTRA_ONLY_MODULES)
        if hits:
            offenders[name] = hits
    assert not offenders, f"core modules importing extra-only modules at module level: {offenders}"


def test_the_export_package_needs_no_extra_at_all() -> None:
    """Feature 004: once a model has been read, turning it into files is plain formatting.

    The generic check above already covers this — a module that is not declared must import no
    framework — but it covers it by omission, and an omission is a poor place for an intention.
    The export package and the kernel data loader are in the *core* on purpose: behind an extra
    they would be denied to the default installation for no reason, and their tests would need one
    to run.

    Read from the source rather than by importing and inspecting ``sys.modules``: in a full suite
    run a sibling test has already imported a framework, so a check on the live interpreter would
    fail for somebody else's import. The same trap caught two tests in feature 003.
    """
    root = Path(caravan.__file__).parent
    modules = [root / "targets" / "kernels.py", *sorted((root / "export").glob("*.py"))]
    assert len(modules) >= 6, "the export package should have more modules than this"
    for path in modules:
        name = "caravan." + str(path.relative_to(root).with_suffix("")).replace("/", ".")
        assert name.removesuffix(".__init__") not in EXTRA_ONLY_MODULES
        imported = module_level_imports(path) & set(FRAMEWORKS)
        assert not imported, f"{name} imports {sorted(imported)} at module level and must not"
