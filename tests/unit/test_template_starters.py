"""Every registered starter is valid for its own template (feature 013, data-model, SC-006)."""

from __future__ import annotations

import pytest

from caravan.templates.mlp import MlpParameters
from caravan.templates.registry import (
    TemplateParameterSpec,
    TemplateRegistry,
    TemplateStarter,
    default_registry,
)


@pytest.mark.parametrize("spec", list(default_registry()), ids=lambda s: s.identifier)
def test_a_starter_validates_and_fits_its_window(spec) -> None:
    starter = spec.starter
    assert starter is not None, "every built-in template proposes where to start"
    params = spec.parameters.model_validate(dict(starter.params))
    if spec.window_fit is not None and starter.window is not None:
        assert spec.window_fit(params, starter.window) is None
    assert starter.note


def test_a_template_without_a_starter_is_still_registered() -> None:
    registry = TemplateRegistry()
    registry.register(
        TemplateParameterSpec(
            identifier="plain", parameters=MlpParameters, consumes_window=True, summary="x"
        )
    )
    assert registry.get("plain").starter is None


def test_the_ranks_put_the_simplest_first() -> None:
    ranks = {s.identifier: s.starter.rank for s in default_registry()}
    assert ranks["mlp"] < ranks["conv1d"] < ranks["conv2d"]
    assert isinstance(next(iter(default_registry())).starter, TemplateStarter)
