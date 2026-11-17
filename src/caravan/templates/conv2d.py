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

from caravan.targets.fit import LayerRecord
from caravan.templates.plane import as_pair, walk_plane
from caravan.templates.registry import TemplateParameterSpec, TemplateStarter
from caravan.templates.sequence import length_after_conv

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


def layers(params: BaseModel, steps: int, channels: int) -> tuple[list[object], int]:
    """A window as a plane of steps by channels, through ``builders/conv2d.py``'s layers."""
    assert isinstance(params, Conv2dParameters)
    records: list[object] = []
    rows, columns, depth = steps, channels, 1
    for position, block in enumerate(params.blocks, start=1):
        kernel = as_pair(block.kernel)
        stride = as_pair(block.stride)
        assert kernel is not None and stride is not None
        out_rows = length_after_conv(
            rows, kernel=kernel[0], stride=stride[0], padding=block.padding
        )
        out_cols = length_after_conv(
            columns, kernel=kernel[1], stride=stride[1], padding=block.padding
        )
        if not out_rows or not out_cols:
            return records, rows * columns * depth
        out_rows, out_cols = int(out_rows), int(out_cols)
        if block.kind == "standard":
            records.append(
                LayerRecord(
                    kind="conv",
                    name=f"conv_{position}",
                    kernel_elements=kernel[0] * kernel[1] * depth * block.filters,
                    bias_elements=block.filters,
                    input_elements=rows * columns * depth,
                    output_elements=out_rows * out_cols * block.filters,
                )
            )
        else:
            records.append(
                LayerRecord(
                    kind="conv",
                    name=f"depthwise_{position}",
                    kernel_elements=kernel[0] * kernel[1] * depth,
                    bias_elements=depth,
                    input_elements=rows * columns * depth,
                    output_elements=out_rows * out_cols * depth,
                )
            )
            records.append(
                LayerRecord(
                    kind="conv",
                    name=f"pointwise_{position}",
                    kernel_elements=depth * block.filters,
                    bias_elements=block.filters,
                    input_elements=out_rows * out_cols * depth,
                    output_elements=out_rows * out_cols * block.filters,
                )
            )
        rows, columns, depth = out_rows, out_cols, block.filters
        pool = as_pair(block.pool)
        if pool is not None:
            pooled_rows, pooled_cols = rows // pool[0], columns // pool[1]
            records.append(
                LayerRecord(
                    kind="pooling",
                    name=f"pool_{position}",
                    input_elements=rows * columns * depth,
                    output_elements=pooled_rows * pooled_cols * depth,
                )
            )
            rows, columns = pooled_rows, pooled_cols
    if params.head == "average":
        records.append(
            LayerRecord(
                kind="pooling",
                name="pool_head",
                input_elements=rows * columns * depth,
                output_elements=depth,
            )
        )
        return records, depth
    return records, rows * columns * depth


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
    layers=layers,
    # examples/frames-conv2d.yaml's parameters (feature 013, research R7).
    starter=TemplateStarter(
        params={
            "blocks": [
                {"filters": 8, "kernel": 3, "padding": "same", "normalise": True},
                {
                    "kind": "separable",
                    "filters": 16,
                    "kernel": 3,
                    "stride": 2,
                    "padding": "same",
                    "normalise": True,
                },
            ],
        },
        window=12,
        rank=2,
        note="filters over time and columns at once: for frames of coefficients, like audio",
    ),
)
