"""The resolver method table, against what the templates actually emit.

The table is the answer to a trap: ``Add`` plus the camel-cased operator name is the obvious way to
generate a resolver and it produces code that does not compile. These tests hold the table to the
spelling the runtime uses, and hold its *coverage* to what this project can produce rather than to
somebody's idea of completeness.
"""

from __future__ import annotations

from caravan.export.methods import CUSTOM_METHOD, READ_ON, RESOLVER_METHODS, SOURCE, method_for

#: The operators the implemented templates produce today, after the input batch is fixed. `mlp`
#: gives the first three; `conv1d` will add the pooling and convolution entries.
EMITTED_BY_TEMPLATES = ("RESHAPE", "FULLY_CONNECTED", "SOFTMAX")


def test_every_operator_the_templates_emit_has_a_method() -> None:
    missing = [name for name in EMITTED_BY_TEMPLATES if method_for(name) is None]
    assert not missing, f"no resolver method for {missing}"


def test_the_irregular_names_are_spelled_the_runtimes_way() -> None:
    # Each of these breaks a naming rule in a different place, which is the whole argument for a
    # table. Checked against the header named in SOURCE.
    assert method_for("CONV_2D") == "AddConv2D"
    assert method_for("DEPTHWISE_CONV_2D") == "AddDepthwiseConv2D"
    assert method_for("MAX_POOL_2D") == "AddMaxPool2D"
    assert method_for("AVERAGE_POOL_2D") == "AddAveragePool2D"


def test_a_naming_rule_would_have_got_these_wrong() -> None:
    # Stated as a test so the next person to think of the shortcut sees why it fails.
    def camel(name: str) -> str:
        return "Add" + "".join(part.capitalize() for part in name.split("_"))

    wrong = [name for name in RESOLVER_METHODS if camel(name) != RESOLVER_METHODS[name]]
    assert "CONV_2D" in wrong and camel("CONV_2D") == "AddConv2d"


def test_an_unmapped_operator_returns_nothing_rather_than_a_guess() -> None:
    assert method_for("WHILE") is None
    assert method_for("ETHOSU") is None


def test_every_method_name_looks_like_one() -> None:
    for operator, method in RESOLVER_METHODS.items():
        assert method.startswith("Add"), operator
        assert method.isidentifier(), operator


def test_the_table_says_where_it_came_from() -> None:
    # A table of names with no source is a table of guesses.
    assert "micro_mutable_op_resolver.h" in SOURCE
    assert READ_ON == "2026-10-22"
    assert CUSTOM_METHOD == "AddCustom"
