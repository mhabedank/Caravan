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
  window: 64                               # required: this template consumes a window (CF-6)
  labels: [normal, dos, fuzzy, replay]     # the committed fixture's own labels
```

This one runs: the labels are the four the committed synthetic dataset actually carries, and the
blocks fit a 64-sample window — 64 → 30 after the first convolution, 15 after its pooling, 13 after
the second convolution, which the `average` head then reduces.

At the named model's shape the same template reads:

```yaml
    blocks:
      - {filters: 16, kernel: 5, stride: 2, normalise: true, pool: 2}
      - {filters: 32, kernel: 3, normalise: true, pool: 2}
    head: average
dataset:
  window: 128         # 2.56 s at 50 Hz; 9 channels come from the data's own width
  labels: [walking, walking_upstairs, walking_downstairs, sitting, standing, lying]
```

**That second one is not runnable in this repository**, and deliberately so: the committed fixture
has five columns and four labels, and the named model's dataset never enters here (Principle IX).
It is shown because the template exists for that shape, and the shape is checked by building rather
than by training (spec FR-013).

The channel count is never written in either: it comes from the data's own width, as it does for the
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

Shown for the manifest above with `window: 16` instead of 64, so the arithmetic can be checked
against the formulas of research R5: 16 → 6 after the first convolution (kernel 5, stride 2), 3
after its pooling, and the second block's kernel of 3 leaves exactly 1 — so a kernel of 5 there
would not fit:

```
manifest.yaml: dataset.window — the conv1d template needs more window than this manifest has
    window 16 reaches block 2 with 3 samples left, and that block's kernel spans 5
    accepted: a kernel of 3 or less in block 2, no pooling in block 1, or a window of 23 or more
```

The message names the block, the length at that point, and a fitting alternative. Three things,
because "does not fit" alone is a sentence an author cannot act on.

The third one has to be *computed*, not guessed: this document first said "a window of 26 or more",
and the smallest window that actually fits a kernel of 5 in block 2 is **23** — at 22 the first
block leaves 4 samples and at 23 it leaves 5. The implementation computes it by walking the blocks
rather than by estimating, and the test of that walk is `tests/unit/test_window_fit.py`. A
suggestion an author follows has to be right, or it is worse than no suggestion.

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
