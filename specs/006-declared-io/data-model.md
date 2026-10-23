# Data Model: Declared Inputs and Outputs, and a Lean Manifest

Each type below is tagged **core** (importable with no extra installed) or **train** / **verify** (behind
that extra), because Principle XII's layering rule decides where a type may live before anything
else does.

## Manifest, schema version `caravan/v0.1` — core

The validated manifest. Fields not listed here do not exist, and `extra="forbid"` holds at every
level.

| Field | Type | Default | Read by |
|---|---|---|---|
| `apiVersion` | `"caravan/v0.1"` | `"caravan/v0.1"` | loader |
| `model.name` | name pattern of feature 001 | required | `export` (into the interface contract and the header) |
| `model.version` | `X.Y.Z` | required | `export` (likewise) |
| `model.template` | registered identifier | required | `build` |
| `model.params` | mapping, validated by the template | `{}` | `build` |
| `inputs` | list of `InputDeclaration`, exactly 1 (CF-10) | required | field by field, see *Stages* |
| `outputs` | list of `OutputDeclaration`, exactly 1 (CF-10) | required | field by field, see *Stages* |
| `dataset.source` | path | required | dataset resolution, which hands its content to every stage with `reads_dataset` |
| `dataset.split` | `Split` (unchanged) | 0.7 / 0.15 / 0.15, stratified | `train`, `quantize` |
| `dataset.representative_samples` | int > 0 | none; ≥ 100 required at int8 (CF-4) | `quantize` |
| `train.*` | unchanged | unchanged | `train`, `build` (seed) |
| `export.quantization` | `int8` \| `float16` \| `none` | `int8` | `fit`, `quantize`, `export` |
| `export.formats` | list | `[flatbuffer, c_array]` | `export` |
| `export.targets` | list of board identifiers, ≥ 1 | required | `fit`, `export` |

**Removed**, each with its own message (FR-001): `compliance`, `model.topic`, `model.task`,
`dataset.license`, `dataset.permitted_use`, `dataset.labels`, `dataset.window`,
`export.accuracy_drop_max`, `verify`, `bench`, `publish`. The last three return with their stages.

Every field is read by a stage (Principle I), with two fields whose reading the constitution itself
settles: `apiVersion` is required by Principle IX and read by the loader, and `dataset.source`
names the data that `data`, `build`, `train` and `quantize` read. `model.name` and
`model.version` are read by `export`, which writes them into the interface contract and the
header, so a firmware author can tell which model they hold.

### InputDeclaration — core

| Field | Type | Default | Rule |
|---|---|---|---|
| `name` | `[a-z][a-z0-9_]{0,31}` | required | CF-9 |
| `kind` | `"series"` | required | CF-10 names the kinds implemented |
| `columns` | list of distinct non-empty strings, ≥ 1 | derived: every column but the output's, in file order | DS-12 at run time |
| `window` | int > 0 | none | CF-6, unchanged in meaning, now at `inputs[0].window` |

### OutputDeclaration — core

| Field | Type | Default | Rule |
|---|---|---|---|
| `name` | `[a-z][a-z0-9_]{0,31}` | required | CF-9; unique across inputs and outputs |
| `kind` | `"class"` | required | CF-10 |
| `column` | non-empty string | `"label"` | CF-11 if an input also names it |
| `labels` | list of ≥ 2 distinct non-empty strings | derived: distinct values of `column`, sorted as text | DS-5 both directions when stated; DS-11 when fewer than 2 are derived |
| `accuracy_drop_max` | float in [0, 1] | **required**, no default (Principle V: every manifest states its budgets) | the accuracy gate of feature 003 (Q rules), per output; read by `quantize` only |

## Migration — core

```text
Transform = (mapping) -> (mapping, tuple[MigrationNotice, ...])
```

### MigrationNotice

| Field | Meaning |
|---|---|
| `path` | the field path in the declared version, e.g. `compliance` or `dataset.window` |
| `action` | `dropped`, `moved`, or `added` (only for a budget the previous form left to its default) |
| `to` | the new path, for `moved` (e.g. `inputs[0].window`) |
| `reason` | one sentence, from the table in `contracts/manifest.md` |

`MigrationResult` gains `notices: tuple[MigrationNotice, ...]`. `validate` prints them, `render`
prints them to stderr so they do not corrupt the YAML on stdout, and the run report carries them
under `manifest.migration_notices`.

**Transform `caravan/v0` → `caravan/v0.1`**: see `contracts/manifest.md`, *Migration*. It is a pure
mapping transform with no I/O and no framework, so it runs in the core like the rest of loading.

## Derived values — `data` stage, behind `train` (it parses the dataset)

### DataSchema, written to `data/schema.json`

| Field | Type | Meaning |
|---|---|---|
| `input_columns` | list of str | the columns the input reads, in the order they go into the tensor |
| `output_column` | str | the column the output reads |
| `labels` | list of str | stated in the manifest, or derived from the data and sorted |
| `labels_source` | `stated` or `derived` | which of the two it was |
| `columns_source` | `stated` or `derived` | likewise for the input columns |
| `ignored_columns` | list of str | data columns neither declaration reads, so that a column dropped by a stated list is visible |
| `records` | int | how many records were read |

The pipeline merges `input_columns` into `inputs[0].columns` and `labels` into `outputs[0].labels`
of the resolved manifest. That merged form is what the run's `resolved.yaml` holds and what every
later stage's projection reads.

