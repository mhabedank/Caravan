"""The two-axis walk of the ``conv2d`` template (feature 010, research R3).

Each axis follows ``sequence.py``'s verified formulas on its own, so these cases check the
bookkeeping — which axis, which block, what is left — rather than re-deriving the arithmetic.
"""

from __future__ import annotations

from caravan.templates.plane import as_pair, axis_blocks, walk_plane


def block(**values):
    return {"kernel": 3, "stride": 1, "padding": "valid", "pool": None, **values}


def test_an_int_is_a_square_and_a_pair_is_rows_then_columns() -> None:
    assert as_pair(3) == (3, 3)
    assert as_pair([10, 4]) == (10, 4)
    assert as_pair(None) is None


def test_each_axis_sees_its_own_kernel_stride_and_pool() -> None:
    blocks = [block(kernel=[10, 4], stride=[2, 1], pool=[2, 1])]
    assert axis_blocks(blocks, 0) == [{"kernel": 10, "stride": 2, "padding": "valid", "pool": 2}]
    assert axis_blocks(blocks, 1) == [{"kernel": 4, "stride": 1, "padding": "valid", "pool": 1}]


def test_the_keyword_spotting_reference_leaves_a_25_by_5_plane() -> None:
    # 49 x 10, a (10, 4) kernel at stride 2 with same padding, then four 3 x 3 same blocks.
    blocks = [block(kernel=[10, 4], stride=2, padding="same")] + [block(padding="same")] * 4
    outcome = walk_plane(49, 10, blocks)
    assert outcome.fits
    assert outcome.final == (25, 5)


def test_the_columns_axis_can_fail_while_the_rows_axis_fits() -> None:
    outcome = walk_plane(12, 2, [block(kernel=[3, 4])])
    assert not outcome.fits
    assert (outcome.axis, outcome.failed_block, outcome.size_there, outcome.kernel_there) == (
        "columns",
        1,
        2,
        4,
    )
    assert outcome.smallest == 4


def test_pooling_can_exhaust_an_axis_before_the_next_block() -> None:
    # 8 rows, a 3-row kernel leaves 6, pooling by 4 leaves 1, and block 2's kernel spans 3.
    outcome = walk_plane(8, 8, [block(pool=4), block()])
    assert not outcome.fits
    assert (outcome.axis, outcome.failed_block, outcome.size_there) == ("rows", 2, 1)


def test_an_unknown_axis_is_skipped() -> None:
    outcome = walk_plane(None, 2, [block()])
    assert not outcome.fits and outcome.axis == "columns"
    assert walk_plane(12, None, [block()]).fits
