"""The ``conv2d`` template as the manifest sees it (feature 010, User Story 2)."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from caravan.manifest._yaml import dump_mapping
from caravan.manifest.errors import RULE_TEMPLATE_PARAMETERS, RULE_WINDOW_MATCHES_TEMPLATE
from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import resolve
from caravan.templates.conv2d import Conv2dParameters
from caravan.templates.registry import default_registry

BASE: dict[str, Any] = {
    "apiVersion": "caravan/v0.2",
    "model": {
        "name": "probe",
        "version": "0.0.1",
        "template": "conv2d",
        "params": {"blocks": [{"filters": 8, "kernel": 3}]},
    },
    "input_features": [{"name": f"c{index}", "type": "number"} for index in range(8)],
    "output_features": [{"name": "label", "type": "category", "accuracy_drop_max": 0.02}],
    "preprocessing": {"window_size": 12},
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


def test_the_template_is_registered_for_the_classifying_outputs_and_images() -> None:
    spec = default_registry().get("conv2d")
    assert spec is not None
    assert spec.output_types == ("category", "binary", "number")
    assert spec.takes_images and spec.consumes_window
    assert spec.plane_fit is not None


def test_every_default_is_resolved(tmp_path) -> None:
    result = outcome(tmp_path)
    assert result.is_valid, [finding.as_dict() for finding in result.findings]
    params = resolve(result.manifest)["model"]["params"]
    assert params == {
        "blocks": [
            {
                "kind": "standard",
                "filters": 8,
                "kernel": 3,
                "stride": 1,
                "padding": "valid",
                "normalise": False,
                "pool": None,
                "dropout": 0.0,
            }
        ],
        "head": "average",
    }


@pytest.mark.parametrize(
    "block",
    [
        {"filters": 0, "kernel": 3},
        {"filters": 8, "kernel": [3]},
        {"filters": 8, "kernel": [3, 3, 3]},
        {"filters": 8, "kernel": [3, 0]},
        {"filters": 8, "kernel": 3, "kind": "residual"},
        {"filters": 8, "kernel": 3, "padding": "causal"},
        {"filters": 8, "kernel": 3, "dropout": 1.0},
        {"filters": 8, "kernel": 3, "dilation": 2},
    ],
)
def test_bad_blocks_are_refused(block) -> None:
    with pytest.raises(ValidationError):
        Conv2dParameters.model_validate({"blocks": [block]})


def test_a_refusal_names_the_block(tmp_path) -> None:
    def edit(document):
        document["model"]["params"]["blocks"].append({"filters": 8, "kernel": [3, 0]})

    finding = outcome(tmp_path, edit).findings[0]
    assert finding.rule == RULE_TEMPLATE_PARAMETERS
    assert finding.path.startswith("model.params.blocks[1].kernel")


def test_a_kernel_too_wide_for_the_columns_is_refused_at_validation(tmp_path) -> None:
    def edit(document):
        document["model"]["params"]["blocks"] = [{"filters": 8, "kernel": [3, 9]}]

    finding = outcome(tmp_path, edit).findings[0]
    assert (finding.rule, finding.path) == (
        RULE_WINDOW_MATCHES_TEMPLATE,
        "preprocessing.window_size",
    )
    assert "columns axis has 8 columns" in finding.problem
    assert "at least 9 columns" in finding.accepted


def test_a_window_too_short_for_the_rows_is_refused(tmp_path) -> None:
    def edit(document):
        document["preprocessing"]["window_size"] = 2

    finding = outcome(tmp_path, edit).findings[0]
    assert finding.rule == RULE_WINDOW_MATCHES_TEMPLATE
    assert "rows axis has 2 rows" in finding.problem


def test_a_category_of_unknown_width_leaves_the_columns_to_the_build(tmp_path) -> None:
    # A one-hot category's width is its vocabulary, learned from the data: the columns axis is
    # unknown at validation, so a kernel wider than the numbers alone is not refused here.
    def edit(document):
        document["input_features"] = [
            {"name": "a", "type": "number"},
            {"name": "gear", "type": "category", "encoder": {"type": "onehot"}},
        ]
        document["model"]["params"]["blocks"] = [{"filters": 8, "kernel": [3, 4]}]

    assert outcome(tmp_path, edit).is_valid


def test_a_stated_embedding_counts_its_columns(tmp_path) -> None:
    def edit(document):
        document["input_features"] = [
            {"name": "a", "type": "number"},
            {"name": "gear", "type": "category", "encoder": {"embedding_size": 2}},
        ]
        document["model"]["params"]["blocks"] = [{"filters": 8, "kernel": [3, 4]}]

    finding = outcome(tmp_path, edit).findings[0]
    assert finding.rule == RULE_WINDOW_MATCHES_TEMPLATE
    assert "columns axis has 3 columns" in finding.problem
