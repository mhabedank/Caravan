"""The resolved manifest of caravan/v0.2 (feature 008, contracts/manifest.md).

Every default expanded, nothing left implicit, key order from the schema; every feature shown fully
resolved, in the order feature value, then ``defaults``, then the type's default; and what only the
training part can say shown as ``derived`` until a run has fitted it.
"""

from __future__ import annotations

import copy

import pytest

from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import DERIVED, merge_fitted, render, resolve
from tests.support import PILOT_FIXTURE, pilot_fitted


@pytest.fixture
def pilot():
    outcome = load_manifest(PILOT_FIXTURE)
    assert outcome.is_valid, outcome.findings
    return outcome.manifest


def test_key_order_follows_the_schema(pilot) -> None:
    resolved = resolve(pilot)
    assert list(resolved) == [
        "apiVersion",
        "model",
        "input_features",
        "output_features",
        "preprocessing",
        "defaults",
        "dataset",
        "trainer",
        "random_seed",
        "export",
    ]
    assert list(resolved["input_features"][0]) == ["name", "type", "preprocessing", "encoder"]
    assert list(resolved["output_features"][0]) == [
        "name",
        "type",
        "preprocessing",
        "loss",
        "accuracy_drop_max",
    ]


def test_every_type_default_is_shown(pilot) -> None:
    resolved = resolve(pilot)
    can_id, dlc = resolved["input_features"][:2]
    assert can_id["preprocessing"] == {
        "missing_value_strategy": "fill_with_const",
        "fill_value": "<UNK>",
        "most_common": 32,
        "vocab": DERIVED,
    }
    assert can_id["encoder"] == {"type": "dense", "embedding_size": DERIVED}
    assert dlc["preprocessing"] == {
        "normalization": "zscore",
        "missing_value_strategy": "fill_with_const",
        "fill_value": 0.0,
    }
    assert "encoder" not in dlc
    assert resolved["trainer"] == {
        "epochs": 50,
        "batch_size": 256,
        "learning_rate": 0.001,
        "optimizer": {"type": "adam"},
        "early_stop": 5,
    }
    assert resolved["random_seed"] == 42


def test_what_the_training_part_will_say_is_marked_derived(pilot) -> None:
    resolved = resolve(pilot)
    assert resolved["output_features"][0]["preprocessing"]["vocab"] == DERIVED == "derived"
    assert resolved["input_features"][0]["preprocessing"]["vocab"] == DERIVED


def test_a_stratified_split_names_the_output_column(pilot) -> None:
    assert resolve(pilot)["preprocessing"]["split"] == {
        "type": "stratify",
        "probabilities": [0.7, 0.15, 0.15],
        "column": "label",
    }


def test_the_output_shows_only_the_keys_of_its_type(pilot) -> None:
    binary = pilot.model_copy(deep=True)
    binary.output_features[0].type = "binary"
    assert set(resolve(binary)["output_features"][0]) == {
        "name",
        "type",
        "preprocessing",
        "loss",
        "threshold",
        "accuracy_drop_max",
    }
    assert resolve(binary)["output_features"][0]["threshold"] == 0.5
    number = pilot.model_copy(deep=True)
    number.output_features[0].type = "number"
    output = resolve(number)["output_features"][0]
    assert output["loss"] == {"type": "mean_squared_error"}
    assert output["preprocessing"] == {"normalization": None}
    assert output["clip"] is None


def test_no_removed_field_appears(pilot) -> None:
    text = render(pilot)
    for gone in (
        "compliance",
        "topic:",
        "task:",
        "permitted_use",
        "license",
        "inputs:",
        "outputs:",
    ):
        assert gone not in text, gone


def test_merge_fills_every_fitted_value_and_leaves_the_input_alone(pilot) -> None:
    resolved = resolve(pilot)
    before = copy.deepcopy(resolved)
    merged = merge_fitted(resolved, pilot_fitted())

    assert resolved == before  # the input is not mutated
    can_id = merged["input_features"][0]
    assert can_id["preprocessing"]["vocab"] == [291, 608, 790, 1072]
    assert can_id["preprocessing"]["fitted"]["codes"] == [291, 608, 790, 1072]
    # min(vocabulary, 4), resolved once the vocabulary is known (spec, Assumptions).
    assert can_id["encoder"]["embedding_size"] == 4
    assert merged["input_features"][1]["preprocessing"]["fitted"]["shift"] == 100.0
    assert merged["output_features"][0]["preprocessing"]["vocab"] == list(
        pilot_fitted()["output"]["labels"]
    )


def test_a_stated_embedding_size_is_kept(pilot) -> None:
    from caravan.manifest.schema.features import Encoder

    stated = pilot.model_copy(deep=True)
    stated.input_features[0].encoder = Encoder(type="dense", embedding_size=2)
    merged = merge_fitted(resolve(stated), pilot_fitted())
    assert merged["input_features"][0]["encoder"]["embedding_size"] == 2


def test_rendering_is_byte_identical_across_calls(pilot) -> None:
    assert render(pilot) == render(pilot)
