"""The window check: what it refuses, and whether its message can be acted on.

The check's value is not the boolean — it is the sentence. An author who is told "this does not
fit" has to bisect their own manifest; an author who is told which block, how much window was left
when it was reached, and what would fit instead can change one number and move on.
"""

from __future__ import annotations

from caravan.templates.conv1d import Conv1dParameters, window_fit
from caravan.templates.registry import default_registry

TIGHT = {
    "blocks": [
        {"filters": 16, "kernel": 5, "stride": 2, "pool": 2},
        {"filters": 32, "kernel": 5},
    ]
}
FIXTURE = {
    "blocks": [
        {"filters": 16, "kernel": 5, "stride": 2, "normalise": True, "pool": 2},
        {"filters": 32, "kernel": 3, "dropout": 0.1},
    ]
}


def params(raw) -> Conv1dParameters:
    return Conv1dParameters.model_validate(raw)


def test_a_fitting_configuration_returns_nothing() -> None:
    assert window_fit(params(FIXTURE), 64) is None


def test_the_named_models_shape_fits_its_configuration() -> None:
    assert window_fit(params(FIXTURE), 128) is None


def test_a_window_that_is_too_short_is_refused() -> None:
    message = window_fit(params(TIGHT), 16)
    assert message is not None


def test_the_message_names_the_block_the_length_and_a_fitting_window() -> None:
    verdict = window_fit(params(TIGHT), 16)
    assert verdict is not None
    problem, accepted = verdict
    assert "block 2" in problem
    assert "3 samples left" in problem
    assert "kernel spans 5" in problem
    # The alternative, computed by walking the blocks: 22 does not fit and 23 does.
    assert "a window of 23 or more" in accepted


def test_the_suggested_window_is_the_truth_and_not_an_estimate() -> None:
    # The documents of this feature first said 26. Walking says 23, and the message must say what
    # walking says, because an author will take the number and use it.
    assert window_fit(params(TIGHT), 23) is None
    assert window_fit(params(TIGHT), 22) is not None


def test_the_message_offers_dropping_the_pooling_when_there_is_pooling_to_drop() -> None:
    verdict = window_fit(params(TIGHT), 16)
    assert verdict is not None
    assert "no pooling in block 1" in verdict[1]


def test_a_single_block_refusal_does_not_offer_a_block_zero() -> None:
    # The first block has no predecessor, so there is no earlier pooling to suggest removing.
    verdict = window_fit(params({"blocks": [{"filters": 8, "kernel": 9}]}), 4)
    assert verdict is not None
    whole = verdict[0] + " " + " ".join(verdict[1])
    assert "block 1" in whole
    assert "block 0" not in whole


def test_the_dense_template_has_no_window_check_and_is_unaffected() -> None:
    # Optional on purpose: most templates have nothing to check here, and a required field would
    # make every third-party template carry a stub.
    assert default_registry().get("mlp").window_fit is None


def test_the_convolutional_template_declares_one() -> None:
    spec = default_registry().get("conv1d")
    assert spec is not None
    assert spec.window_fit is not None
    assert spec.consumes_window is True
