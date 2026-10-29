"""The reference pages name everything the code has (feature 009, FR-015, research R7).

A reference that misses an option is worse than none: the reader concludes the option does not
exist. So each page is checked against the code it describes:

- the CLI reference against the argument parser;
- the manifest reference against the schema models;
- the rules page against the rule table;
- the boards page against the board registry;
- the compatibility page against the registries and the feature types.

Each field, command, rule and board is declared once, as a reference object
(``:::{manifest-field} export.targets``), and every other page links to it by name.

Each failure names what is missing and from which page. The pages are written by hand, so they can
say why and give examples; this test only keeps them complete. Core only: it imports no framework
and runs on every Python.
"""

from __future__ import annotations

import argparse
import re
import types
import typing
from pathlib import Path

from pydantic import BaseModel

from caravan.cli.main import build_parser
from caravan.manifest import errors
from caravan.manifest.schema import Manifest
from caravan.manifest.schema.features import INPUT_TYPES, OUTPUT_TYPES
from caravan.targets.registry import default_registry as default_boards
from caravan.templates.registry import default_registry as default_templates

DOCS = Path(__file__).resolve().parents[2] / "docs"
CLI = DOCS / "ref" / "cli.md"
#: The manifest reference is one overview and one page per top-level section of the manifest.
MANIFEST = DOCS / "ref" / "manifest"
RULES = DOCS / "ref" / "rules.md"
COMPATIBILITY = DOCS / "ref" / "compatibility.md"
BOARDS = DOCS / "ref" / "boards.md"


def manifest_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(MANIFEST.glob("*.md")))


# --- the command line -------------------------------------------------------------------------


def subcommands() -> dict[str, argparse.ArgumentParser]:
    parser = build_parser()
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return dict(action.choices)


def section(text: str, name: str) -> str:
    """The entry of the command ``name``: the body of its ``:::{cli} name`` block."""
    match = re.search(rf"^:::+\{{cli\}} {re.escape(name)}\s*$(.*?)^:::+\s*$", text, re.M | re.S)
    return match.group(1) if match else ""


def test_every_command_and_option_is_in_the_cli_reference() -> None:
    text = CLI.read_text(encoding="utf-8")
    missing: list[str] = []
    for verb, sub in subcommands().items():
        body = section(text, f"caravan {verb}")
        if not body:
            missing.append(f"the entry ':::{{cli}} caravan {verb}'")
            continue
        for action in sub._actions:
            for option in action.option_strings:
                if option in ("-h", "--help"):
                    continue
                if f"`{option}" not in body:
                    missing.append(f"{option} of caravan {verb}")
            if not action.option_strings and action.metavar and f"`{action.metavar}`" not in body:
                missing.append(f"the argument {action.metavar} of caravan {verb}")
    assert not missing, f"{CLI.relative_to(DOCS.parent)} lacks: {', '.join(missing)}"


def test_the_global_option_and_every_exit_code_are_in_the_cli_reference() -> None:
    text = CLI.read_text(encoding="utf-8")
    missing = [] if "`--version`" in text else ["--version"]
    missing += [f"exit code {code}" for code in range(5) if not re.search(rf"\b{code}\b", text)]
    for name in ("EXIT_OK", "EXIT_RULE", "EXIT_USAGE", "EXIT_INTERNAL", "EXIT_ENVIRONMENT"):
        assert hasattr(__import__("caravan.cli.main", fromlist=[name]), name)
    assert not missing, f"{CLI.relative_to(DOCS.parent)} lacks: {', '.join(missing)}"


# --- the manifest -----------------------------------------------------------------------------


def _models(annotation: typing.Any) -> list[tuple[str, type[BaseModel]]]:
    """The models inside an annotation, with their path suffix: "", "[]" or ".<type>"."""
    origin = typing.get_origin(annotation)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [("", annotation)]
    if origin in (list, tuple):
        return [("[]" + s, m) for arg in typing.get_args(annotation) for s, m in _models(arg)]
    if origin is dict:
        _key, value = typing.get_args(annotation)
        return [(".<type>" + s, m) for s, m in _models(value)]
    if origin in (typing.Union, types.UnionType):
        return [found for arg in typing.get_args(annotation) for found in _models(arg)]
    return []


def field_paths(model: type[BaseModel], prefix: str = "") -> set[str]:
    """Every field path of a model, nested models expanded, in the reference's notation."""
    paths: set[str] = set()
    for name, info in model.model_fields.items():
        key = info.alias or name
        path = f"{prefix}{key}"
        nested = _models(info.annotation)
        if not nested:
            paths.add(path)
            continue
        for suffix, inner in nested:
            paths |= field_paths(inner, f"{path}{suffix}.")
    return paths


def declared(kind: str, text: str) -> list[str]:
    """The names a page declares as reference objects of one kind: ``:::{kind} name``."""
    return re.findall(rf"^:::+\{{{re.escape(kind)}\}} (.+?)\s*$", text, re.M)


