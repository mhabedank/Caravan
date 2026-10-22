"""Which samples calibrate the quantization, and the state the schema makes possible."""

from __future__ import annotations

from caravan.stages.quantize import plan_calibration

TRAIN = tuple(range(56))


def test_the_same_seed_draws_the_same_samples() -> None:
    first = plan_calibration(20, TRAIN, seed=42)
    again = plan_calibration(20, TRAIN, seed=42)
    assert first.indices == again.indices


def test_another_seed_draws_other_samples() -> None:
    assert (
        plan_calibration(20, TRAIN, seed=42).indices != plan_calibration(20, TRAIN, seed=43).indices
    )


def test_the_draw_is_capped_by_what_the_split_holds_and_says_so() -> None:
    # The fixture's own case: the pilot manifest asks for 500 and the training split holds 56.
    plan = plan_calibration(500, TRAIN, seed=42)
    assert plan.requested == 500
    assert plan.available == 56
    assert plan.used == 56
    assert len(plan.indices) == 56
    # All three numbers, because the one thing that is not acceptable is silence.
    assert plan.as_dict() == {
        "requested": 500,
        "available": 56,
        "used": 56,
        "split": "train",
        "seed": 42,
    }


def test_no_calibration_count_is_a_valid_state_and_not_an_error() -> None:
    # ``representative_samples`` is optional in the schema and rule CF-4 demands it only for int8,
    # so a float16 or none manifest legitimately has none. ``min(None, 56)`` would raise here on
    # correct input, which the analysis pass caught before this was written.
    plan = plan_calibration(None, TRAIN, seed=42)
    assert plan.requested is None
    assert plan.used == 0
    assert plan.indices == ()
    assert plan.as_dict()["requested"] is None


def test_every_drawn_index_is_in_the_training_split() -> None:
    # There must be no path that calibrates on the test split: a quantization fitted to the data
    # it is then judged on has a measurement that means nothing.
    plan = plan_calibration(30, tuple(range(100, 156)), seed=1)
    assert set(plan.indices) <= set(range(100, 156))


def test_asking_for_fewer_than_available_draws_exactly_that_many() -> None:
    plan = plan_calibration(10, TRAIN, seed=5)
    assert plan.used == 10
    assert len(set(plan.indices)) == 10  # a sample, so no repeats
