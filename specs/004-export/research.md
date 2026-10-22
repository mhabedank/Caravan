# Research: Export

**Date**: 2026-10-22 · **Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Everything below was checked against a running tool or a primary source on 2026-10-22, with the
command or the URL recorded. Where a claim could not be checked it says so and names what it would
take.

---

## R1 — Where the operator set comes from

**Decision**: read it from the model file, through `ai_edge_litert.schema_py_generated`, the
flatbuffer schema binding that ships inside the runtime extra.

**Why, and what was checked.** The obvious route is the interpreter, which has
`_get_ops_details()`. It lies about the model, in the direction that breaks firmware. Run against
the pilot fixture's quantized model with `ai-edge-litert` 2.3.0:

```
op 0 SHAPE      op 3 RESHAPE          op 6 FULLY_CONNECTED
op 1 STRIDED_SLICE  op 4 FULLY_CONNECTED  op 7 SOFTMAX
op 2 PACK       op 5 FULLY_CONNECTED  op 8 DELEGATE      ← inserted by the desktop runtime
```

Node 8 is a delegate the desktop interpreter created for itself while allocating tensors. There is
no such operator on a microcontroller. A resolver generated from that list would name a kernel the
target's runtime has never heard of, and the error would appear at link or init time on hardware,
far from here.

The same model read as a flatbuffer reports six operator codes and eight nodes, with builtin codes
and versions and no delegate:

```
(77 SHAPE v1) (45 STRIDED_SLICE v1) (83 PACK v1) (22 RESHAPE v1) (9 FULLY_CONNECTED v4) (25 SOFTMAX v2)
```

**Alternatives rejected**:

- *The interpreter's node list* — wrong, as above.
- *Vendoring our own schema binding* — a dependency and a pin for a module already installed. The
  constitution's footprint-analysis note calls for "a pinned schema binding"; the binding inside
  the runtime extra is pinned by the extra's own version floor.
- *Parsing the flatbuffer by hand* — a schema reimplementation, which is the kind of code
  Principle I says to not own when a dependency already carries it correctly.

**Consequence for the layering rule**: the whole proving half needs the runtime extra and no
training framework, which is what feature 003 bought the second extra for.

---

## R2 — The working memory, and what may honestly be said about it

**Decision**: record the **peak of simultaneously live read-write tensors**, computed from the model
file by lifetime analysis, labelled as a floor on the working memory and never as the figure the
model requires. Record separately that the runtime adds scratch buffers and bookkeeping on top, and
that the working figure is established by measurement in a later stage.

**Why.** Principle VIII requires the export to document "the tensor arena size it requires". No
desktop tool can supply that number:

- The runtime plans that memory with its own allocator, on the target, from the operators it has
  actually linked.
- The analysis tool that ships with the runtime extra (`ModelAnalyzer`) reports the model size and
  the split between data and non-data buffers, and no arena figure at all. Checked on the pilot
  model: `Model size: 15664 bytes / Non-data buffer size: 4516 bytes (28.83 %) / Total data buffer
  size: 11148 bytes (71.17 %)`.

**A correction made while researching this.** The first idea was to sum the read-write tensors and
call it a floor. It is not a floor. The runtime reuses one buffer for tensors whose lifetimes do not
overlap, so the sum is an *upper* bound on the tensor area, and it is not a bound on the arena in
either direction, because scratch buffers are not in it. The figure that *is* a floor is the peak of
simultaneously live tensors: every planner, however good, must hold at once everything that is live
at once. Both computed on the pilot model:

| Figure | Pilot model | What it bounds |
|---|---|---|
| Sum of all read-write tensors | 720 bytes | an upper bound on the tensor area |
| Peak simultaneously live | 648 bytes (at node 3) | a **lower** bound on the whole arena |

So the export states 648, calls it a floor, names the method, and says what is missing from it. A
number that is wrong by an unknown amount in an unknown direction is worse than no number, which is
the whole of Principle IV.

**Alternatives rejected**:

- *State the sum and call it the arena size* — the error this section exists to avoid.
- *State nothing* — Principle VIII asks for a figure, and an author needs somewhere to start.
- *Link the runtime and ask its allocator* — that is cross-compiling and running, which is
  emulated verification's job and is out of scope here.

**Governance consequence**: Principle VIII's wording asks this stage for a figure it cannot
honestly produce. The principle needs one sentence saying which stage supplies the required figure
and that the export supplies a computed floor. That is a constitution amendment, and it is a task of
this feature rather than a silent reinterpretation.

---

## R3 — The form of the C array

**Decision**: emit what the runtime's own generator emits, and say so. Source:
`tensorflow/lite/micro/tools/generate_cc_arrays.py` in `tensorflow/tflite-micro`, read 2026-10-22.

The generator produces, for a `.tflite` input:

- a source file that starts `#include <cstdint>`, includes its own header, and defines
  `alignas(16) const unsigned char g_<stem>_model_data[] = { 0x1c, ... };`
