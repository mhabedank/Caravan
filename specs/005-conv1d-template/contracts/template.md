# Contract: The conv1d Template

**Feature**: 005 · **Date**: 2026-10-22

## In a manifest

```yaml
model:
  name: picket-conv1d
  template: conv1d
  params:
    blocks:
      - {filters: 16, kernel: 5, stride: 2, normalise: true, pool: 2}
      - {filters: 32, kernel: 3, dropout: 0.1}
    head: average

dataset:
  window: 64          # required: this template consumes a window (CF-6)
  labels: [normal, fault_a, fault_b, fault_c]
```

At the named model's shape the same template reads:

```yaml
    blocks:
      - {filters: 16, kernel: 5, stride: 2, normalise: true, pool: 2}
      - {filters: 32, kernel: 3, normalise: true, pool: 2}
    head: average
dataset:
  window: 128         # 2.56 s at 50 Hz, 9 channels from the dataset's own width
```

The channel count is never written here: it comes from the data's own width, as it does for the
dense template.

## What it promises

- **One score per class**, with the class count taken from `dataset.labels`.
- **A reported shape**: the build report carries every layer with its kind, its output shape and
  its parameter count, in the form the dense template already produces.
- **The operator set the file contains**, recorded by the export stage, not asserted here.

## What it refuses, and how

**A parameter it cannot accept** — rule `T-2`, at validation, naming the path:

```
manifest.yaml: model.params.blocks.0.kernel — the conv1d template rejects this parameter:
    Input should be greater than 0
    found: 0
```

**A configuration the window cannot carry** — rule `CF-6`, at validation, with the arithmetic shown:

```
manifest.yaml: dataset.window — the conv1d template needs more window than this manifest has
    window 64 reaches block 2 with 7 samples left, and that block's kernel spans 9
    accepted: a kernel of 7 or less in block 2, a stride of 1 in block 1, or no pooling in block 1
```

The message names the block, the length at that point, and a fitting alternative. Three things,
because "does not fit" alone is a sentence an author cannot act on.

## What the author is choosing when they pick a head

Measured on one two-block architecture at 128×9 with six classes (research R3), and recorded in the
export so it is visible per model rather than remembered from a document:

| | `average` | `flatten` |
|---|---|---|
| Parameters | **2,502** | 7,878 |
| Model bytes | **7,920** | 12,896 |
| Distinct operators | 6 | **5** |
| On the reference kernel | `RESHAPE`, `MEAN` | `RESHAPE` |

`average` is the default: it is the smaller model, and a template for microcontrollers should
default to the cheaper side of a trade. `flatten` buys one fewer operator on the reference
implementation for three times the parameters.

## What it does not promise

Nothing about accuracy, and nothing about latency. A model built from this template has been
trained on nothing until somebody trains it, and this project has no dataset to train it on
(Principle IX). What such a model achieves is measured where the data is.
