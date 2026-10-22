"""Reading a model's graph from the file, where no training framework exists.

This is the half of the export that has to run on a Python the converter cannot be installed on,
so it lives here beside the other runtime tests and is collected by the `measure` matrix.

What it asserts are invariants rather than a particular operator count: the committed fixture is
regenerated whenever the conversion changes, and a test pinned to today's count would fail for the
right reason in the wrong place. The count after the batch fix is asserted where that fix lives.
"""

from __future__ import annotations

from caravan.export.memory import read_write_total
from caravan.runtime.flatbuffer import inspect_graph


def test_the_operator_records_carry_what_a_resolver_needs(int8_model) -> None:
    graph = inspect_graph(int8_model)
    assert graph.operators, "a model with no operators would not be a model"
    for operator in graph.operators:
        assert operator.name and operator.name.isupper()
        assert operator.builtin_code >= 0
        assert operator.version >= 1
        assert operator.nodes >= 1
        assert operator.custom_name is None


def test_the_node_count_is_the_sum_of_the_per_operator_counts(int8_model) -> None:
    # The two numbers are different things — the resolver's length and the graph's cost — and the
    # report carries both, so they have to agree.
    graph = inspect_graph(int8_model)
    assert graph.nodes == sum(operator.nodes for operator in graph.operators)
    assert len(graph.operators) <= graph.nodes


def test_a_single_subgraph_model_says_so(int8_model) -> None:
    assert inspect_graph(int8_model).subgraphs == 1


def test_the_shapes_have_a_batch_dimension_first(int8_model) -> None:
    graph = inspect_graph(int8_model)
    assert graph.input_shape[0] == 1
    assert graph.output_shape[0] == 1


def test_the_floor_is_a_floor_and_the_total_is_the_larger(int8_model) -> None:
    graph = inspect_graph(int8_model)
    assert 0 < graph.working_memory_floor <= graph.read_write_total
    assert graph.read_write_total == read_write_total(graph.lifetimes)


def test_the_recorded_size_is_the_file_size(int8_model) -> None:
    assert inspect_graph(int8_model).model_bytes == int8_model.stat().st_size


def test_the_fully_connected_operator_is_found_with_its_version(int8_model) -> None:
    # One concrete assertion, because every invariant above would also hold for an empty reading
    # of the wrong field.
    by_name = {operator.name: operator for operator in inspect_graph(int8_model).operators}
    assert "FULLY_CONNECTED" in by_name
    assert by_name["FULLY_CONNECTED"].builtin_code == 9
    assert by_name["FULLY_CONNECTED"].version >= 1
    assert by_name["FULLY_CONNECTED"].nodes == 2
