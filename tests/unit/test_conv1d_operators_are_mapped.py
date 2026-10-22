"""Every operator this template can produce already has a resolver method.

FR-022, and the reason it is a test rather than a note: feature 004 built the method table against
exactly these irregular spellings — `AddConv2D`, not `AddConv2d` — because this template was the
next one planned. That foresight is worth nothing if it quietly stops being true, and the way it
would stop being true is somebody adding a parameter here that produces an operator nobody mapped.

No framework needed: this reads two tables against each other.
"""

from __future__ import annotations

from caravan.export.methods import RESOLVER_METHODS, method_for

#: What a converted conv1d contains, measured 2026-10-22 at the named model's shape and again on
#: the committed fixture, read back from the flatbuffer both times (feature 005, research R2/R3).
#: `MEAN` appears for the reducing head and not for the flattening one; everything else is common.
PRODUCED = ("RESHAPE", "CONV_2D", "MAX_POOL_2D", "MEAN", "FULLY_CONNECTED", "SOFTMAX")

#: Measured but not offered: separable convolution adds this beside CONV_2D. Mapped already, so
#: the day a named model asks for it, the resolver is not the thing that blocks it.
PRODUCED_IF_SEPARABLE_ARRIVES = ("DEPTHWISE_CONV_2D",)


def test_every_operator_this_template_produces_is_mapped() -> None:
    missing = [name for name in PRODUCED if method_for(name) is None]
    assert not missing, f"no resolver method for {missing}; the export would refuse with X-4"


def test_the_operator_a_future_parameter_would_add_is_mapped_too() -> None:
    missing = [name for name in PRODUCED_IF_SEPARABLE_ARRIVES if method_for(name) is None]
    assert not missing, f"no resolver method for {missing}"


def test_the_spellings_are_the_runtimes_own() -> None:
    # The four where a naming rule would have gone wrong, and the reason the table exists.
    assert method_for("CONV_2D") == "AddConv2D"
    assert method_for("MAX_POOL_2D") == "AddMaxPool2D"
    assert method_for("DEPTHWISE_CONV_2D") == "AddDepthwiseConv2D"
    assert method_for("MEAN") == "AddMean"


def test_no_one_dimensional_convolution_is_offered_anywhere() -> None:
    # There is none in the runtime's header, and a template called conv1d is exactly where somebody
    # would reach for one. Asserted so that reaching for it fails here rather than at a compiler.
    assert method_for("CONV_1D") is None
    assert not any("Conv1D" in method for method in RESOLVER_METHODS.values())
