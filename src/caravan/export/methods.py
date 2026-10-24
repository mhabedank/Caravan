"""Which resolver method registers which operator.

A table rather than a naming rule, because a naming rule produces code that does not compile. The
runtime's public methods are not a mechanical transform of the operator names: ``CONV_2D`` is
``AddConv2D`` and not ``AddConv2d``, ``SVDF`` is ``AddSvdf``, ``L2_POOL_2D`` is ``AddL2Pool2D``.
And there is no escape hatch — the generic ``AddBuiltin`` is private, so an operator with no public
method of its own cannot be registered at all, which is why that case refuses the run (X-4) rather
than emitting something the author's compiler rejects.

Only operators an implemented template can actually produce are mapped (Principle X). The table
grows with the templates, and the test that guards it asks the templates what they emit rather
than asking this file what it knows.
"""

from __future__ import annotations

#: Where the method names were read, and when. A reader checking one entry needs no more than this.
SOURCE = "tensorflow/lite/micro/micro_mutable_op_resolver.h in tensorflow/tflite-micro"
READ_ON = "2026-10-22"

#: The method that registers a custom operator. It takes the operator's name and a registration the
#: author supplies, which is why a custom operator is recorded as the author's job.
CUSTOM_METHOD = "AddCustom"

#: Operator name as the schema spells it -> the public method that registers it.
RESOLVER_METHODS: dict[str, str] = {
    # What the mlp template produces today.
    "FULLY_CONNECTED": "AddFullyConnected",
    "RESHAPE": "AddReshape",
    "SOFTMAX": "AddSoftmax",
    # What the conv1d template will produce. Mapped now because these are the four names where a
    # naming rule goes wrong, and leaving them out would invite someone to write that rule.
    "CONV_2D": "AddConv2D",
    "DEPTHWISE_CONV_2D": "AddDepthwiseConv2D",
    "AVERAGE_POOL_2D": "AddAveragePool2D",
    "MAX_POOL_2D": "AddMaxPool2D",
    # Reached by a dynamic reshape prologue, which a fixed input batch removes (feature 004,
    # research R5). Mapped so that a model which somehow keeps one still exports rather than
    # refusing for a reason the author cannot act on.
    "SHAPE": "AddShape",
    "STRIDED_SLICE": "AddStridedSlice",
    "PACK": "AddPack",
    # Common int8 neighbours of the above, each checked against the header.
    "ADD": "AddAdd",
    "MUL": "AddMul",
    "MEAN": "AddMean",
    "QUANTIZE": "AddQuantize",
    "DEQUANTIZE": "AddDequantize",
    "RELU": "AddRelu",
    "LOGISTIC": "AddLogistic",
    "TANH": "AddTanh",
    "CONCATENATION": "AddConcatenation",
    "TRANSPOSE": "AddTranspose",
    "PAD": "AddPad",
    # What the preprocessing of feature 008 produces: a number's SUB, a category's EQUAL, CAST and
    # SUM, a number output's clip. Read in the same header at f7ed40d on 2026-10-24.
    "SUB": "AddSub",
    "EQUAL": "AddEqual",
    "CAST": "AddCast",
    "SUM": "AddSum",
    "MAXIMUM": "AddMaximum",
    "MINIMUM": "AddMinimum",
}


def method_for(operator: str) -> str | None:
    """The method that registers ``operator``, or ``None`` when there is none to give."""
    return RESOLVER_METHODS.get(operator)
