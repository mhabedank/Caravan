"""Level 4: what the built distribution declares.

The cheapest of the four checks and the one that catches a budget breach before any code runs:
the dependency count, the extras count, the absence of a framework, and the absence of an upper
version bound nobody documented (FR-028, FR-031).
"""

from __future__ import annotations

from importlib.metadata import metadata, requires

from packaging.requirements import Requirement

from tests.layering.test_no_framework_imported import FRAMEWORKS

DISTRIBUTION = "caravan-ml"

#: The constitution's numbers. Changing one is a PATCH amendment with a stated reason, not a
#: decision inside a feature.
MAX_RUNTIME_DEPENDENCIES = 6
MAX_EXTRAS = 4


def runtime_requirements() -> list[Requirement]:
    """The requirements installed by default — those without an extra marker."""
    declared = requires(DISTRIBUTION) or []
    out = []
    for raw in declared:
        requirement = Requirement(raw)
        marker = str(requirement.marker) if requirement.marker else ""
        if "extra ==" in marker:
            continue
        out.append(requirement)
    return out


def test_the_default_installation_stays_within_the_dependency_budget() -> None:
    names = sorted(r.name for r in runtime_requirements())
    assert len(names) <= MAX_RUNTIME_DEPENDENCIES, (
        f"the default installation may have at most {MAX_RUNTIME_DEPENDENCIES} direct runtime "
        f"dependencies (Principle XII); it declares {len(names)}: {names}"
    )


def test_the_project_stays_within_the_extras_budget() -> None:
    extras = metadata(DISTRIBUTION).get_all("Provides-Extra") or []
    assert len(extras) <= MAX_EXTRAS, (
        f"at most {MAX_EXTRAS} optional extras (Principle XII); found {sorted(extras)}"
    )


def test_no_runtime_dependency_is_a_training_framework() -> None:
    offenders = sorted(
        r.name for r in runtime_requirements() if r.name.replace("-", "_").lower() in FRAMEWORKS
    )
    assert not offenders, f"the core must not depend on a training framework: {offenders}"


def test_no_upper_version_bound_without_a_documented_incompatibility() -> None:
    # FR-031. Upper bounds are the mechanism that turns a Python version bump into a blocked
    # project, which is the failure Principle XII was written against.
    bounded = sorted(
        r.name
        for r in runtime_requirements()
        if any(spec.operator in {"<", "<=", "=="} for spec in r.specifier)
    )
    assert not bounded, (
        "a dependency may carry an upper bound only with a documented incompatibility "
        f"(FR-031); bounded: {bounded}"
    )


def test_the_declared_dependencies_are_the_two_the_plan_chose() -> None:
    # Names as the metadata normalises them: ``ruamel.yaml`` is declared with a dot and recorded
    # with a hyphen.
    assert sorted(r.name for r in runtime_requirements()) == ["pydantic", "ruamel-yaml"]


def test_the_distribution_declares_its_identity_and_its_python_policy() -> None:
    # FR-029, FR-030, FR-031: the names, the licence and the supported Python range are package
    # metadata, so they are asserted against the built distribution rather than against intent.
    info = metadata(DISTRIBUTION)
    assert info["Name"] == "caravan-ml"
    assert "Apache-2.0" in (info["License-Expression"] or info["License"] or "")
    assert info["Requires-Python"] == ">=3.14"


def test_the_command_is_installed_under_the_name_the_constitution_fixes() -> None:
    from importlib.metadata import entry_points

    scripts = {entry.name for entry in entry_points(group="console_scripts")}
    assert "caravan" in scripts
