"""Requirements of the schema that no fixture happens to cover.

Each test here exists because walking the functional requirements found it unasserted — not
because the behaviour was in doubt, but because an unasserted requirement is one refactor away
from being untrue.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from caravan.manifest.load import load_manifest
from caravan.manifest.schema import Manifest
from caravan.templates.registry import TemplateParameterSpec, TemplateRegistry
from tests.support import MINIMAL


def manifest_data() -> dict:
    from caravan.manifest._yaml import read_mapping

    return read_mapping(MINIMAL)


def first_error(data: dict) -> dict:
    with pytest.raises(ValidationError) as caught:
        Manifest.model_validate(data)
    return caught.value.errors()[0]


def test_defaults_set_feature_types_and_nothing_else() -> None:
    # Feature 008: Ludwig's ``defaults`` is per feature type. It sets no other section's values,
    # so a trainer setting in it is refused rather than inherited.
    data = manifest_data()
    data["defaults"] = {"number": {"trainer": {"epochs": 1}}}
    error = first_error(data)
    assert error["type"] == "extra_forbidden"
    assert error["loc"] == ("defaults", "number", "trainer")


def test_a_manifest_without_an_output_is_invalid() -> None:
    # Principle I (constitution 3.0.0): the manifest declares what goes in and what comes out.
    data = manifest_data()
    del data["output_features"]
    error = first_error(data)
    assert error["type"] == "missing"
    assert error["loc"] == ("output_features",)


def test_a_split_is_a_mapping_with_named_keys() -> None:
    # FR-018: named keys, never a bare positional list in place of the split.
    data = manifest_data()
    data["preprocessing"]["split"] = [0.7, 0.15, 0.15]
    error = first_error(data)
    assert error["loc"][:2] == ("preprocessing", "split")
    assert error["type"] in {"model_attributes_type", "model_type", "dict_type"}


def test_a_second_template_can_be_registered_without_editing_a_central_list(tmp_path) -> None:
    # FR-021: the registry is extensible. Proven by registering one, not by shipping an unused
    # template nobody needs (Principle X).
    from pydantic import BaseModel, ConfigDict

    class FlatParameters(BaseModel):
        model_config = ConfigDict(extra="forbid")

        units: int = 4

    registry = TemplateRegistry()
    registry.register(
        TemplateParameterSpec(
            identifier="flat",
            parameters=FlatParameters,
            consumes_window=False,
            summary="A template that consumes no time window",
        )
    )

    source = MINIMAL.read_text(encoding="utf-8")
    source = source.replace("template: mlp", "template: flat")
    source = source.replace("  params:\n    hidden: [8]\n", "  params:\n    units: 4\n")
    source = source.replace("preprocessing:\n  window_size: 32\n", "")
    manifest = tmp_path / "flat.yaml"
    manifest.write_text(source, encoding="utf-8")

    outcome = load_manifest(manifest, templates=registry)
    assert outcome.is_valid, outcome.findings
    assert registry.identifiers == ("flat",)


def test_a_template_that_consumes_no_window_rejects_one(tmp_path) -> None:
    # The other half of CF-6, which the shipped template cannot exercise.
    from pydantic import BaseModel, ConfigDict

    class FlatParameters(BaseModel):
        model_config = ConfigDict(extra="forbid")

        units: int = 4

    registry = TemplateRegistry()
    registry.register(
        TemplateParameterSpec(
            identifier="flat",
            parameters=FlatParameters,
            consumes_window=False,
            summary="A template that consumes no time window",
        )
    )
    source = MINIMAL.read_text(encoding="utf-8")
    source = source.replace("template: mlp", "template: flat")
    source = source.replace("  params:\n    hidden: [8]\n", "  params:\n    units: 4\n")
    manifest = tmp_path / "flat-with-window.yaml"
    manifest.write_text(source, encoding="utf-8")

    outcome = load_manifest(manifest, templates=registry)
    assert not outcome.is_valid
    assert outcome.findings[0].rule == "CF-6"
    assert "must be left out" in outcome.findings[0].problem
