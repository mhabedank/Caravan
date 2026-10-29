"""The schema of caravan/v0.2: features, their types and keys, and the rules across them.

Feature 008, contracts/manifest.md. Each test writes one manifest that differs from a valid base in
one place and asserts which rule fired at which path — or that it is accepted, with what default.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import resolve
from caravan.manifest.schema.features import INPUT_TYPES, OUTPUT_TYPES

BASE: dict[str, Any] = {
    "apiVersion": "caravan/v0.2",
    "model": {"name": "probe", "version": "0.0.1", "template": "mlp", "params": {"hidden": [8]}},
    "input_features": [
        {"name": "speed", "type": "number"},
        {"name": "gear", "type": "category"},
        {"name": "brake", "type": "binary"},
    ],
    "output_features": [{"name": "state", "type": "category", "accuracy_drop_max": 0.02}],
    "preprocessing": {"window_size": 16},
    "dataset": "data/",
    "export": {"targets": ["stm32h743"], "representative_samples": 100},
}


def outcome_for(tmp_path, edit=None):
    from caravan.manifest._yaml import dump_mapping

    document = copy.deepcopy(BASE)
    if edit is not None:
        edit(document)
    path = tmp_path / "probe.yaml"
    path.write_text(dump_mapping(document), encoding="utf-8")
    return load_manifest(path)


def refused(tmp_path, edit) -> tuple[str | None, str, str]:
    outcome = outcome_for(tmp_path, edit)
    assert not outcome.is_valid, "expected a refusal"
    finding = outcome.findings[0]
    return finding.rule, finding.path, finding.problem


def resolved(tmp_path, edit=None) -> dict[str, Any]:
    outcome = outcome_for(tmp_path, edit)
    assert outcome.is_valid, [finding.as_dict() for finding in outcome.findings]
    return resolve(outcome.manifest)


# --- accepted, with every default -------------------------------------------------------------


def test_the_base_is_valid_and_every_default_is_resolved(tmp_path) -> None:
    out = resolved(tmp_path)
    speed, gear, brake = out["input_features"]
    assert speed["preprocessing"]["normalization"] == "zscore"
    assert gear["preprocessing"]["most_common"] == 32
    assert gear["encoder"]["type"] == "dense"
    assert brake["preprocessing"] == {
        "missing_value_strategy": "fill_with_const",
        "fill_value": False,
        "fallback_true_label": None,
    }
    assert out["preprocessing"]["split"] == {
        "type": "random",
        "probabilities": [0.7, 0.15, 0.15],
        "column": None,
    }
    assert out["trainer"]["early_stop"] == 5
    assert out["random_seed"] == 42
    assert out["export"]["representative_samples"] == 100


@pytest.mark.parametrize("normalization", ["zscore", "minmax", "iq", None])
def test_every_normalization_is_accepted(tmp_path, normalization) -> None:
    def edit(document):
        document["input_features"][0]["preprocessing"] = {"normalization": normalization}

    assert resolved(tmp_path, edit)["input_features"][0]["preprocessing"]["normalization"] == (
        normalization
    )


def test_the_implemented_types_are_those_of_the_specs() -> None:
    # The three of feature 008, and image and anomaly from feature 010.
    assert set(INPUT_TYPES) == {"number", "binary", "category", "image"}
    assert set(OUTPUT_TYPES) == {"category", "binary", "number", "anomaly"}


def test_a_number_output_takes_its_loss_and_clip(tmp_path) -> None:
    def edit(document):
        document["output_features"] = [
            {
                "name": "torque",
                "type": "number",
                "loss": {"type": "huber"},
                "clip": [0, 300],
                "mae_increase_max": 2.5,
            }
        ]

    output = resolved(tmp_path, edit)["output_features"][0]
    assert output["loss"] == {"type": "huber"}
    assert output["clip"] == [0, 300]
    assert output["mae_increase_max"] == 2.5


# --- the rules ---------------------------------------------------------------------------------


def test_an_unimplemented_type_is_cf_14_naming_the_implemented_types(tmp_path) -> None:
    def edit(document):
        document["input_features"][1]["type"] = "text"

    rule, path, problem = refused(tmp_path, edit)
    assert (rule, path) == ("CF-14", "input_features[1].type")
    assert "number, binary, category" in problem


def test_an_unimplemented_output_type_is_cf_14(tmp_path) -> None:
    def edit(document):
        document["output_features"][0]["type"] = "set"

    assert refused(tmp_path, edit)[:2] == ("CF-14", "output_features[0].type")


def test_two_outputs_are_cf_17(tmp_path) -> None:
    def edit(document):
        document["output_features"].append({"name": "other", "type": "binary"})

    assert refused(tmp_path, edit)[:2] == ("CF-17", "output_features")


def test_no_output_is_cf_17(tmp_path) -> None:
    def edit(document):
        document["output_features"] = []

    assert refused(tmp_path, edit)[:2] == ("CF-17", "output_features")


def test_stratify_on_another_column_is_cf_15(tmp_path) -> None:
    def edit(document):
        document["preprocessing"]["split"] = {"type": "stratify", "column": "speed"}

    assert refused(tmp_path, edit)[:2] == ("CF-15", "preprocessing.split.column")


def test_stratify_on_a_number_output_is_cf_15(tmp_path) -> None:
    def edit(document):
        document["output_features"] = [{"name": "torque", "type": "number", "mae_increase_max": 1}]
        document["preprocessing"]["split"] = {"type": "stratify"}

    assert refused(tmp_path, edit)[:2] == ("CF-15", "preprocessing.split.column")


def test_stratify_without_a_column_takes_the_output(tmp_path) -> None:
    def edit(document):
        document["preprocessing"]["split"] = {"type": "stratify"}

    assert resolved(tmp_path, edit)["preprocessing"]["split"]["column"] == "state"


def test_mae_on_a_category_is_cf_16(tmp_path) -> None:
    def edit(document):
        document["output_features"][0]["mae_increase_max"] = 0.5

    assert refused(tmp_path, edit)[:2] == ("CF-16", "output_features[0].mae_increase_max")


def test_accuracy_on_a_number_is_cf_16(tmp_path) -> None:
    def edit(document):
        document["output_features"] = [
            {"name": "torque", "type": "number", "accuracy_drop_max": 0.02}
        ]

    assert refused(tmp_path, edit)[:2] == ("CF-16", "output_features[0].accuracy_drop_max")


def test_a_missing_budget_is_cf_16(tmp_path) -> None:
    def edit(document):
        del document["output_features"][0]["accuracy_drop_max"]

    assert refused(tmp_path, edit)[:2] == ("CF-16", "output_features[0].accuracy_drop_max")


def test_probabilities_with_a_fixed_split_are_cf_12(tmp_path) -> None:
    def edit(document):
        document["preprocessing"]["split"] = {
            "type": "fixed",
            "column": "part",
            "probabilities": [0.7, 0.15, 0.15],
        }

    assert refused(tmp_path, edit)[:2] == ("CF-12", "preprocessing.split.probabilities")


def test_a_fixed_split_without_a_column_is_cf_12(tmp_path) -> None:
    def edit(document):
        document["preprocessing"]["split"] = {"type": "fixed"}

    assert refused(tmp_path, edit)[:2] == ("CF-12", "preprocessing.split.column")


@pytest.mark.parametrize("column", ["speed", "state"])
def test_the_split_column_as_a_feature_or_the_output_is_cf_13(tmp_path, column) -> None:
    def edit(document):
        document["preprocessing"]["split"] = {"type": "fixed", "column": column}

    assert refused(tmp_path, edit)[:2] == ("CF-13", "preprocessing.split.column")


def test_a_feature_naming_the_output_column_is_cf_11(tmp_path) -> None:
    def edit(document):
        document["input_features"].append({"name": "state", "type": "category"})

    assert refused(tmp_path, edit)[:2] == ("CF-11", "input_features[3].name")


@pytest.mark.parametrize("name", ["Speed", "wheel-speed", "1st", "x" * 33])
def test_a_name_outside_the_form_is_cf_9(tmp_path, name) -> None:
    def edit(document):
        document["input_features"][0]["name"] = name

    assert refused(tmp_path, edit)[:2] == ("CF-9", "input_features[0].name")


def test_the_same_column_twice_is_cf_9(tmp_path) -> None:
    def edit(document):
        document["input_features"].append({"name": "speed", "type": "number"})

    assert refused(tmp_path, edit)[:2] == ("CF-9", "input_features[3].name")


def test_a_window_the_template_needs_is_cf_6(tmp_path) -> None:
    def edit(document):
        del document["preprocessing"]["window_size"]

    assert refused(tmp_path, edit)[:2] == ("CF-6", "preprocessing.window_size")


def test_probabilities_that_do_not_sum_to_one_are_cf_1(tmp_path) -> None:
    def edit(document):
        document["preprocessing"]["split"] = {"probabilities": [0.5, 0.2, 0.2]}

    assert refused(tmp_path, edit)[:2] == ("CF-1", "preprocessing.split.probabilities")


# --- keys that do not apply to the type are refused, never ignored (Principle I) ----------------


@pytest.mark.parametrize(
    ("index", "key", "value"),
    [
        (0, "most_common", 10),
        (0, "vocab", [1, 2]),
        (1, "normalization", "zscore"),
        (2, "most_common", 10),
        (1, "fallback_true_label", "yes"),
    ],
)
def test_a_preprocessing_key_of_another_type_is_refused(tmp_path, index, key, value) -> None:
    def edit(document):
        document["input_features"][index]["preprocessing"] = {key: value}

    rule, path, problem = refused(tmp_path, edit)
    assert rule is None
    assert path == f"input_features[{index}].preprocessing.{key}"
    assert "does not apply" in problem


def test_a_number_filled_with_text_is_refused(tmp_path) -> None:
    def edit(document):
        document["input_features"][0]["preprocessing"] = {"fill_value": "none"}

    assert refused(tmp_path, edit)[1] == "input_features[0].preprocessing.fill_value"


def test_an_encoder_on_a_number_is_refused(tmp_path) -> None:
    def edit(document):
        document["input_features"][0]["encoder"] = {"type": "dense"}

    assert refused(tmp_path, edit)[1] == "input_features[0].encoder"


def test_fill_with_mean_on_a_category_is_refused(tmp_path) -> None:
    def edit(document):
        document["input_features"][1]["preprocessing"] = {
            "missing_value_strategy": "fill_with_mean"
        }

    assert refused(tmp_path, edit)[1] == "input_features[1].preprocessing.missing_value_strategy"


def test_an_embedding_size_with_onehot_is_refused(tmp_path) -> None:
    def edit(document):
        document["input_features"][1]["encoder"] = {"type": "onehot", "embedding_size": 4}

    assert refused(tmp_path, edit)[1] == "input_features[1].encoder.embedding_size"


def test_a_threshold_on_a_category_output_is_refused(tmp_path) -> None:
    def edit(document):
        document["output_features"][0]["threshold"] = 0.3

    assert refused(tmp_path, edit)[1] == "output_features[0].threshold"


# --- defaults per type (US4, T011) ------------------------------------------------------------


def test_defaults_apply_to_every_feature_of_the_type_without_its_own_value(tmp_path) -> None:
    def edit(document):
        document["input_features"].append({"name": "rpm", "type": "number"})
        document["input_features"][0]["preprocessing"] = {"normalization": "iq"}
        document["defaults"] = {"number": {"preprocessing": {"normalization": "minmax"}}}

    features = resolved(tmp_path, edit)["input_features"]
    assert features[0]["preprocessing"]["normalization"] == "iq"  # the feature's own value wins
    assert features[3]["preprocessing"]["normalization"] == "minmax"


def test_a_default_encoder_applies_to_every_category(tmp_path) -> None:
    def edit(document):
        document["defaults"] = {"category": {"encoder": {"type": "onehot"}}}

    gear = resolved(tmp_path, edit)["input_features"][1]
    assert gear["encoder"] == {"type": "onehot"}


def test_a_default_for_an_absent_type_is_accepted_and_rendered(tmp_path) -> None:
    def edit(document):
        document["input_features"] = [{"name": "speed", "type": "number"}]
        document["defaults"] = {"category": {"preprocessing": {"most_common": 8}}}

    out = resolved(tmp_path, edit)
    assert out["defaults"] == {"category": {"preprocessing": {"most_common": 8}}}


def test_a_default_for_an_unimplemented_type_is_cf_14(tmp_path) -> None:
    def edit(document):
        document["defaults"] = {"text": {"preprocessing": {}}}

    assert refused(tmp_path, edit)[:2] == ("CF-14", "defaults.text")


def test_a_default_key_of_another_type_is_refused(tmp_path) -> None:
    def edit(document):
        document["defaults"] = {"number": {"preprocessing": {"most_common": 8}}}

    assert refused(tmp_path, edit)[1] == "defaults.number.preprocessing.most_common"
