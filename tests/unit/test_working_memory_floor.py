"""The working-memory floor is an arithmetic claim, so it is tested as one.

The number this computes is the one the export publishes, and it is published as a *floor*. That
word is the whole content of the test: the sum of the read-write tensors is not a floor, because a
planner reuses one buffer for tensors whose lifetimes do not overlap. The peak of simultaneously
live tensors is, because no planner can hold less than what is live at once.

The arithmetic lives in the core and not behind the runtime extra on purpose: it is the claim most
worth checking and it needs no model file to check, so a test in an installation with no extra at
all can hold it.
"""

from __future__ import annotations

from caravan.export.memory import TensorLifetime, peak_live, read_write_total


def test_a_chain_lets_a_planner_reuse_buffers() -> None:
    # Four tensors of 100 bytes, each live only across one node: a planner needs two at a time.
    chain = tuple(
        TensorLifetime(index=i, bytes=100, first_node=i, last_node=i + 1) for i in range(4)
    )
    assert read_write_total(chain) == 400
    assert peak_live(chain, nodes=5) == 200


def test_the_peak_is_what_is_live_at_once() -> None:
    # Two large tensors whose lifetimes overlap cannot share a buffer.
    overlapping = (
        TensorLifetime(index=0, bytes=1000, first_node=0, last_node=3),
        TensorLifetime(index=1, bytes=1000, first_node=1, last_node=3),
        TensorLifetime(index=2, bytes=10, first_node=2, last_node=2),
    )
    assert peak_live(overlapping, nodes=4) == 2010


def test_the_peak_never_exceeds_the_sum() -> None:
    # The relation that makes the two figures bound different things: whatever the graph, the peak
    # is the smaller or equal one, so publishing the sum as a floor would overstate it.
    for spread in (0, 1, 2, 5):
        lifetimes = tuple(
            TensorLifetime(index=i, bytes=64, first_node=i, last_node=i + spread) for i in range(6)
        )
        assert peak_live(lifetimes, nodes=12) <= read_write_total(lifetimes)


def test_a_graph_input_is_live_before_the_first_node() -> None:
    # -1 is the input's first node: it exists before anything runs, so it is live at node 0.
    tensors = (
        TensorLifetime(index=0, bytes=320, first_node=-1, last_node=0),
        TensorLifetime(index=1, bytes=32, first_node=0, last_node=1),
    )
    assert peak_live(tensors, nodes=2) == 352


def test_a_graph_output_is_live_after_the_last_node() -> None:
    # The node count is the output's last node: it must survive the final operator.
    tensors = (
        TensorLifetime(index=0, bytes=16, first_node=0, last_node=1),
        TensorLifetime(index=1, bytes=8, first_node=1, last_node=2),
    )
    assert peak_live(tensors, nodes=2) == 24


def test_an_empty_graph_has_no_floor_rather_than_a_wrong_one() -> None:
    assert peak_live((), nodes=0) == 0
    assert read_write_total(()) == 0
