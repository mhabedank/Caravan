"""Level 4: what the built distribution declares.

The cheapest of the four checks and the one that catches a budget breach before any code runs:
the dependency count, the extras count, the absence of a framework, and the absence of an upper
version bound nobody documented (FR-028, FR-031).
"""

from __future__ import annotations

from importlib.metadata import metadata, requires

from packaging.requirements import Requirement

from tests.layering.test_no_framework_imported import FRAMEWORKS, TRAINING_FRAMEWORKS

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
    # Changed by feature 002 from ">=3.14", the one assertion of feature 001 that the lowered
    # floor makes factually wrong. The floor is 3.13 because packaging has no per-extra Python
    # window and TensorFlow ships no stable wheel above cp313 (constitution v2.3.0, research R1).
    # It returns to ">=3.14" when a stable TensorFlow ships cp314 against a released keras.
    assert info["Requires-Python"] == ">=3.13"


def extra_requirements() -> dict[str, list[Requirement]]:
    """The declared dependencies of each extra, by extra name."""
    out: dict[str, list[Requirement]] = {}
    for raw in requires(DISTRIBUTION) or []:
        requirement = Requirement(raw)
        marker = str(requirement.marker or "")
        for extra in metadata(DISTRIBUTION).get_all("Provides-Extra") or []:
            if f'extra == "{extra}"' in marker:
                out.setdefault(extra, []).append(requirement)
    return out


def test_the_extras_are_the_two_the_plan_chose() -> None:
    # Updated by feature 003 from "train is the only extra". Two of the four Principle XII allows,
    # and the remaining two are the groups the constitution already names: benchmarking and
    # publication.
    extras = metadata(DISTRIBUTION).get_all("Provides-Extra") or []
    assert sorted(extras) == ["train", "verify"]


def test_every_dependency_of_the_training_extra_is_marked() -> None:
    # Feature 002, Principle XII conditions 1 to 3 as amended in v2.3.0. An extra cannot carry its
    # own Requires-Python, so its window is expressed as a floor that admits it plus a marker on
    # every dependency it carries. Without the markers, installing the extra on 3.14 would fail in
    # the resolver instead of telling the user which Python to train on.
    carried = extra_requirements()["train"]
    assert carried, "the train extra declares no dependency"
    unmarked = sorted(r.name for r in carried if 'python_version < "3.14"' not in str(r.marker))
    assert not unmarked, (
        "every dependency of the train extra must carry the python_version marker that states "
        f"its window (Principle XII, condition 3); unmarked: {unmarked}"
    )


def test_every_dependency_of_the_verify_extra_states_its_window() -> None:
    """The verify extra's window, which this test first had backwards.

    It originally forbade a ``python_version`` marker here, on the grounds that the runtime
    installs on every Python the project supports. It does not: ``ai-edge-litert`` publishes cp310
    through cp314 and no cp315, in every recent version. The claim came from checking cp314 and
    assuming the next tag followed.

    So the requirement is the same one the train extra carries, with a wider window: every
    dependency states where it installs, and Principle XII's condition 4 then turns the gap into a
    sentence from caravan rather than a resolver error.
    """
    carried = extra_requirements()["verify"]
    assert carried, "the verify extra declares no dependency"
    unmarked = sorted(r.name for r in carried if "python_version" not in str(r.marker or ""))
    assert not unmarked, (
        "every dependency of the verify extra must state the Python window it installs on; "
        f"unmarked: {unmarked}"
    )


def test_the_two_extras_have_different_windows_and_both_are_stated() -> None:
    # The windows are the reason there are two extras at all, so a test holds them apart: the
    # conversion half stops below 3.14, the runtime below 3.15.
    windows = {
        extra: {str(r.marker) for r in carried} for extra, carried in extra_requirements().items()
    }
    assert all('python_version < "3.14"' in marker for marker in windows["train"])
    assert all('python_version < "3.15"' in marker for marker in windows["verify"])


def test_the_verify_extra_carries_no_training_framework() -> None:
    # The reason it is 114 MiB and not 1,971: nothing in its graph trains anything. It does carry
    # a model *runtime*, which is the point — so this checks the narrower set, and the broader
    # FRAMEWORKS remains what the core may not import.
    names = {r.name.replace("-", "_").lower() for r in extra_requirements()["verify"]}
    assert not names & TRAINING_FRAMEWORKS, (
        f"the verify extra must not depend on a training framework: {sorted(names)}"
    )


def test_the_floor_admits_the_training_extras_window() -> None:
    # Condition 1: the lowered floor must admit the extra's window, and every version it admits is
    # tested in continuous integration. A floor that is claimed and not tested is a false claim.
    from packaging.specifiers import SpecifierSet

    floor = SpecifierSet(metadata(DISTRIBUTION)["Requires-Python"])
    assert floor.contains("3.13"), (
        "the train extra needs Python 3.13 and the published floor must admit it, or the extra "
        "cannot be installed on any interpreter at all"
    )
    for supported in ("3.13", "3.14", "3.15"):
        assert floor.contains(supported)


def test_the_command_is_installed_under_the_name_the_constitution_fixes() -> None:
    from importlib.metadata import entry_points

    scripts = {entry.name for entry in entry_points(group="console_scripts")}
    assert "caravan" in scripts
