"""The kernel coverage data, checked against the schema that defines operator names.

Here rather than in ``tests/unit`` because the authority on an operator's name is the model
schema, which ships with the runtime extra. A data file naming ``FULLYCONNECTED`` would otherwise
be a verdict that silently never matches anything.
"""

from __future__ import annotations

from caravan.targets.kernels import default_libraries


def schema_operator_names() -> set[str]:
    from ai_edge_litert import schema_py_generated as schema

    return {
        name
        for name, value in vars(schema.BuiltinOperator).items()
        if isinstance(value, int) and name.isupper()
    }


def test_every_mapped_operator_is_one_the_schema_knows() -> None:
    known = schema_operator_names()
    for library in default_libraries().values():
        unknown = sorted(set(library.operators) - known)
        assert not unknown, (
            f"{library.library} maps operator names the schema does not have: {unknown}"
        )


def test_every_library_carries_a_source_and_a_date() -> None:
    for library in default_libraries().values():
        assert library.source.strip()
        assert library.read_on.strip()
        assert library.runtime == "tflm"


def test_the_pilot_models_operators_are_all_decided() -> None:
    # Decided, not necessarily covered: RESHAPE is a fallback on both libraries, which is a
    # verdict. What would be wrong is an operator about which the data says nothing at all.
    for library in default_libraries().values():
        for operator in ("FULLY_CONNECTED", "SOFTMAX"):
            assert operator in library.operators