- a header with `#include <cstdint>`, `constexpr unsigned int g_<stem>_model_data_size = <N>;` and
  `extern const unsigned char g_<stem>_model_data[];`

**`alignas(16)` is not decoration.** The runtime requires the model buffer aligned, and an
unaligned buffer fails at initialisation on the target rather than at compile time here.

**The one real decision**: `alignas` and `constexpr` make these files C++, not C89. The constitution
says "a plain C array with its header". The array *is* plain — bytes of `unsigned char`, no
framework type anywhere — and the file is compiled by the same C++ toolchain as the runtime that
consumes it, which is how every example in the runtime's own tree does it. Emitting C that compiles
under a C compiler as well would mean either `<stdalign.h>` or a compiler-specific attribute, for a
runtime whose API is C++ regardless. Recorded so that a future board with a C-only runtime reopens
it rather than rediscovers it.

**Determinism**: the generated files contain no timestamp, no path and no host name — only the
bytes, the name derived from the artifact, and the length. The same model therefore exports to
identical bytes, which FR-005 requires and a test asserts by exporting twice.

---

## R4 — The form of the resolver, and why a naming rule will not do

**Decision**: generate a resolver using the runtime's public per-operator methods, from an explicit
table mapping builtin operator to method name. Refuse, by rule, any operator with no such method.

**Why not a naming rule.** The tempting implementation is `Add` + camel-case of the operator name.
It produces code that does not compile. From
`tensorflow/lite/micro/micro_mutable_op_resolver.h` (read 2026-10-22), the public methods include
`AddConv2D` (not `AddConv2d`), `AddMaxPool2D`, `AddAveragePool2D`, `AddL2Pool2D`, `AddSvdf`,
`AddPCAN`, `AddEthosU`, `AddUnidirectionalSequenceLSTM`, `AddBatchMatMul`. The class is
`template <unsigned int tOpCount> class MicroMutableOpResolver`, so the generated code must also
carry the operator count as a template argument, and the generic `AddBuiltin` is **private** —
there is no escape hatch for an operator without a public method.

The three operators the pilot model needs after R5 are regular: `AddReshape`,
`AddFullyConnected`, `AddSoftmax`. The trap is one template away: `conv1d` is the next feature.

**Consequence**: the mapping is data with a source and a date, the same way board descriptions are
data. An operator outside it refuses the run (rule X-4) instead of generating code that fails at the
author's compiler.

**Custom operators** have a public method, `AddCustom`, which takes a name and a registration the
author supplies. So a custom operator is recorded and resolvable, but the author must register the
kernel — which is what FR-012 says the export must state rather than pretend otherwise.

---

## R5 — Fixing the input batch, and where it belongs

**Decision**: clone the trained model onto a batch of one immediately before conversion, inside the
conversion seam, so that one conversion serves both the measurement and the export.

**What was checked.** The converted mlp carries four operators of shape plumbing — `SHAPE`,
`STRIDED_SLICE`, `PACK`, `RESHAPE` — whose only job is to compute the flatten shape from the batch
dimension. On a board the batch is one, always. Cloning with
`keras.models.clone_model(model, input_tensors=keras.layers.Input(batch_shape=(1, *shape[1:])))`
followed by `set_weights` gives:

| | Bytes | Nodes | Distinct operators |
|---|---|---|---|
| As trained (dynamic batch) | 8,656 | 7 | 6 |
| Cloned onto batch 1 | 7,856 | 4 | **3** |

and the clone computes the same function: float predictions compared element by element against the
trained model's agree **within float32 round-off**, checked on an `mlp` and on a `conv1d` model so
this is not a one-architecture trick.

**Corrected 2026-10-22, by continuous integration, while feature 005 was being implemented.** This
section first said "identical, maximum absolute difference 0.0", because that is what the
development container produced. A runner produced 1.1920928955078125e-07 for the dense model and
2.9802322387695312e-08 for the convolutional one — the first is exactly 2**-23, one unit in the last
place of a float32. Comparing five samples in one call against five calls of one sample compares
two orders of accumulation, and a machine with other vector instructions may choose a different
kernel for each shape. Feature 002 had already written this down about training — "no claim of
bit-identical weights: thread counts, kernel implementations and hardware make that untrue" — and
this section claimed it anyway for the clone; the two were not connected until a runner connected
them. What the pipeline depends on, and what is now asserted, is that the *decisions* are identical
and the scores agree to within round-off.

**Alternatives rejected**:

- *Fix the batch in the template's input layer* — training would then run one window at a time,
  changing both its speed and its dynamics. The batch belongs to deployment, not to the model.
- *Convert a concrete function with a fixed signature*
  (`from_concrete_functions` over `tf.function(...).get_concrete_function(TensorSpec([1, ...]))`) —
  does not work. The graph keeps variable-reading nodes and calibration dies with
  `RuntimeError: ... read_variable.cc:67 variable != nullptr was not true. Node number 4
  (READ_VARIABLE) failed to invoke.` (TF 2.21.0). Recorded because it is the obvious second idea.
