"""The ``autoencoder`` template and the ``anomaly`` output, as the manifest sees them (feature 010).

Core only: the parameter half and the rules across template and output validate without a
framework. What a built model does is in ``tests/train/test_anomaly_pipeline.py``.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from caravan.manifest._yaml import dump_mapping
from caravan.manifest.errors import (
    RULE_BUDGET_FOR_TYPE,
    RULE_TEMPLATE_OUTPUT,
    RULE_TEMPLATE_PARAMETERS,
)
from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import resolve
from caravan.templates.autoencoder import AutoencoderParameters
from caravan.templates.registry import default_registry

BASE: dict[str, Any] = {
    "apiVersion": "caravan/v0.2",
    "model": {
        "name": "probe",
        "version": "0.0.1",
        "template": "autoencoder",
        "params": {"encoder": [16, 8], "code": 2},
    },
    "input_features": [{"name": "m0", "type": "number"}, {"name": "m1", "type": "number"}],
    "output_features": [{"name": "condition", "type": "anomaly", "auc_drop_max": 0.02}],
    "preprocessing": {"window_size": 5},
    "dataset": "data/",
    "export": {"targets": ["stm32h743"], "representative_samples": 100},
}


def outcome(tmp_path, edit=None):
    document = copy.deepcopy(BASE)
    if edit is not None:
        edit(document)
    path = tmp_path / "probe.yaml"
    path.write_text(dump_mapping(document), encoding="utf-8")
    return load_manifest(path)


def test_the_template_is_registered_for_anomaly_only() -> None:
    spec = default_registry().get("autoencoder")
    assert spec is not None
    assert spec.output_types == ("anomaly",)
    assert spec.consumes_window
    assert not spec.takes_images


def test_the_decoder_defaults_to_the_encoder_reversed() -> None:
    assert AutoencoderParameters(encoder=[64, 32], code=8).decoder == [32, 64]
    assert AutoencoderParameters(encoder=[64], code=8, decoder=[16, 16]).decoder == [16, 16]


@pytest.mark.parametrize(
    "params",
    [
        {"encoder": [], "code": 2},
        {"encoder": [0], "code": 2},
        {"encoder": [8], "code": 0},
        {"encoder": [8], "code": 2, "dropout": 1.0},
        {"encoder": [8], "code": 2, "decoder": [-1]},
        {"encoder": [8], "code": 2, "hidden": [4]},
    ],
)
def test_bad_parameters_are_refused(params) -> None:
    with pytest.raises(ValidationError):
        AutoencoderParameters.model_validate(params)


def test_a_valid_anomaly_manifest_resolves_every_default(tmp_path) -> None:
    result = outcome(tmp_path)
    assert result.is_valid, [finding.as_dict() for finding in result.findings]
    resolved = resolve(result.manifest)
    assert resolved["model"]["params"] == {
        "encoder": [16, 8],
        "code": 2,
        "decoder": [8, 16],
        "dropout": 0.0,
    }
    assert resolved["output_features"][0] == {
        "name": "condition",
        "type": "anomaly",
        "preprocessing": {"normal_label": "normal"},
        "threshold_percentile": 95.0,
        "auc_drop_max": 0.02,
    }


def test_stated_normal_label_and_percentile_are_kept(tmp_path) -> None:
    def edit(document):
        document["output_features"][0]["preprocessing"] = {"normal_label": "ok"}
        document["output_features"][0]["threshold_percentile"] = 99

    output = resolve(outcome(tmp_path, edit).manifest)["output_features"][0]
    assert output["preprocessing"]["normal_label"] == "ok"
    assert output["threshold_percentile"] == 99


def test_a_parameter_refusal_names_the_parameter(tmp_path) -> None:
    def edit(document):
        document["model"]["params"]["code"] = 0

    finding = outcome(tmp_path, edit).findings[0]
    assert finding.rule == RULE_TEMPLATE_PARAMETERS
    assert finding.path == "model.params.code"


def test_the_autoencoder_does_not_answer_a_category(tmp_path) -> None:
    def edit(document):
        document["output_features"] = [
            {"name": "state", "type": "category", "accuracy_drop_max": 0.02}
        ]

    finding = outcome(tmp_path, edit).findings[0]
    assert (finding.rule, finding.path) == (RULE_TEMPLATE_OUTPUT, "model.template")
    assert "anomaly" in finding.problem
    assert "conv1d" in finding.accepted and "mlp" in finding.accepted


def test_a_classifier_does_not_answer_an_anomaly(tmp_path) -> None:
    def edit(document):
        document["model"] = {
            "name": "probe",
            "version": "0.0.1",
            "template": "mlp",
            "params": {"hidden": [4]},
        }

    finding = outcome(tmp_path, edit).findings[0]
    assert (finding.rule, finding.path) == (RULE_TEMPLATE_OUTPUT, "model.template")
    assert finding.accepted == ("autoencoder",)


@pytest.mark.parametrize("wrong", ["accuracy_drop_max", "mae_increase_max"])
def test_an_anomaly_states_its_budget_as_auc(tmp_path, wrong) -> None:
    def edit(document):
        document["output_features"][0][wrong] = 0.02

    finding = outcome(tmp_path, edit).findings[0]
    assert (finding.rule, finding.path) == (RULE_BUDGET_FOR_TYPE, f"output_features[0].{wrong}")
    assert finding.accepted == ("auc_drop_max",)


def test_an_anomaly_without_a_budget_is_refused(tmp_path) -> None:
    def edit(document):
        del document["output_features"][0]["auc_drop_max"]

    finding = outcome(tmp_path, edit).findings[0]
    assert (finding.rule, finding.path) == (
        RULE_BUDGET_FOR_TYPE,
        "output_features[0].auc_drop_max",
    )


@pytest.mark.parametrize(
    ("key", "value"), [("threshold_percentile", 95), ("preprocessing", {"normal_label": "ok"})]
)
def test_anomaly_keys_do_not_apply_to_a_category(tmp_path, key, value) -> None:
    def edit(document):
        document["model"] = {
            "name": "probe",
            "version": "0.0.1",
            "template": "mlp",
            "params": {"hidden": [4]},
        }
        output = {"name": "state", "type": "category", "accuracy_drop_max": 0.02, key: value}
        document["output_features"] = [output]

    result = outcome(tmp_path, edit)
    assert not result.is_valid
    assert "does not apply to a category output" in result.findings[0].problem
