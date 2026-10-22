"""The resolver: exactly this model's operators, each once, in graph order."""

from __future__ import annotations

import pytest

from caravan.export import resolver
from caravan.manifest.errors import RunRuleFailure
from caravan.runtime.flatbuffer import OperatorRecord

MLP = (
    OperatorRecord(name="RESHAPE", builtin_code=22, version=1, nodes=1),
    OperatorRecord(name="FULLY_CONNECTED", builtin_code=9, version=4, nodes=3),
    OperatorRecord(name="SOFTMAX", builtin_code=25, version=2, nodes=1),
)


def test_each_operator_is_registered_exactly_once() -> None:
    header = resolver.generate(MLP)
    for method in ("AddReshape", "AddFullyConnected", "AddSoftmax"):
        assert header.count(f"resolver.{method}();") == 1


def test_the_template_argument_is_the_distinct_count_not_the_node_count() -> None:
    # The runtime sizes the resolver by distinct operators; using the node count would reserve
    # entries nothing fills, and flash pays for the difference.
    header = resolver.generate(MLP)
    assert "MicroMutableOpResolver<3>" in header
    assert "<5>" not in header


def test_the_order_is_the_graph_order() -> None:
    header = resolver.generate(MLP)
    positions = [
        header.index(f"resolver.Add{name}") for name in ("Reshape", "FullyConnected", "Softmax")
    ]
    assert positions == sorted(positions)


def test_each_line_says_what_it_registers_and_how_many_nodes_use_it() -> None:
    header = resolver.generate(MLP)
    assert "/* FULLY_CONNECTED v4, 3 nodes */" in header
    assert "/* RESHAPE v1, 1 node */" in header


def test_no_operator_outside_the_graph_appears() -> None:
    header = resolver.generate(MLP)
    for absent in ("AddConv2D", "AddShape", "AddStridedSlice", "AddPack", "AddCustom"):
        assert absent not in header


def test_the_method_names_are_spelled_as_the_runtime_spells_them() -> None:
    # The whole reason the mapping is a table: camel-casing CONV_2D gives AddConv2d, which does
    # not exist, and the generic AddBuiltin is private so there is no fallback.
    header = resolver.generate(
        (OperatorRecord(name="CONV_2D", builtin_code=3, version=3, nodes=1),)
    )
    assert "resolver.AddConv2D();" in header
    assert "AddConv2d" not in header


def test_a_custom_operator_says_the_kernel_is_the_authors_job() -> None:
    header = resolver.generate(
        (OperatorRecord(name="my_op", builtin_code=32, version=1, nodes=1, custom_name="my_op"),)
    )
    assert 'AddCustom("my_op"' in header
    assert "you must supply the kernel" in header


def test_an_operator_the_runtime_cannot_resolve_refuses_the_run() -> None:
    # X-4. Better here than at the author's compiler, with a message that names the operator and
    # where caravan read its method list.
    from caravan.manifest.errors import RULE_OPERATOR_UNRESOLVABLE

    unknown = (OperatorRecord(name="WHILE", builtin_code=119, version=1, nodes=1),)
    with pytest.raises(RunRuleFailure) as raised:
        resolver.generate(unknown)
    assert raised.value.finding.rule == RULE_OPERATOR_UNRESOLVABLE
    assert "WHILE" in raised.value.finding.problem
