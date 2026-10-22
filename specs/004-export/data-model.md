# Phase 1 Data Model: Export

**Date**: 2026-10-22 · **Feature**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

Every type says which half of the installation it belongs to, because that is the layering rule of
Principle XII and it is easier to keep than to restore. Reading the model file needs the `verify`
extra; turning what was read into text needs nothing at all, so the emitters live in the core.

---

## The graph, as the file describes it

### `OperatorRecord` (extra `verify` — `caravan/runtime/flatbuffer.py`)

One distinct operator of the graph. Read from the model file, never from a runtime that loaded it
(FR-009, research R1).

| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | the operator's name as the schema spells it, e.g. `FULLY_CONNECTED` |
| `builtin_code` | `int` | the schema's numeric code, e.g. `9` |
| `version` | `int` | the operator version the file asks for, e.g. `4` |
| `nodes` | `int` | how many nodes of the graph use it, at least 1 |
| `custom_name` | `str \| None` | the custom operator's name, or `None` for a built-in one |

`custom_name` is not cosmetic: a custom operator is resolvable but needs a kernel the author
registers, and the export has to say so rather than emit a resolver that implies otherwise
(FR-012).

### `GraphInspection` (extra `verify`)

What one reading of the model file established.

| Field | Type | Meaning |
|---|---|---|
| `operators` | `tuple[OperatorRecord, ...]` | distinct operators, ordered by first appearance |
| `nodes` | `int` | nodes in the graph — the cost; `len(operators)` is the resolver's length |
| `subgraphs` | `int` | subgraphs in the file; more than one refuses the run (X-3) |
| `input_shape` | `tuple[int, ...]` | the input tensor's shape, with the batch first |
| `output_shape` | `tuple[int, ...]` | the output tensor's shape |
| `working_memory_floor` | `int` | peak simultaneously live read-write tensor bytes (research R2) |
| `read_write_total` | `int` | the sum of those tensors, an upper bound on the tensor area |
| `model_bytes` | `int` | the file's size |

Both memory figures are carried, because they bound different things in different directions and a
report that showed one without the other would invite the reader to treat it as *the* number.

### `TensorLifetime` (extra `verify`, internal to the floor computation)

| Field | Type | Meaning |
|---|---|---|
| `index` | `int` | the tensor's index in the subgraph |
| `bytes` | `int` | its size: the product of its shape times the width of its type |
| `first_node` | `int` | the first node that reads or writes it; `-1` for a graph input |
| `last_node` | `int` | the last; the node count for a graph output |

The floor is `max` over nodes of the summed `bytes` of the tensors live at that node. Not the sum
of all of them — buffer reuse makes that an upper bound, which is the correction recorded in
research R2.

---

## Accelerated kernel coverage

### `KernelLibrary` (core — `caravan/targets/kernels.py`, loaded from data)

One accelerated library, as a data file under `caravan/targets/kernels/`. Boards are data
(Principle VII); the libraries they name are too.

| Field | Type | Meaning |
|---|---|---|
| `library` | `str` | the identifier a board's `accel` field uses, e.g. `cmsis-nn` |
| `runtime` | `str` | the runtime the kernels plug into, e.g. `tflm` |
| `operators` | `mapping[str, str]` | operator name → the source file the claim came from |
| `source` | `str` | where the list was read, exactly enough for someone to re-read it |
| `read_on` | `date` | the day it was read |
| `unmapped` | `tuple[str, ...]` | source files whose operators are not mapped yet |

`unmapped` is how the file stays honest while it is incomplete: a source file that covers operators
no implemented template can produce is recorded as unmapped rather than guessed at, and mapped when
a template needs it.

### `CoverageVerdict` (core)

One operator against one target.

| Field | Type | Meaning |
|---|---|---|
| `target` | `str` | the board identifier |
| `operator` | `str` | the operator's name |
| `library` | `str \| None` | the accelerated library the board declares, or `None` |
| `accelerated` | `bool` | whether that library supplies a kernel for this operator |
| `evidence` | `str` | the source file, or the reason there is none |
| `source` | `str` | the library data file's source statement |
| `read_on` | `date` | its date |

`accelerated=False` with `library=None` is a stated verdict — nothing is accelerated on a board
that declares no library (FR-022) — and is recorded differently from a board whose library has no
data file, which refuses the run (X-5).

---

## What is written

### `Artifact` (core — `caravan/export/artifacts.py`)

| Field | Type | Meaning |
|---|---|---|
| `path` | `str` | relative to the run directory |
| `bytes` | `int` | its size |
| `digest` | `str` | `sha256:…` over its exact bytes |
| `format` | `str` | the manifest's format name, or `resolver` / `skeleton` |
| `target` | `str \| None` | the board it is specific to, or `None` when it is not |

### `ExportSet` (core)

| Field | Type | Meaning |
|---|---|---|
| `artifacts` | `tuple[Artifact, ...]` | everything written, in the order written |
| `formats` | `tuple[str, ...]` | the formats the manifest asked for and this stage honoured |
| `graph` | `GraphInspection` | what the model file said |
| `coverage` | `tuple[CoverageVerdict, ...]` | one entry per (target, operator) |
| `requirements` | `RunnerRequirements` | what the author must still supply |

### `RunnerRequirements` (core)

The answer to "what do I need to run this?", with the provenance of each part, because a figure
without its provenance is the thing Principle IV forbids.

| Field | Type | Meaning |
|---|---|---|
| `runtime` | `str` | from the board description's `toolchain.runtime` |
| `operators` | `tuple[str, ...]` | the resolver's contents, from the model file |
| `working_memory_floor` | `int` | the computed floor, in bytes |
| `floor_method` | `str` | `"peak simultaneously live read-write tensors, from the model file"` |
| `floor_is_not_the_requirement` | `str` | the sentence stating what the floor omits and which stage measures the real figure |

The last field is a string and not a boolean on purpose: what has to reach the reader is the
sentence, not a flag they have to look up.

---

## The stage

### `StageSpec` declaration (core — `caravan/stages/export.py`)

```text
name          export
upstream      quantize
reads         export.formats, export.targets, export.quantization
reads_dataset False
artifacts     model/model.tflite, model/model_data.cc, model/model_data.h,
              model/resolver.h, runner/<target>/main.cc, export.json
```

`reads_dataset` is false: this stage reads a model file and board descriptions, and the dataset
reaches it only through the upstream result's key. Declaring otherwise would make every stage
downstream of a dataset edit re-export for nothing — and the generic projection test of feature 002
checks the declaration against what the code actually touches, so an over-broad `reads` is caught
rather than merely regretted.

The board descriptions are part of the cache key through the targets the manifest names: a board
whose `accel` field changed must produce new coverage. They enter the key as the resolved board
data, the same way the dataset's digest enters the training key.

---

## Rule identifiers introduced here

The `X` prefix is free; `E` already belongs to the board emulator rules.

| Rule | Refuses |
|---|---|
| `X-1` | the manifest names an export format this version does not implement (`onnx`) |
| `X-2` | the run has no quantized model to export — the gate failed, or the stage never ran |
| `X-3` | the model file has more than one subgraph |
| `X-4` | an operator of the graph has no resolver method in the runtime, so no resolver can be generated that compiles |
| `X-5` | a target board names an accelerated library for which there is no sourced coverage data |

All five refuse a *run*, like the `DS` and `Q` rules, so none of them has an invalid-manifest
fixture and all five are covered by their own coverage test instead.
