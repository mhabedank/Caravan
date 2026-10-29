"""The ``conv2d`` template: a convolution over a plane — feature frames, or an image.

Feature 010. A pattern in a spectrogram has extent in time *and* in frequency, and a pattern in an
image in both of its axes; ``conv1d`` treats the columns as unrelated channels and cannot see that.
This template slides over both axes of a plane:

* a **window** of records seen as rows by input columns, one channel — keyword spotting's 49
  frames by 10 MFCC coefficients is exactly this, once extracted;
* an **image**, height by width with its channels (``takes_images``).

Justified by two documented application classes (Principle X): keyword spotting, with Speech
Commands v2 (CC BY 4.0) and the MLPerf Tiny DS-CNN reference, and the image classes — Visual Wake
Words (MobileNetV1 at width 0.25) and small image classification. Both references are built from
the two block kinds offered here: a standard convolution, and a depthwise-separable one (a
depthwise convolution with the block's kernel and stride, then a 1 x 1 convolution with its
filters). Measured on 2026-10-29 (research R1, R4): every operator either produces has an
accelerated kernel in both built-in libraries.

The ``average`` head is average pooling over the whole remaining plane, not a global mean: the
same arithmetic, but it converts to AVERAGE_POOL_2D, accelerated everywhere, where a global mean
converts to MEAN, accelerated nowhere (research R2). It is also what the MLPerf reference does.

The parameter half is here, in the core. The builder half is
``caravan/templates/builders/conv2d.py``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from caravan.templates.plane import as_pair, walk_plane
from caravan.templates.registry import TemplateParameterSpec

Positive = Annotated[int, Field(gt=0)]
#: An int for a square, or [rows, columns].
Extent = Positive | Annotated[list[Positive], Field(min_length=2, max_length=2)]

Kind = Literal["standard", "separable"]
Padding = Literal["valid", "same"]
Head = Literal["average", "flatten"]


class Conv2dBlock(BaseModel):
    """One stage: a convolution, its normalisation and activation, optional pooling and dropout."""

    model_config = ConfigDict(extra="forbid")

    kind: Kind = "standard"
    filters: Positive
    kernel: Extent
    stride: Extent = 1
    padding: Padding = "valid"
    #: After each convolution of the block, before its ReLU; folds into the convolution.
    normalise: bool = False
    #: Max pooling after the block.
    pool: Extent | None = None
    dropout: Annotated[float, Field(ge=0.0, lt=1.0)] = 0.0


class Conv2dParameters(BaseModel):
    """Parameters of the ``conv2d`` template, validated by the template itself."""

    model_config = ConfigDict(extra="forbid")

    blocks: list[Conv2dBlock] = Field(min_length=1)
    head: Head = "average"

    def as_blocks(self) -> list[dict[str, object]]:
        return [block.model_dump() for block in self.blocks]


def plane_fit(
    params: BaseModel, rows: int | None, columns: int | None
) -> tuple[str, tuple[str, ...]] | None:
    """``None`` when the plane fits the blocks, else what does not and what would.

    Either axis may be unknown — an image size or a vocabulary still to be learned from the data —
    and is then skipped here and checked by the build stage, before training.
    """
    assert isinstance(params, Conv2dParameters)
    outcome = walk_plane(rows, columns, params.as_blocks())
    if outcome.fits:
        return None
    assert outcome.failed_block is not None
    unit = "rows" if outcome.axis == "rows" else "columns"
    problem = (
        f"the conv2d template needs more of the plane than this manifest has: the {outcome.axis} "
        f"axis has {outcome.size_there} {unit} when block {outcome.failed_block} is reached, and "
        f"that block's kernel spans {outcome.kernel_there}"
    )
    alternatives = [
        f"a kernel of {outcome.size_there} or less on the {outcome.axis} axis in block "
        f"{outcome.failed_block}"
    ]
    position = outcome.failed_block
    if position > 1 and as_pair(params.blocks[position - 2].pool) is not None:
        alternatives.append(f"no pooling in block {position - 1}")
    if outcome.smallest is not None:
        alternatives.append(f"at least {outcome.smallest} {unit}")
    return problem, tuple(alternatives)


SPEC = TemplateParameterSpec(
    identifier="conv2d",
    parameters=Conv2dParameters,
    consumes_window=True,
    summary=(
        "Convolution over a plane: feature frames (rows by columns) or an image; standard and "
        "separable blocks"
    ),
    takes_images=True,
    plane_fit=plane_fit,
)
