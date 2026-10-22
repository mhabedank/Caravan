"""Every parameter of the conv1d template, rejected at its bounds and named where it is.

The point of each case is the *path*: an author with four blocks needs to be told which one is
wrong, not that "blocks" is wrong. That is FR-011, and it is the difference between a message
somebody can act on and a message somebody has to bisect.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from caravan.templates.conv1d import Conv1dParameters

VALID = {
    "blocks": [
        {"filters": 16, "kernel": 5, "stride": 2, "normalise": True, "pool": 2},
        {"filters": 32, "kernel": 3, "dropout": 0.1},
    ],
    "head": "average",
}


def test_the_valid_set_validates() -> None:
    params = Conv1dParameters.model_validate(VALID)
    assert len(params.blocks) == 2
    assert params.head == "average"


def test_the_defaults_are_the_documented_ones() -> None:
    params = Conv1dParameters.model_validate({"blocks": [{"filters": 8, "kernel": 3}]})
    block = params.blocks[0]
    assert (block.stride, block.padding, block.normalise, block.pool, block.dropout) == (
        1,
        "valid",
        False,
        None,
        0.0,
    )
    assert params.head == "average"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("filters", 0),
        ("filters", -4),
        ("kernel", 0),
        ("stride", 0),
        ("pool", 0),
        ("dropout", 1.0),
        ("dropout", -0.1),
        ("padding", "reflect"),
    ],
)
def test_a_bad_block_field_is_rejected_and_located(field: str, value) -> None:
    blocks = [dict(VALID["blocks"][0]), {"filters": 8, "kernel": 3}]
    blocks[1][field] = value
    with pytest.raises(ValidationError) as raised:
        Conv1dParameters.model_validate({"blocks": blocks, "head": "average"})
    location = raised.value.errors()[0]["loc"]
    # The second block, by position, and the field by name: that is what makes the message usable.
    assert location[0] == "blocks"
    assert location[1] == 1
    assert field in location


def test_an_empty_block_list_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Conv1dParameters.model_validate({"blocks": [], "head": "average"})


def test_an_unknown_head_is_rejected_and_names_the_field() -> None:
    with pytest.raises(ValidationError) as raised:
        Conv1dParameters.model_validate({**VALID, "head": "attention"})
    assert raised.value.errors()[0]["loc"] == ("head",)


def test_an_unknown_field_is_rejected_rather_than_ignored() -> None:
    # extra="forbid": a typo in a manifest is a refusal, not a silently dropped parameter.
    with pytest.raises(ValidationError):
        Conv1dParameters.model_validate({**VALID, "dilation": 2})
    with pytest.raises(ValidationError):
        Conv1dParameters.model_validate(
            {"blocks": [{"filters": 8, "kernel": 3, "activation": "tanh"}]}
        )


def test_what_the_template_deliberately_does_not_offer() -> None:
    # Principle X: separable convolution was measured and found cheap, and is still absent because
    # no named model needs it. Asserted so that adding it is a decision rather than a drift.
    from caravan.templates.conv1d import ConvBlock

    fields = set(Conv1dParameters.model_fields) | set(ConvBlock.model_fields)
    for absent in ("dilation", "separable", "residual", "attention", "activation"):
        assert absent not in fields


def test_pooling_may_be_left_out_entirely() -> None:
    params = Conv1dParameters.model_validate({"blocks": [{"filters": 8, "kernel": 3}]})
    assert params.blocks[0].pool is None


def test_a_single_channel_single_block_configuration_is_valid() -> None:
    # The commonest small configuration, and the one a first-time author writes.
    params = Conv1dParameters.model_validate({"blocks": [{"filters": 4, "kernel": 3}]})
    assert len(params.blocks) == 1
