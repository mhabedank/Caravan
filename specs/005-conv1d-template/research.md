# Research: The conv1d Template

**Date**: 2026-10-22 · **Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Everything below was checked against a running tool, a primary source, or this project's own code
on 2026-10-22, with the command or the path recorded. Where something was *not* checked it says so.

---

## R1 — What the named model is, and what it is not

**Read from the zoo** (`mobility-model-zoo`, commit `a5c95a2`), not assumed:

| | |
|---|---|
| Input contract | 1,152 int8 values, row-major **128 samples × 9 channels** — 2.56 s at 50 Hz of the UCI-HAR inertial signals |
| Output | 6 int8 scores in label order |
| Measured quality | int8 macro-F1 **0.9229**, accuracy 0.9230, minimum class F1 0.810, over 2,947 test-subject items of benchmark `uci-har-v1` |
| Measured latency | **55.0 ms** median per inference on an ESP32-D0WDQ6-V3 rev3 at 240 MHz, 100 inferences, device timer |

*(A correction that landed during this feature's implementation and belongs on the record here too:
feature 004 claimed the batch-fixing clone was bit-identical to the trained model. It is identical
within float32 round-off, not to the bit — a runner showed one unit in the last place where the
development container showed zero. Feature 004's research R5 carries the full correction and its
cause.)*
| Runtime it was built for | the zoo's own int8 engine (`picket-forest` 0.2.0), **not** the runtime this project targets |

**Two consequences.** The template must express a 128×9 input with six classes — that is the shape
it exists for. And a version built through this pipeline is a *new version* rather than a
reproduction: the published 0.1.0's numbers were produced by a different engine, so comparing them
is work for the place that has the data, and nothing in this feature claims either figure.

**Not found in the zoo**: the architecture itself. There is no `conv1d` anywhere in that
repository — 0.1.0 was built outside it. So the block structure below is derived from the input
contract and the measured size, not copied from a definition, and that is stated rather than
implied.

---

## R2 — A one-dimensional convolution is a two-dimensional one in the file

**Decision**: describe the template to the author in one dimension; let the artifacts record what
the file contains.

**Measured** at the named model's input shape (TF 2.21.0, read back through the flatbuffer reader
feature 004 built):

```
Conv1D              → RESHAPE, CONV_2D, RESHAPE     (a dummy spatial dimension, added and removed)
MaxPooling1D        → MAX_POOL_2D
GlobalAveragePooling1D → MEAN
```

There is no one-dimensional convolution operator in the runtime's resolver at all — feature 004's
method table was read from the header and has no `AddConv1D` to offer.

**Alternative rejected**: naming the template after the operator the file ends up with
(`conv2d`, or `conv`). It would describe the machine to the author instead of the model they are
building, and the author writes a manifest about a model.

---

## R3 — The head is a parameter, because its cost goes both ways

**Measured** on one two-block architecture at 128×9 with six classes:

| Head | Bytes | Nodes | Distinct operators | Parameters | Falls back to reference |
|---|---|---|---|---|---|
| reduce over time | 7,920 | 8 | 6 | **2,502** | `RESHAPE`, **`MEAN`** |
| flatten | 12,896 | 7 | **5** | 7,878 | `RESHAPE` |

Checked against the kernel coverage data feature 004 shipped: neither `cmsis-nn` nor `esp-nn`
supplies a kernel for `MEAN`, and neither lists a reduce file among its unmapped ones. So reducing
over time costs **three times fewer parameters** and **one more operator on the reference
implementation**.

**Decision**: the author chooses, the export records what the choice cost. Neither is the right
default for every model, and this is exactly the kind of trade the export stage was built to make
visible.

### What the first real export recorded (added after implementation, T014)

The table above predicted the operator sets from probes. The first run of the committed conv1d
fixture through the real pipeline, 2026-10-22, recorded:

```
exported 6 operators in 8 nodes — 7,888 bytes
operators: RESHAPE v1, CONV_2D v3, MAX_POOL_2D v2, MEAN v2, FULLY_CONNECTED v4, SOFTMAX v2
accelerated: s32k144 4 of 6, stm32h743 4 of 6, esp32 4 of 6
  reference kernels: MEAN, RESHAPE
working memory: floor 832 bytes
```

Six operators in eight nodes, as predicted, at the fixture's smaller scale; 2,180 parameters built;
and the two fallbacks are the two the kernel data said they would be. The prediction and the
measurement agree, which is the only reason the prediction was worth writing down.

---

## R4 — Three more measurements, three parameter decisions

