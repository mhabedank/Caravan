# Research: Declared Inputs and Outputs, and a Lean Manifest

Phase 0 of the plan. Each decision states what was chosen, why, and what else was weighed. Where a
decision rests on behaviour of the toolchain, the behaviour was measured, and the command, the
versions and the date are given. The scripts are not committed: they ran against the project's
own environment (`.venv`, Python 3.13) and are reproduced here in enough detail to rerun.

Versions measured against, 2026-10-23: TensorFlow 2.21.0, Keras 3.15.1, ai-edge-litert 2.3.0,
tflite-micro at commit `f7ed40df396cd25a67db7896ae02cd98866021ea` (`main`).

## R1. The schema version of the new form, and the migration to it

**Decision**: the new form is `apiVersion: caravan/v0.1`. The registry knows two versions,
`caravan/v0` (oldest) and `caravan/v0.1` (newest), with one transform from the first to the second.
A manifest that declares no version is `caravan/v0`, as today. The transform returns the migrated
mapping **and a list of notices**, one per dropped or moved field; the notices reach `validate`,
`render` and the run report.

**Rationale**: Principle IX requires a registered migration per schema version and an upgrade in
memory on every load. The new form is not a superset of the old one — fields disappear and others
move — so the loader must be told which form it holds, and the only honest way to be told is the
declared version. `v0.1` stays inside the pre-stable `v0` series, which is what Principle IX allows
breaking changes in.

**Alternatives considered**:
- *Keep `caravan/v0` and recognise the old form by its shape* (a `compliance` key, say). Rejected:
  it is silent reinterpretation by guesswork, which Principle IX forbids, and it breaks the first
  time a new-form manifest happens to carry a key the old form also had.
- *`caravan/v1`*. Rejected: Principle IX reserves a stable version for the point where breaking
  changes need a new version every time. Nothing about this feature is that point.

## R2. The shape of the declarations

**Decision**: two top-level lists, `inputs` and `outputs`, as Ludwig has `input_features` and
`output_features`. Each entry carries a `name` and a `kind`. For an input of kind `series`, there
are optional `columns` and an optional `window`. For an output of kind `class`, there are `column`
(default `label`), optional `labels` and optional `accuracy_drop_max` (default `0.02`, today's
default). A name is required and must match `[a-z][a-z0-9_]{0,31}`.

**Rationale**:
- Lists make a second input or output an additive change later (FR-007).
- A required name, because the name is what a firmware author binds by (FR-030), and a default
  name hides that it is a contract.
- The pattern is the intersection of what a C identifier allows, which the header uses (R7), and
  what a TensorFlow tensor name keeps intact (R4). Hyphens are excluded, because they are not C.
- `window` moves onto the input because it describes how that input is cut. `accuracy_drop_max`
  moves onto the output because Principle V in 3.0.0 places the budget per declared output.

**Alternatives considered**:
- *Ludwig's own key names*. Rejected: `input_features` reads as feature engineering, and the same
  word is already used for the columns of the data.
- *A single `model.io` mapping*. Rejected: it nests the thing the owner said makes a manifest
  readable.

## R3. Values that come from the data

**Decision**: a new internal stage, `data`, runs before `build`. It reads the dataset, derives the
input columns and the labels, checks a pinned label list in both directions (the existing rule
DS-5), and writes `data/schema.json`. Its cache key is the dataset version plus the two declaration
lists, so a reused result reads no data. The pipeline merges the derived values into the resolved
manifest, and the run's `resolved.yaml` is written after this stage rather than before it. Every
later stage therefore sees concrete columns and labels through its projection, and its cache key
covers them.

`caravan render`, which reads no data, writes the marker `derived` in place of a derived list.

**Rationale**:
- Stages receive only their projection of the resolved manifest (feature 002, research R7). A label
  list that reached a stage any other way would bypass the mechanism that makes "the fields this
  stage reads" true by construction, and would leave the labels out of the cache key.
- Deriving inside `build` would hide the labels in an artifact that `train`, `quantize` and
  `export` would each have to read back.
- A stage of its own also keeps the existing property that a fully reused run reads no data at all.

**Alternatives considered**:
- *Derive at the start of every run*. Rejected: it reads the author's full dataset on every
  invocation, including the fully cached one that reads nothing today.
- *Write a list into the manifest on first run*. Rejected: Principle IX forbids rewriting the
  user's file.
- *An empty list in `render`*. Rejected by FR-013: an empty list reads as "no labels".

## R4. Names in the converted model

**Measured** (2026-10-23, the versions above): Keras models converted through the project's own
`caravan.convert.tflite.convert` at int8:

