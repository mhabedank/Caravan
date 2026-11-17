"""The parameter form, built from each template's own model (feature 013, FR-033, R14)."""

from __future__ import annotations

import pytest

from caravan.init.form import Form, presets
from caravan.templates.registry import default_registry


@pytest.mark.parametrize("identifier", default_registry().identifiers)
def test_every_template_gets_a_form_and_its_starter_round_trips(identifier) -> None:
    spec = default_registry().get(identifier)
    form = Form(spec.parameters, spec.starter.params)
    assert form.errors() == {}
    assert form.params() == dict(spec.starter.params)
    for _, value in presets(spec.starter.params):
        assert Form(spec.parameters, value).errors() == {}


def test_rows_are_added_and_removed_within_the_model_bounds() -> None:
    spec = default_registry().get("conv1d")
    form = Form(spec.parameters, spec.starter.params)
    assert form.add("blocks") and form.rows("blocks") == 3
    assert form.remove("blocks", 0) and form.remove("blocks", 0)
    assert not form.remove("blocks", 0), "a conv1d needs at least one block"
    assert form.rows("blocks") == 1


def test_a_refused_value_is_named_at_its_field() -> None:
    spec = default_registry().get("conv1d")
    form = Form(spec.parameters, spec.starter.params)
    form.set("blocks", "0", row=1, name="kernel")
    assert list(form.errors()) == ["blocks.1.kernel"]
    with pytest.raises(ValueError, match="expected int"):
        form.set("blocks", "five", row=0, name="filters")


def test_a_choice_and_an_optional_value() -> None:
    spec = default_registry().get("conv1d")
    form = Form(spec.parameters, spec.starter.params)
    form.set("head", "flatten")
    form.set("blocks", "", row=0, name="pool")
    assert form.params()["head"] == "flatten"
    assert "pool" not in form.params()["blocks"][0]
    with pytest.raises(ValueError, match=r"average \| flatten"):
        form.set("head", "max")


def test_defaults_are_not_written_and_a_derived_value_is_not_stated() -> None:
    # The autoencoder mirrors its decoder when none is stated; the form must not write the mirror.
    spec = default_registry().get("autoencoder")
    assert "decoder" not in Form(spec.parameters, spec.starter.params).params()
    mlp = default_registry().get("mlp")
    form = Form(mlp.parameters, {"hidden": [8], "dropout": 0.0})
    assert form.params() == {"hidden": [8]}


def test_the_presets_scale_widths_and_leave_kernels() -> None:
    spec = default_registry().get("conv1d")
    _, smaller = presets(spec.starter.params)[1]
    assert [b["filters"] for b in smaller["blocks"]] == [8, 16]
    assert [b["kernel"] for b in smaller["blocks"]] == [5, 3]