| Measured | Result | Decision |
|---|---|---|
| `padding="same"` | **no extra operator** — it folds into the convolution's attributes, no `PAD` node; 4,344 bytes against 4,360 for `valid` | offer it |
| `BatchNormalization` after a convolution | **no extra operator**, +648 bytes of folded weights | offer it: free at inference, and it can save a great deal of training |
| `SeparableConv1D` | adds `DEPTHWISE_CONV_2D` beside `CONV_2D`; both accelerated on **both** libraries | **do not** offer it yet — no named model needs it (Principle X). Recorded here so the next model finds the measurement |

---

## R5 — The sequence-length arithmetic, verified against the framework

**Decision**: compute the length through the blocks and refuse a configuration that cannot fit,
with the formulas below.

**Why verified rather than recalled**: a wrong formula either refuses a configuration that would
have worked, or lets one through to fail inside the framework with a shape error the author cannot
act on. Both are worse than no check. So all 14 cases were run through Keras and compared:

```
 same   padding : n → ceil(n / stride)
 valid  padding : refuse if n < kernel, else n → floor((n - kernel) / stride) + 1
 pooling p      : refuse if n < p, else n → floor(n / p); refuse if the result is 0
```

Agreement on every case, including the two the framework itself refuses (`n=4, k=5, valid` and
`n=2, k=3, valid`). Two cases worth keeping in mind: `n=3, k=5, same` gives 3 — `same` padding
never shortens below the stride — and `n=6, k=3, valid, pool=4` gives 1, which is legal and
nearly useless, so the refusal is about *impossible*, not about *unwise*.

---

## R6 — Where the refusal lives

**Decision**: the template spec gains an optional window check, and the existing cross-field rule
CF-6 calls it. The core keeps knowing nothing about convolutions; the template keeps knowing
nothing about the manifest's layout.

**Why not the alternatives**:

- *In the parameter model's own validator*: it cannot see `dataset.window`, because it validates
  `model.params` alone. The arithmetic needs both halves.
- *At build time, as a run rule*: then a manifest that can never work would pass `caravan
  validate`, and the whole point of that verb is to answer "is this sound?" before anything runs.
- *In the core, by special-casing the identifier*: forbidden by this feature's own FR-023, and it
  would make the registry's claim — a template is two files and a registration — false.

CF-6 today checks only that a window is present when the template consumes one, and absent when it
does not (`src/caravan/manifest/schema/__init__.py`). It is the natural home: same rule, same field
path, one more thing it asks the template.

---

## R7 — What needs no work at all

Checked by reading the code rather than assumed:

- **The build report's per-layer table** (`stages/_framework.py:layer_table`) is generic over the
  framework's layers: name, `type(layer).__name__`, output shape, parameter count. It will describe
  convolution, pooling and normalisation layers without a line of change. FR-018 is already met.
- **The resolver method table** (`export/methods.py`) already maps `CONV_2D`,
  `DEPTHWISE_CONV_2D`, `MAX_POOL_2D`, `MEAN`, `RESHAPE`, `FULLY_CONNECTED` and `SOFTMAX` — every
  operator this template can produce, in the runtime's own spelling. Feature 004 mapped them
  against exactly this template's needs. FR-022 turns that into a test so it cannot quietly stop
  being true.
- **The kernel coverage data** needs no entry added: `MEAN` is absent from both libraries, and
  "absent" is already the correct verdict by construction — a missing accelerated kernel *is* a
  fallback.
- **Every stage** reads the template through the registry, so none needs a change. FR-023 is a test
  that no branch on an identifier exists, not a task.

---

## R8 — Naming, against the constitution's identifier rule

The constitution forbids identifiers that are vendor product names, because a rename would become
a schema migration. `valid` and `same` are not product names: they are the two padding modes every
convolution implementation uses, in frameworks and in the literature alike. Inventing names for
them would make the schema harder to read and would not protect against anything.

The head's values are named for what they do — `average` and `flatten` — rather than for the layer
types a framework happens to call them, which keeps the schema readable if the builder's framework
is ever replaced.

---

## What remains unverified

- **What a Caravan-built version of the named model achieves.** It needs the real dataset, which
  never enters this repository. The acceptance test here runs on the committed synthetic fixture,
  and the named model's shape is checked by building — input shape, output shape, parameter count —
  not by training.
- **Whether the architecture this template expresses can reach the published 0.1.0's macro-F1.**
  Same reason. The template's job is to express the shape; whether a particular configuration
  learns well is measured where the data is.
- **The separable-convolution path beyond its operator set.** Measured for operators only; nothing
  is claimed about its accuracy or its speed.