- *Convert twice, once for measuring and once for exporting* — two models, two accuracies, and the
  one that ships is the one nobody gated. This is the reason the decision lands in feature 003's
  conversion rather than in a post-processing step here.

**Consequence**: feature 003's recorded numbers change — fewer operators, a smaller model. That is
the correction working as intended, and the quantize stage's report says what it measured, so the
change is visible rather than silent.

---

## R6 — Accelerated kernel coverage, per library

**Decision**: a data file per accelerated library, listing the operators for which that library
supplies a kernel, with the source and the date. Coverage of an operator is then a lookup, and an
operator absent from the list is recorded as falling back to the reference implementation — which is
correct by construction, because a missing accelerated kernel *is* a fallback.

**Sources, read 2026-10-22.** The authoritative statement is the runtime's own kernel directory for
each library: a kernel file exists exactly where an accelerated implementation exists.

- `cmsis-nn`: `tensorflow/lite/micro/kernels/cmsis_nn/` in `tensorflow/tflite-micro` — 14 source
  files: `add`, `batch_matmul`, `conv`, `depthwise_conv`, `fully_connected`, `maximum_minimum`,
  `mul`, `pad`, `pooling`, `softmax`, `svdf`, `transpose`, `transpose_conv`,
  `unidirectional_sequence_lstm`.
- `esp-nn`: `tensorflow/lite/micro/kernels/esp_nn/` in `espressif/esp-tflite-micro` — 7 source
  files: `add`, `conv`, `depthwise_conv`, `fully_connected`, `mul`, `pooling`, `softmax`.

**A file is not an operator.** `pooling.cc` was opened to check: it defines
`Register_AVERAGE_POOL_2D_INT8`, `Register_AVERAGE_POOL_2D_INT16`, `Register_AVERAGE_POOL_2D`,
`Register_MAX_POOL_2D_INT8`, `Register_MAX_POOL_2D_INT16` and `Register_MAX_POOL_2D` — one file,
two operators. So the data file maps operators, not file names, and each entry names the file it
came from. The ambiguous names are mapped when a template can actually produce the operator
(Principle X), and the data file records which entries have been checked against the source and
which are still unmapped.

**What this gives for the pilot model, on all three built-in boards**:

| Operator | `cmsis-nn` (s32k144, stm32h743) | `esp-nn` (esp32) |
|---|---|---|
| `FULLY_CONNECTED` | accelerated (`fully_connected.cc`) | accelerated (`fully_connected.cc`) |
| `SOFTMAX` | accelerated (`softmax.cc`) | accelerated (`softmax.cc`) |
| `RESHAPE` | reference fallback (no kernel file) | reference fallback (no kernel file) |

A non-trivial answer on the first model, which is the argument for recording it at all.

**What coverage does not say.** Whether an accelerated kernel is *selected* for a given node can
depend on operand shapes and on build flags. This stage records that the library supplies a kernel
for the operator, which is the weaker and checkable claim, and says so (FR-023). The stronger claim
needs the toolchain and belongs to a later stage.

**A board naming a library with no data file** refuses the run (rule X-5) rather than recording an
absent verdict, because "we do not know" printed next to an operator is the kind of silence
Principle IV exists against. A board declaring no library at all is a different thing and a stated
verdict: nothing is accelerated there.

---

## R7 — The runner skeleton, and the limit of this feature

**Decision**: emit the skeleton, state what it needs, and claim nothing about building it.

Nothing in this feature can compile the skeleton: no ARM or Xtensa toolchain is installed, the
runtime is not vendored, and both would be a dependency this project has no budget for. Asserting a
successful build without having done one is precisely the unverified claim Principle IV forbids. The
skeleton therefore carries the runtime the board declares, the generated resolver and C array, the
working-memory floor as a named constant with its label, and a comment naming what the author
supplies. Compiling and running it is emulated verification, a later stage.

---

## R8 — Unimplemented formats

**Decision**: `onnx` stays in the schema and is refused by the stage, by name, under its own rule
(X-1), with no artifact of any format written.

The schema already accepts `flatbuffer`, `c_array` and `onnx`, and the roadmap still intends the
third. Removing it would be a breaking schema change for a format that is coming; accepting it
silently would export two formats while the manifest asked for three. The same pattern as the
unimplemented quantization settings of feature 003: a named refusal that says which part of the
manifest the tool does not yet honour.

---

## What remains unverified, and what it would take

- **That the emitted skeleton compiles and runs.** Needs a cross toolchain and the vendored
  runtime; belongs to emulated verification. Nothing in this feature claims it.
- **That the accelerated kernel is selected for a given node.** Needs the build. The stage records
  the weaker claim and labels it.
- **The working memory a board actually needs.** Needs the runtime's allocator on the target or in
  emulation. The stage records a floor, computed by a named method, and says what is missing from
  it.
- **The coverage entries for operators no implemented template can produce.** Left unmapped in the
  data file, recorded as unmapped, and mapped when a template needs them.