| Model | Signature inputs | Signature outputs | Subgraph output order |
|---|---|---|---|
| Sequential, `Input(name="frames")`, last layer `"attack"` | `frames` → 0 | `output_0` → 7 | — |
| Functional, same names | `frames` → 0 | `output_0` → 7 | — |
| Functional, output as dict `{"attack": …}` | `frames` → 0 | `attack` → 7 | — |
| Functional, two outputs as a list | `frames` → 0 | `output_0` → 8, `output_1` → 10 | **10, 8** (reversed) |

The converter keeps the input's name. It drops a Keras output layer's name unless the model returns
a dict, in which case the dict key becomes the signature name. With two outputs, it **reverses**
their order in the subgraph relative to the declared order. Only the SignatureDef still maps each
name to the right tensor. This is direct evidence for Principle VIII's sentence that the converter
does not guarantee the declared order.

**Decision**: the build stage takes the template builder's model unchanged and **rewires** it into a
functional model: an `Input` named after the declared input, the builder's layers applied in order,
and a dict output keyed by the declared output name. Builders, including third-party ones
registered by entry point, keep their signature.

**Verified**: for `mlp` (`hidden: [32, 16], dropout: 0.1`) and `conv1d` (one block, `filters: 8,
kernel: 3, normalise: true, pool: 2`), built under seed 7:
- the rewired model's weights are identical to the builder's, array for array;
- the converted operator lists are identical (mlp: RESHAPE, FULLY_CONNECTED ×3, SOFTMAX; conv1d:
  RESHAPE, CONV_2D, MAX_POOL_2D, RESHAPE, MEAN, FULLY_CONNECTED, SOFTMAX);
- the signature carries the declared names, `frames` and `attack`.

**Alternatives considered**:
- *Change every builder to accept names*. Rejected: it breaks the builder signature for third-party
  templates, and the names are a concern of the pipeline, not of a template.
- *Wrap the builder's model as one nested layer*. Rejected: the per-layer table of feature 002 and
  the per-layer error table of feature 003 would see one opaque layer.
- *Rename tensors in the flatbuffer after conversion*. Rejected: Principle VIII's portability rests
  on never rewriting a converted model, and a round-tripped flatbuffer can fail to load (feature
  004).

## R5. How a runner on the board finds an input or an output

**Checked**: `tensorflow/lite/micro/micro_interpreter.h` and `.cc` at `f7ed40d`.
`MicroInterpreter::input(size_t index)` returns `input_tensors_[index]`, where the inputs are those
of subgraph 0 by position (`inputs_size()` is `subgraphs()->Get(0)->inputs()->size()`). The same
holds for `output(i)`. Neither file reads SignatureDefs. The microcontroller runtime binds by
position in the subgraph, never by tensor index or by name.

**Decision**: the interface contract records, for each declared name, the **position** in the
subgraph's input or output list. The C header turns that into a named constant. The position is
found by reading the SignatureDef's tensor index for the name and locating that tensor in the
subgraph list; it is read from the file, never assumed from the declaration. The tensor index and
the converted tensor name are recorded as well, for readers that use the desktop runtime.

**Rationale**: a name the runner cannot look up is of no use to it. A constant per declared name
lets runner code say `interpreter.input(g_model_input_frames)`, which binds by name at compile time
and stays correct when the converter reorders (R4).

## R6. The fit check before training

**Decision**: a stage of its own, `fit`. It runs after `build`, has `build` as its upstream, and
reads `export.targets` and `export.quantization`. `train` keeps `build` as its upstream, so adding
or removing a board re-runs `fit` and `export` and never retrains (Principle III).

It computes two floors per model, both counted only over layers that are certain to remain
operators of their own after conversion:

- **Weight floor**: the sum, over Dense and Conv layers, of kernel elements × kernel bytes plus
  bias elements × bias bytes. At `int8`, kernels are 1 byte and biases 4 (int32). At `float16`,
  both are 2. At `none`, both are 4. Normalisation layers are excluded, because they fold into
  the preceding convolution and their parameters disappear: feature 005 measured that the fold adds
  no operator. Counting them could overstate the floor.
- **Working-memory floor**: the largest, over Dense, Conv and pooling layers (including global
  pooling), of input elements plus output elements, times the activation size: 1 byte at `int8`, 4
  at `float16` and `none`, whose activations stay float32. These operators need their input and
  their output live at once in any memory plan.

  Layers that may vanish, be fused or run in place — Flatten and Reshape, Dropout, normalisation,
  and stand-alone activations — are excluded. A ReLU fused into a convolution has no buffers of its
  own, and counting it could overstate the floor. That would break the one property the check
  depends on.

