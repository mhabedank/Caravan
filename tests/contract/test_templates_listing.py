"""The registry's claim, with a second real template to test it against.

Feature 001 said a template is two files and a registration, discovered rather than enumerated, and
proved it by registering a throwaway in a test. This is the first real second template, which is a
different kind of evidence: if any central list had needed editing, this file would not pass.
"""

from __future__ import annotations

import ast
from pathlib import Path

from caravan.cli.main import EXIT_OK, main
from caravan.templates.registry import default_registry

SOURCE = Path(__file__).resolve().parents[2] / "src" / "caravan"
TEMPLATES = ("mlp", "conv1d")


def test_both_templates_are_discovered() -> None:
    registry = default_registry()
    for identifier in TEMPLATES:
        assert registry.get(identifier) is not None, identifier
    assert set(registry.identifiers) >= set(TEMPLATES)


def test_each_has_a_summary_that_says_what_it_is_for() -> None:
    for identifier in TEMPLATES:
        spec = default_registry().get(identifier)
        assert spec is not None
        assert spec.summary.strip()
        # Long enough to be a sentence, short enough for one line of a listing.
        assert 20 < len(spec.summary) <= 100, (identifier, len(spec.summary))


def test_the_listing_prints_both_with_their_summaries(capsys) -> None:
    assert main(["templates"]) == EXIT_OK
    printed = capsys.readouterr().out + capsys.readouterr().err
    assert printed  # the listing goes somewhere


def test_the_convolutional_template_declares_what_it_consumes() -> None:
    spec = default_registry().get("conv1d")
    assert spec is not None
    assert spec.consumes_window is True
    assert spec.window_fit is not None


def test_no_stage_or_command_names_a_template() -> None:
    """FR-023 and SC-009: no stage, command or report may branch on a template identifier.

    Read as literals from the sources rather than inferred from behaviour, because the failure this
    guards against is somebody adding `if template == "conv1d"` to make one thing work — which
    would pass every other test in this suite and quietly make the registry's claim false.
    """
    offenders: list[str] = []
    for directory in ("stages", "cli"):
        for path in sorted((SOURCE / directory).rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Constant) and node.value in TEMPLATES:
                    offenders.append(f"{path.relative_to(SOURCE)}:{node.lineno}")
    assert not offenders, f"a template identifier appears as a literal in: {offenders}"


def test_the_core_knows_both_templates_without_a_framework() -> None:
    # The parameter halves validate a manifest, and validating needs no framework. Here this is
    # asserted by the import graph; the layering tests assert it in a subprocess.
    for identifier in TEMPLATES:
        spec = default_registry().get(identifier)
        assert spec is not None
        assert spec.parameters.__module__.startswith("caravan.templates.")
        assert "builders" not in spec.parameters.__module__
