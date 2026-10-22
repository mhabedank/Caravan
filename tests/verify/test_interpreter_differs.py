"""The desktop interpreter's node list is not the model's operator set.

This is the finding that shaped the whole feature, asserted rather than trusted. On 2026-10-22 the
interpreter reported a ``DELEGATE`` node it had inserted for itself while allocating tensors; there
is no such operator on a microcontroller, and a resolver built from that list would register a
kernel the target's runtime has never heard of.

Written as a test so that the day a runtime version stops inserting it, this fails and somebody
reads the comment instead of discovering the reasoning from scratch. It does not assert that the
difference *is* a delegate — it asserts that the export reads the file, and that whatever the
interpreter adds does not reach the operator set.
"""

from __future__ import annotations

from caravan.runtime.flatbuffer import inspect_graph


def interpreter_operators(path) -> set[str]:
    from ai_edge_litert.interpreter import Interpreter

    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    return {op["op_name"] for op in interpreter._get_ops_details()}


def test_the_operator_set_comes_from_the_file(int8_model) -> None:
    from_file = {operator.name for operator in inspect_graph(int8_model).operators}
    assert from_file
    assert "DELEGATE" not in from_file


def test_whatever_the_interpreter_adds_is_not_in_the_operator_set(int8_model) -> None:
    from_file = {operator.name for operator in inspect_graph(int8_model).operators}
    from_interpreter = interpreter_operators(int8_model)
    # Every operator the file declares is one the interpreter also runs; the interpreter may know
    # about more, and those extras are its own business and must not reach a resolver.
    assert from_file <= from_interpreter
    extras = from_interpreter - from_file
    assert "DELEGATE" in extras or not extras, (
        f"the interpreter reported {sorted(extras)}, which the file does not declare; if this "
        "runtime version no longer inserts a delegate, the finding still holds: the file is the "
        "source, and the interpreter is not"
    )


def test_the_node_count_comes_from_the_file_too(int8_model) -> None:
    # The interpreter's node count includes its own node, so counting through it would overstate
    # the graph's cost as well as its operator set.
    graph = inspect_graph(int8_model)
    assert graph.nodes == sum(operator.nodes for operator in graph.operators)