Each floor is compared with the board's `flash_kb` and `ram_kb` × 1024. A floor above a board's
figure fails the stage with a new rule, `F-1`, listing every board and resource that fails. A pass
writes `model/fit.json` with each figure, the label `estimated`, the method, and the sentence that
a pass is not a claim of fit.

**Rationale**: Principle V in 3.0.0 lets this check pass without deciding the budget only because it
compares lower bounds. Every rule above is about keeping them lower bounds. The working-memory floor
here may be below the floor the export computes from the converted graph, never above it. A test
asserts that ordering on both pilot templates.

FR-021, a board without a figure, cannot be reached through a board description, because the board
schema already requires `ram_kb` and `flash_kb` greater than zero. The stage still refuses rather
than skipping if a figure is absent, so the property does not depend on the schema staying as it is.

**Alternatives considered**:
- *Put the check inside `build`*. Rejected: `build` would then read `export.targets`, and adding a
  board would change the build key and with it the train key, retraining for nothing.
- *Use the parameter count × element size*. Rejected: it counts folded normalisation parameters.
- *Convert a throwaway model and read the export floor*. Rejected: conversion needs calibration
  data and takes most of the time training would. The point is to answer before spending it.

## R7. The form of the interface contract

**Decision**:
- `model/interface.json`, documented field by field in `contracts/interface.md`, with sorted keys,
  two-space indentation and a trailing newline. It is written by the export stage and listed with
  size and digest like every artifact.
- The existing `model_data.h` gains the per-name position constants and, for a class output, the
  label count and an `extern` label array. `model_data.cc` gains the array's definition.
- Labels are emitted as C string literals. Every byte outside printable ASCII, and every `"` and
  `\`, is written as `\xNN`, and a literal is split after each such escape. In C, an escape runs as
  far as there are hex digits, so a following hex character would otherwise be swallowed into it.

**Rationale**:
- JSON, because every language a firmware toolchain uses reads it, and the run report is already
  JSON.
- The header, because the label order is what a runner needs at the moment it reads an output, and
  FR-026 asks that it not need another file then.
- The escaping is deterministic, so the byte-identical rule (FR-027) holds for any label.

**Alternatives considered**:
- *YAML*, which is the manifest's format. Rejected: a firmware build has a JSON reader more often
  than a YAML one, and the report is JSON.
- *A second header*. Rejected: the spec speaks of the header, and one include is what a runner wants.

## R8. Rules that go, and rules that come

**Retired, identifiers reserved and never reused**:
- CF-3 (personal data against risk class), CF-5 (publication needs compliance), CF-8 (benchmark-only
  data published) and DS-9 (training not permitted) belong to the compliance layer.
- CF-7 (the emulator exists for every target) checks `verify.emulator`, a field of a stage that does
  not exist yet.

A test asserts that no rule table uses any of the five identifiers.

**New**:

| Rule | When | Where |
|---|---|---|
| CF-9 | a declaration name breaks the pattern, or two declarations share a name | validation |
| CF-10 | more than one input or more than one output (FR-028), or a kind not implemented (FR-008) | validation |
| CF-11 | a column is named both by the input and by the output (FR-015) | validation |
| DS-11 | the output column holds fewer than two distinct values (FR-011) | `data` stage |
| DS-12 | an input names a column the data does not have | `data` stage |
| F-1 | a floor exceeds a board (FR-018) | `fit` stage |

**Removed fields** get a message of their own, so an author learns that a field was removed and does
not hunt for a typo (FR-001). The reasons are listed in `contracts/manifest.md`.

## R9. One-time cache invalidation

Every stage's declared reads change. `dataset.labels`, `dataset.window` and
`export.accuracy_drop_max` become paths under `inputs` and `outputs`. So every cache entry written
before this feature misses once. This is correct, not a defect: the projection is the key, and the
projection changed. It is noted in the migration note so nobody reports it as a cache bug.

## R10. What the migration does to the pilot manifest

From `tests/fixtures/manifests/valid/picket-mlp.yaml`, the transform produces:
- an input named `input`, kind `series`, window 64, columns derived;
- an output named `output`, kind `class`, column `label`, labels pinned `normal, dos, fuzzy,
  replay`, `accuracy_drop_max: 0.02`.

It drops six fields with a notice each: `model.topic`, `model.task`, `compliance`, `verify`,
`bench` and `publish`. It moves three, also with a notice each: `dataset.window`, `dataset.labels`
and `export.accuracy_drop_max`.

`input` is the name the templates already give their input layer, so the converted model's input
keeps its signature name. The output's signature name changes from the converter's `output_0` to
`output` (R4). That change is visible to a desktop reader of the signature and invisible to a
microcontroller runner, which binds by position (R5).
