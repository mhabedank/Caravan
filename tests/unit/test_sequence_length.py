"""The sequence-length arithmetic, against the cases the framework itself answered.

These numbers are not derived here. Every case below was run through Keras on 2026-10-22 and its
output shape read back (feature 005, research R5), including the two cases Keras refuses outright.
That matters because a wrong formula fails in one of two bad ways: it refuses a configuration that
would have worked, or it lets one through to die inside the framework with a shape error the author
cannot act on. So this file is the record of what the framework said, and the implementation has to
agree with it rather than with somebody's memory of how convolutions work.

The arithmetic lives in the core, not behind the training extra, so these run in an installation
with no framework at all — which is also the only place the claim "no framework needed to validate
a manifest" can be checked.
"""

from __future__ import annotations

import pytest

from caravan.templates.sequence import DOES_NOT_FIT, length_after_conv, length_after_pool, walk

#: (window, kernel, stride, padding, pool) -> length after the block, or DOES_NOT_FIT.
#: Measured against Keras; see the module docstring.
MEASURED = [
    ((64, 5, 1, "valid", None), 60),
    ((64, 5, 1, "valid", 2), 30),
    ((64, 5, 2, "valid", 2), 15),
    ((64, 5, 1, "same", None), 64),
    ((64, 5, 1, "same", 2), 32),
    ((64, 5, 2, "same", 2), 16),
    ((128, 5, 2, "valid", 2), 31),
    ((128, 3, 1, "valid", 4), 31),
    ((8, 5, 1, "valid", 2), 2),
    ((5, 5, 1, "valid", None), 1),
    ((4, 5, 1, "valid", None), DOES_NOT_FIT),  # Keras raises here
    ((3, 5, 1, "same", None), 3),
    ((2, 3, 1, "valid", 2), DOES_NOT_FIT),  # Keras raises here too
    ((6, 3, 1, "valid", 4), 1),
]


@pytest.mark.parametrize(("case", "expected"), MEASURED, ids=lambda value: str(value))
def test_the_formulas_agree_with_the_framework(case, expected) -> None:
    window, kernel, stride, padding, pool = case
    length = length_after_conv(window, kernel=kernel, stride=stride, padding=padding)
    if length is not DOES_NOT_FIT and pool is not None:
        length = length_after_pool(length, pool)
    assert length == expected


def test_same_padding_never_shortens_below_the_stride() -> None:
    # The surprising case of the measured set: a window of 3 with a kernel of 5 survives `same`
    # padding, because the padding is what makes it survive.
    assert length_after_conv(3, kernel=5, stride=1, padding="same") == 3
    assert length_after_conv(1, kernel=9, stride=1, padding="same") == 1


def test_valid_padding_refuses_a_window_shorter_than_the_kernel() -> None:
    assert length_after_conv(4, kernel=5, stride=1, padding="valid") is DOES_NOT_FIT
    assert length_after_conv(5, kernel=5, stride=1, padding="valid") == 1


def test_pooling_refuses_what_would_leave_nothing() -> None:
    assert length_after_pool(1, 2) is DOES_NOT_FIT
    assert length_after_pool(2, 2) == 1
    assert length_after_pool(3, 4) is DOES_NOT_FIT


def test_a_walk_reports_where_it_stopped() -> None:
    # What the refusal message is built from: which block failed, and the length when it was
    # reached. Without those two the author is told "it does not fit" and nothing else.
    blocks = [
        {"kernel": 5, "stride": 2, "padding": "valid", "pool": 2},
        {"kernel": 5, "stride": 1, "padding": "valid", "pool": None},
    ]
    outcome = walk(16, blocks)
    assert outcome.fits is False
    assert outcome.failed_block == 2
    assert outcome.length_there == 3


def test_a_walk_that_fits_reports_the_final_length() -> None:
    blocks = [
        {"kernel": 5, "stride": 2, "padding": "valid", "pool": 2},
        {"kernel": 3, "stride": 1, "padding": "valid", "pool": None},
    ]
    outcome = walk(64, blocks)
    assert outcome.fits is True
    assert outcome.failed_block is None
    assert outcome.length_there == 13  # 64 -> 30 -> 15 -> 13


def test_the_smallest_fitting_window_is_computed_and_not_estimated() -> None:
    # The refusal offers a fitting alternative, and an offer an author follows has to be right.
    # The documents first said 26 for this configuration; walking the blocks says 23.
    blocks = [
        {"kernel": 5, "stride": 2, "padding": "valid", "pool": 2},
        {"kernel": 5, "stride": 1, "padding": "valid", "pool": None},
    ]
    assert walk(22, blocks).fits is False
    assert walk(23, blocks).fits is True


def test_an_empty_block_list_is_the_window_itself() -> None:
    # Not a configuration the schema admits (blocks has at least one), but the walk should be
    # total: a fold over nothing returns what it started with.
    outcome = walk(64, [])
    assert outcome.fits is True
    assert outcome.length_there == 64
