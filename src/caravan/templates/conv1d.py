"""The ``conv1d`` template: a convolutional decider over a window of samples.

The second template, and the first added since the registry was built to make adding one cheap: two
files and a registration, with no central list edited. It exists because a named model needs it —
``pace-cnn``, which takes 128 samples across 9 channels and gives six classes (Principle X).

**Why it is called conv1d when the file contains a two-dimensional convolution.** Measured on
2026-10-22 and read back from the produced flatbuffer: a one-dimensional convolution is converted
to a two-dimensional one with a dummy spatial dimension added and removed by reshapes, and the
runtime's resolver has no one-dimensional convolution at all. The author is describing a model, so
the template speaks their language; what the file contains is recorded by the export stage, which
reads the file. Naming this ``conv2d`` would describe the machine to somebody writing about a model.

The parameter half is here, in the core, and imports no framework. The builder half is
``caravan/templates/builders/conv1d.py`` and is loaded by name when a stage needs it.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from caravan.templates.registry import TemplateParameterSpec
from caravan.templates.sequence import smallest_window, walk

#: What a head does to the convolved sequence. Named for the operation rather than for the layer
#: type a framework calls it, so the schema survives a change of builder.
Head = Literal["average", "flatten"]

#: The two padding modes every convolution implementation has. Not vendor product names — those are
#: what the constitution's identifier rule forbids — so they keep the names everyone knows.
Padding = Literal["valid", "same"]


class ConvBlock(BaseModel):
    """One stage of the architecture.

    A list of these rather than parallel lists of filters and kernels: ``hidden: [32, 16]`` works
    for the dense template because a layer there is one number, but a block is five, and parallel
    lists let a reader pair the wrong kernel with the wrong filter count without the schema
    noticing.
    """

    model_config = ConfigDict(extra="forbid")

    filters: Annotated[int, Field(gt=0)]
    kernel: Annotated[int, Field(gt=0)]
    stride: Annotated[int, Field(gt=0)] = 1
    padding: Padding = "valid"
    #: Folds entirely into the preceding convolution: measured 2026-10-22, no additional operator
    #: and 648 bytes of folded weights. Free at inference, which is why it is offered.
    normalise: bool = False
    pool: Annotated[int, Field(gt=0)] | None = None
    dropout: Annotated[float, Field(ge=0.0, lt=1.0)] = 0.0


class Conv1dParameters(BaseModel):
    """Parameters of the ``conv1d`` template, validated by the template itself."""

    model_config = ConfigDict(extra="forbid")

    blocks: list[ConvBlock] = Field(min_length=1)
    #: ``average`` by default because it is the smaller model — 2,502 parameters against 7,878 on
    #: the measured pair — and a template for microcontrollers should default to the cheaper side
    #: of a trade and let the author buy the other. What the choice costs is recorded per model by
    #: the export stage: ``average`` introduces an operator for which neither built-in accelerated
    #: kernel library has an implementation, so it falls back to the reference one.
    head: Head = "average"

    def as_blocks(self) -> list[dict[str, object]]:
        """The blocks as plain mappings, for the arithmetic that does not import this module."""
        return [block.model_dump() for block in self.blocks]


def window_fit(params: BaseModel, window: int) -> tuple[str, tuple[str, ...]] | None:
    """``None`` when the configuration fits, or what went wrong and what would work instead.

    Two parts, because the project prints findings in two parts: a sentence, then an indented line
    of what is accepted. "It does not fit" is something an author cannot act on, so the sentence
    names the block and the length when that block was reached, and the alternatives name a window
    that would work — computed by walking the blocks, because an earlier draft of this feature's
    documents *estimated* that number and was wrong by three.
    """
    assert isinstance(params, Conv1dParameters)
    blocks = params.as_blocks()
    outcome = walk(window, blocks)
    if outcome.fits:
        return None

    position = outcome.failed_block
    block = params.blocks[position - 1] if position else None
    assert block is not None
    needed = smallest_window(blocks)
    alternatives = [f"a kernel of {outcome.length_there} or less in block {position}"]
    if position > 1 and params.blocks[position - 2].pool:
        alternatives.append(f"no pooling in block {position - 1}")
    if needed is not None:
        alternatives.append(f"a window of {needed} or more")
    problem = (
        f"the conv1d template needs more window than this manifest has: window {window} reaches "
        f"block {position} with {outcome.length_there} samples left, and that block's kernel "
        f"spans {block.kernel}"
    )
    return problem, tuple(alternatives)


SPEC = TemplateParameterSpec(
    identifier="conv1d",
    parameters=Conv1dParameters,
    consumes_window=True,
    summary="Convolutional decider over a window of samples; blocks of filters and a pooling head",
    window_fit=window_fit,
)
