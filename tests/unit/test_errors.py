"""The message form of ``contracts/cli.md``.

Every rejection names the field, what was wrong and what is accepted — and never a library type
name, a module path or a traceback. Those belong to exit code 3 alone.
"""

from __future__ import annotations

import pytest

from caravan.manifest.errors import Finding, render_finding
from caravan.manifest.load import load_manifest
from tests.support import INVALID, MINIMAL


def findings_for(name: str):
    outcome = load_manifest(INVALID / f"{name}.yaml")
    return outcome.findings


def rendered(name: str) -> str:
    return "\n".join(render_finding(f"{name}.yaml", f) for f in findings_for(name))


def test_field_path_comes_first() -> None:
    text = rendered("b-1-unknown-board")
    assert text.startswith("b-1-unknown-board.yaml: export.targets[0] — unknown board")


def test_unknown_field_lists_what_is_accepted_and_suggests_the_nearest() -> None:
    text = rendered("unknown-field")
    assert "model.hiden — unknown field" in text
    assert "accepted here: name, version, topic, task, template, params" in text
    assert "did you mean: hidden" not in text  # hidden is a template parameter, not a field
    assert "accepted here" in text


def test_misplaced_field_says_where_it_belongs() -> None:
    text = rendered("unknown-field-misplaced")
    assert "model.window — unknown field" in text
    assert "this field belongs at: dataset.window" in text


def test_cross_field_rule_names_the_fields_it_relates() -> None:
    text = rendered("cf-3-personal-data-minimal-risk")
    assert "compliance.eu_ai_act_class" in text
    assert "compliance.privacy" in text
    assert "accepted: limited-risk, high-risk" in text


def test_identity_rejection_states_the_required_form() -> None:
    # FR-019: the tool states the form when it rejects a name or a version.
    from caravan.manifest.schema.model import ModelSpec

    with pytest.raises(Exception) as caught:
        ModelSpec.model_validate(
            {"name": "AB", "version": "0.1.0", "topic": "t", "task": "t", "template": "mlp"}
        )
    message = str(caught.value)
    assert "lower-case letters, digits and hyphens" in message
    assert "at least 3 characters" in message


def test_no_library_internals_leak_into_a_message() -> None:
    forbidden = ("pydantic", "Traceback", "caravan.manifest.schema", "ValidationError")
    for name, _path, _expected in [(n, p, e) for n, p, e in _all_cases()]:
        text = rendered(name)
        for token in forbidden:
            assert token not in text, f"{name}: {token!r} leaked into a message"


def _all_cases():
    from tests.support import invalid_cases

    return invalid_cases()


def test_render_is_stable_for_a_finding_without_extras() -> None:
    finding = Finding(path="dataset.window", problem="this field is required but missing")
    assert render_finding("m.yaml", finding) == (
        "m.yaml: dataset.window — this field is required but missing"
    )


def test_valid_manifest_has_no_findings() -> None:
    assert load_manifest(MINIMAL).findings == []
