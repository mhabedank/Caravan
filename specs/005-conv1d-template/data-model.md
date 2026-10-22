# Phase 1 Data Model: The conv1d Template

**Date**: 2026-10-22 · **Feature**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

Two halves, as every template has: the parameters in the core, the builder behind the training
extra. Nothing else in the project learns a new type.

---

## The parameters (core — `caravan/templates/conv1d.py`)

### `ConvBlock`

One stage of the architecture. A list of these rather than parallel lists of filters and kernel
widths: `hidden: [32, 16]` works for the dense template because a layer is one number, but a
convolution block is four or five, and parallel lists let a reader put the wrong kernel against the
wrong filter count without the schema noticing.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `filters` | `int > 0` | — | how many feature maps this block learns |
| `kernel` | `int > 0` | — | how many samples each filter spans |
| `stride` | `int > 0` | `1` | how far the filter steps |
| `padding` | `"valid"` \| `"same"` | `"valid"` | whether the ends of the window are padded (research R8) |
| `normalise` | `bool` | `false` | normalisation inside the block; free at inference (research R4) |
| `pool` | `int > 0` \| `null` | `null` | downsampling after the block |
| `dropout` | `0.0 ≤ float < 1.0` | `0.0` | zero means no layer appears at all |

### `Conv1dParameters`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `blocks` | `list[ConvBlock]`, at least 1 | — | the architecture, in order |
| `head` | `"average"` \| `"flatten"` | `"average"` | how the convolved sequence becomes one score per class |

`head` defaults to `average` because it is the smaller model — 2,502 parameters against 7,878 on
the measured pair (research R3) — and because a template for microcontrollers should default to the
cheaper side of a trade and let the author buy the other.

The number of classes is **not** here: it comes from `dataset.labels`, as it does for the dense
template. A template that carried its own class count could disagree with the dataset, and one of
the two would be wrong.

### What is deliberately absent

`dilation`, residual connections, more than one input, more than one head, separable convolution
(measured, cheap, and still absent — no named model needs it: Principle X, research R4).

---

## The window check (core)

### `TemplateParameterSpec`, one field wider

```text
identifier        str
parameters        type[BaseModel]
consumes_window   bool
summary           str
window_fit        Callable[[BaseModel, int], str | None] | None     ← new
```

`window_fit` is given the validated parameters and the window length, and returns `None` when the
configuration fits or a sentence naming what does not. Optional, so the dense template and every
third-party template that does not care are unaffected.

Rule **CF-6** calls it, where it already checks a window against a template. The core therefore
learns nothing about convolutions, and the template learns nothing about the manifest's layout
(research R6).

### `SequenceLength` (internal to the check)

The arithmetic of research R5, verified against the framework on 14 cases:

```text
same  : n → ceil(n / stride)
valid : n < kernel → does not fit; else n → floor((n - kernel) / stride) + 1
pool p: n < p → does not fit; else n → floor(n / p); 0 → does not fit
```

The message names the window, the block that does not fit, the length when that block was reached,
and what would fit — a smaller kernel, or a shorter stride, or one fewer pooling step. "It does not
fit" without that is a sentence an author cannot act on.

---

## The builder (extra `train` — `caravan/templates/builders/conv1d.py`)

A function from parameters, input shape and labels to a model, exactly as the dense template's
builder is. It validates what it is given through the parameter half, so the two halves cannot
drift.

Layer order inside a block, which is the one thing the builder decides:

```text
convolution → (normalisation) → activation → (pooling) → (dropout)
```

Normalisation before the activation, because that is the order it folds into the convolution in —
and the fold is the reason it is offered at all (research R4). The activation is the rectifier the
dense template uses; it needs no parameter until a named model asks for another.

---

## What this feature does not add

- **No new rule identifier.** The two refusals belong to CF-6, which exists, and to T-2, which
  already reports a rejected template parameter with its path.
- **No change to the per-layer report.** `layer_table` is generic over the framework's layers
  (research R7).
- **No change to the resolver method table or the kernel data.** Every operator is already mapped;
  `MEAN`'s absence from both libraries is already the right verdict (research R7).
- **No stage change.** Every stage reaches the template through the registry.