def test_every_manifest_field_has_exactly_one_entry() -> None:
    names = declared("manifest-field", manifest_text())
    paths = field_paths(Manifest)
    assert "export.test_windows" in paths
    assert "input_features[].preprocessing.normalization" in paths
    missing = sorted(paths - set(names))
    twice = sorted({n for n in names if names.count(n) > 1})
    unknown = sorted(set(names) - paths)
    assert not missing, (
        f"{MANIFEST.relative_to(DOCS.parent)} has no entry for: {', '.join(missing)}"
    )
    assert not twice, f"{MANIFEST.relative_to(DOCS.parent)} has two entries for: {', '.join(twice)}"
    assert not unknown, (
        f"{MANIFEST.relative_to(DOCS.parent)} has entries for fields the parser does not know: "
        f"{', '.join(unknown)}"
    )


# --- the rules --------------------------------------------------------------------------------


def rule_identifiers() -> set[str]:
    return {
        value
        for name, value in vars(errors).items()
        if name.startswith("RULE_") and isinstance(value, str)
    }


def rule_entries() -> tuple[list[str], set[str]]:
    """Every rule the page declares, and the ones whose entry says it is retired."""
    text = RULES.read_text(encoding="utf-8")
    names = declared("rule", text)
    retired = set(re.findall(r"^:::+\{rule\} (\S+)\s*\n\*\*Retired\.\*\*", text, re.M))
    return names, retired


def test_every_rule_is_on_the_rules_page() -> None:
    names, retired = rule_entries()
    missing = sorted(
        rule for rule in rule_identifiers() - set(errors.RETIRED_RULES) if rule not in names
    )
    missing += sorted(f"{rule} (retired)" for rule in errors.RETIRED_RULES if rule not in retired)
    twice = sorted({n for n in names if names.count(n) > 1})
    assert not missing, f"{RULES.relative_to(DOCS.parent)} lacks: {', '.join(missing)}"
    assert not twice, f"{RULES.relative_to(DOCS.parent)} has two entries for: {', '.join(twice)}"


def test_no_live_rule_is_marked_retired() -> None:
    _names, retired = rule_entries()
    wrongly = sorted(retired - set(errors.RETIRED_RULES))
    assert not wrongly, f"{RULES.relative_to(DOCS.parent)} marks live rules retired: {wrongly}"


# --- the boards -------------------------------------------------------------------------------


def test_every_board_has_exactly_one_entry() -> None:
    names = declared("board", BOARDS.read_text(encoding="utf-8"))
    shipped = {board.board for board in default_boards()}
    missing = sorted(shipped - set(names))
    unknown = sorted(set(names) - shipped)
    twice = sorted({n for n in names if names.count(n) > 1})
    assert not missing, f"{BOARDS.relative_to(DOCS.parent)} has no entry for: {', '.join(missing)}"
    assert not unknown, f"{BOARDS.relative_to(DOCS.parent)} describes boards not shipped: {unknown}"
    assert not twice, f"{BOARDS.relative_to(DOCS.parent)} has two entries for: {', '.join(twice)}"


def test_every_command_has_exactly_one_entry() -> None:
    names = declared("cli", CLI.read_text(encoding="utf-8"))
    verbs = {f"caravan {verb}" for verb in subcommands()}
    assert sorted(names) == sorted(verbs), f"{CLI.relative_to(DOCS.parent)}: {names} vs {verbs}"


# --- compatibility ----------------------------------------------------------------------------


def test_every_template_board_and_feature_type_is_on_the_compatibility_page() -> None:
    text = COMPATIBILITY.read_text(encoding="utf-8")
    names = {f"template {spec.identifier}" for spec in default_templates()}
    names |= {f"board {board.board}" for board in default_boards()}
    names |= {f"input type {kind}" for kind in INPUT_TYPES}
    names |= {f"output type {kind}" for kind in OUTPUT_TYPES}
    missing = sorted(name for name in names if f"`{name.split(' ')[-1]}`" not in text)
    assert not missing, f"{COMPATIBILITY.relative_to(DOCS.parent)} lacks: {', '.join(missing)}"


# --- the landing page ---------------------------------------------------------------------------


def test_the_landing_page_does_not_carry_its_own_install_line() -> None:
    """The install line lives on the installation page, and only there.

    It used to be on the landing page as well, and two copies are two places to forget on a version
    bump. The landing page also gets exactly one primary next step (FR-003), which an install
    command standing beside it would compete with. ``test_docs_guide.py`` pins its version, so
    the check that mattered is still made — once.
    """
    text = (DOCS / "index.md").read_text(encoding="utf-8")
    assert "pip install" not in text, (
        "the landing page has an install command again. It belongs to the installation page, "
        "where one check keeps its version current; a second copy here would drift."
    )
