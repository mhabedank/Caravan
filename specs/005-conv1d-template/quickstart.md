# Quickstart: The conv1d Template

**Feature**: 005 · **Date**: 2026-10-22

Everything here runs on the committed synthetic fixture. No dataset enters this repository, so none
leaves it either (Principle IX).

## Prerequisites

Validating a manifest needs nothing but the default installation:

```bash
pip install -e .
```

Building and training need the conversion half, and therefore Python 3.13:

```bash
pip install -e ".[train,verify]"
```

## See it listed

```bash
caravan templates
```

Expected: both templates, each with a one-line summary. The convolutional one appears without any
central list having been edited — that is what the registry is for, and this is the first real
second template that proves it.

## The happy path

```bash
M=tests/fixtures/manifests/valid/picket-conv1d-fixture.yaml
caravan validate $M
caravan build    $M
caravan train    $M
caravan quantize $M
caravan export   $M
```

Expected:

- `validate`: exit 0.
- `build`: a per-layer table naming the convolution, the pooling and the normalisation layers with
  their output shapes, and the model's parameter count.
- `train`, `quantize`: as for the dense template, with the accuracy gate judging.
- `export`: an operator set of `RESHAPE`, `CONV_2D`, `MAX_POOL_2D`, `MEAN`, `FULLY_CONNECTED`,
  `SOFTMAX` for the `average` head, and the same without `MEAN` for `flatten`. Coverage shows
  `MEAN` falling back to the reference implementation on all three boards, with its source and date.

The exact byte count is not predicted here: it is measured when the code runs, and recorded then —
the same discipline feature 004's quickstart followed.

## Check the thing most likely to surprise you

The template is called `conv1d` and the file contains a two-dimensional convolution. That is not a
mistake, and it is worth seeing once:

```bash
python - <<'PY'
import json, pathlib
from caravan.runtime.flatbuffer import inspect_graph

run = sorted(pathlib.Path("runs").iterdir())[-1]
graph = inspect_graph(run / "model" / "model.tflite")
print("operators in the file:", [(o.name, o.nodes) for o in graph.operators])
print("resolver was generated for:", (run / "model" / "resolver.h").read_text().count("resolver.Add"), "operators")
PY
```

The converter adds a dummy spatial dimension, convolves in two dimensions and reshapes back; the
runtime has no one-dimensional convolution at all. The template speaks the author's language and
the artifacts record the machine's.

## See the head's cost

```bash
# the same manifest with head: flatten, in a copy
caravan export tests/fixtures/manifests/valid/picket-conv1d-fixture.yaml
caravan export /tmp/conv1d-flatten.yaml
# then compare the two export records
```

Expected: `flatten` has one fewer distinct operator and visibly more parameters. Both numbers come
from the artifacts, which is the point — the trade is recorded per model rather than remembered
from a table in a document.

## See it refuse

**A window too short for the configuration.** Set `dataset.window: 16` in a copy of the fixture
manifest, keeping its blocks, and widen the second block's kernel to 5:

```
manifest.yaml: dataset.window — the conv1d template needs more window than this manifest has
    window 16 reaches block 2 with 3 samples left, and that block's kernel spans 5
    accepted: a kernel of 3 or less in block 2, no pooling in block 1, or a window of 23 or more
```

Exit 1, nothing built. The message names the block and the length at that point, because "does not
fit" alone cannot be acted on.

**A parameter out of range.** Set a block's `filters: 0`:

```
manifest.yaml: model.params.blocks.0.filters — the conv1d template rejects this parameter:
    Input should be greater than 0
```

Exit 1, and the path names *which* block — not a complaint about the list.

## Run the suite the way continuous integration does

```bash
pytest tests -q                                   # everything, with both extras
VIRTUAL_ENV=/tmp/no-extras pytest tests -q        # the core alone: validation still works
```

The second one is the layering rule: the parameter half validates a manifest in an installation
with no training framework, because validating is not building.