## Fit pre-check — `fit` stage, behind `train` (it reads the built Keras model)

### FitFloor

| Field | Meaning |
|---|---|
| `resource` | `flash` or `ram` |
| `floor_bytes` | the computed lower bound |
| `method` | which layers were counted and at what element size (research R6), as a sentence |
| `counted_layers` | the layer names that contributed (for flash) or the layer that sets the peak (for ram) |

### FitVerdict, one per board and resource

| Field | Meaning |
|---|---|
| `board` | identifier |
| `resource` | `flash` or `ram` |
| `floor_bytes` | from `FitFloor` |
| `board_bytes` | `flash_kb` or `ram_kb` × 1024, from the board description |
| `board_source` | the source the board description records for that value (Principle VII) |
| `verdict` | `below` or `exceeds` |
| `shortfall_bytes` | for `exceeds` only |

### FitRecord, written to `model/fit.json` on a pass

```text
{ provenance: "estimated", quantization, floors: [FitFloor], verdicts: [FitVerdict],
  not_a_fit_claim: "<sentence>" }
```

On a failure, rule F-1 carries the failing verdicts in `found`, and no artifact is written. That is
the same failure path the accuracy gate uses (feature 003).

## Interface contract — written by `export`; the reading is **verify**, the writing is **core**

### ModelIdentity

| Field | Source |
|---|---|
| `name` | `model.name` |
| `version` | `model.version` |

### TensorBinding, one per declared input and output

| Field | Source |
|---|---|
| `name` | the declared name; also the SignatureDef key |
| `role` | `input` or `output` |
| `position` | position in subgraph 0's input or output list, the index `input(i)`/`output(i)` take (research R5) |
| `tensor_index` | the SignatureDef's tensor index |
| `tensor_name` | the converted tensor's name, as the file has it |
| `shape` | from the file |
| `element_type` | from the file, e.g. `int8` |
| `scale`, `zero_point` | from the file's quantization parameters; `null` for a float tensor |

### InputTransformation, one per input

| Field | Value in this feature |
|---|---|
| `kind` | `series` |
| `columns` | `inputs[0].columns` as resolved (derived or stated) |
| `window` | `inputs[0].window`, or `null` (one record per sample) |
| `stride` | equal to `window`; windows do not overlap |
| `scaling` | `"none"` — this feature adds none (spec, Assumptions) |

### OutputInterpretation, one per class output

| Field | Value |
|---|---|
| `kind` | `class` |
| `labels` | in output-unit order |
| `decision` | `"argmax"`, which is how the train and quantize stages turn scores into a class today |

## Rules — core (`caravan/manifest/errors.py`)

| Identifier | Group | Status |
|---|---|---|
| CF-3, CF-5, CF-7, CF-8, DS-9 | — | **retired**, reserved, never reused |
| CF-9, CF-10, CF-11 | manifest rules | new |
| DS-11, DS-12 | dataset rules | new |
| F-1 | fit rules | new group |
| X-6 | export rules | new: a declared name missing from the converted model's signature |
| DS-5 | dataset rules | unchanged in meaning; its path becomes `outputs[0].labels` |
| CF-6 | manifest rules | unchanged in meaning; its path becomes `inputs[0].window` |

## Stages after this feature

A stage reads the declaration **field by field**, never the whole list (Principle III, FR-031). The
projection supports an index in a path, `outputs[0].labels`, for this purpose. That keeps a
budget change, which only `quantize` reads, from changing the keys of `data`, `build` and
`train`.

| Stage | Upstream | Reads (projection) | Writes | Needs |
|---|---|---|---|---|
| `data` | — | `inputs[0].columns`, `outputs[0].column`, `outputs[0].labels` (as declared) + dataset | `data/schema.json` | train |
| `build` | — | `model.template`, `model.params`, `train.seed`, `inputs[0].name`, `inputs[0].columns`, `inputs[0].window`, `outputs[0].name`, `outputs[0].labels` + dataset | `model/built.keras`, `model/built.json` | train |
| `fit` | `build` | `export.targets`, `export.quantization` | `model/fit.json` | train |
| `train` | `build` | `train.*`, `dataset.split`, `inputs[0].columns`, `inputs[0].window`, `outputs[0].name`, `outputs[0].labels` + dataset | as feature 002 | train |
| `quantize` | `train` | `export.quantization`, `dataset.representative_samples`, `dataset.split`, `train.seed`, `inputs[0].columns`, `inputs[0].window`, `outputs[0].name`, `outputs[0].labels`, **`outputs[0].accuracy_drop_max`** + dataset | as feature 003 | train, verify |
| `export` | `quantize` | `model.name`, `model.version`, `export.formats`, `export.targets`, `export.quantization`, `inputs[0].name`, `inputs[0].columns`, `inputs[0].window`, `outputs[0].name`, `outputs[0].labels` | as feature 004 + `model/interface.json` | verify |

Every stage but `data` reads `inputs[0].columns` and `outputs[0].labels` **after** the merge, so the
derived values are part of its key. `data` reads them **before** the merge, as the author wrote
them (a list or the marker `derived`), so its key does not depend on its own output.

What each change re-runs, as a consequence:

| Change | Re-runs |
|---|---|
| `outputs[0].accuracy_drop_max` | `quantize`, `export` |
| `export.targets` | `fit`, `export` |
| `model.name` or `model.version` | `export` |
| a label pinned or reordered | every stage from `data` |
