# Phase 1 Data Model: Build and Train

Date: 2026-10-22 · Feature: 002 · Decisions: [research.md](./research.md)

Nothing here is a manifest field. The manifest schema gains nothing in this feature (FR of the
spec, Principle IX); these are the in-memory and on-disk shapes the two stages work with.

## Dataset

### `DatasetFiles` (core — `caravan/data/fingerprint.py`)

What a `dataset.source` resolved to, and what it hashes to.

| Field | Type | Meaning |
|---|---|---|
| `root` | `Path` | the resolved source, relative to the manifest's directory |
| `files` | `tuple[Path, ...]` | the data files, in sorted relative-path order — the sequence order |
| `version` | `str` | `sha256:` + hex digest over, per file, its relative path, its byte length and its bytes |
| `total_bytes` | `int` | recorded in the report, so a reader can tell a 2 KB fixture from a 2 GB dataset |

Rules:

- A `source` that does not exist, is not readable, or is a directory containing no file with a data
  extension → rule **DS-1**, naming the path and which of the three it was.
- A directory is not searched recursively at 0.1.0: only its own files. A nested layout is a
  rejection naming the subdirectories found, not a silent partial read.
- The version is computed from bytes, never from mtime or size alone (R4).

### `RecordSchema` (extra — `caravan/data/reader.py`)

The header, once it has been read and checked.

| Field | Type | Meaning |
|---|---|---|
| `feature_names` | `tuple[str, ...]` | every column but `label`, in header order |
| `label_column` | `int` | the index of the `label` column |
| `record_count` | `int` | records read across all files, excluding headers |

Rules:

- No column named `label` → **DS-2**, listing the columns found.
- Fewer than one feature column → **DS-2**.
- Files whose headers differ → **DS-3**, naming both files and the first differing column.
- A cell that is empty or not a number → **DS-4**, naming the file, the record number within that
  file, and the column.
- A label value not in `dataset.labels` → **DS-5**, naming the value and the declared labels.
- Declared labels never seen in the data → **DS-5** as well: a label the model is asked to predict
  and the data does not contain is a disagreement, not a curiosity.

### `WindowPlan` (core — `caravan/data/windows.py`)

The windowing decision, computed from counts and labels alone — no arrays, so it is testable on
every Python in the matrix (R5).

| Field | Type | Meaning |
|---|---|---|
| `window` | `int \| None` | from the manifest; `None` means one record is one sample |
| `kept` | `tuple[int, ...]` | start index of each kept window, in sequence order |
| `labels` | `tuple[int, ...]` | the label index of each kept window, parallel to `kept` |
| `discarded_mixed` | `int` | windows whose records disagreed about the label |
| `dropped_remainder` | `int` | records at the end that did not fill a window |

Rules:

- Windows are consecutive and non-overlapping. Window *i* covers records `[i·w, (i+1)·w)`.
- A window whose records carry more than one label is discarded and counted; it is never labelled
  (FR-025).
- `kept` empty → **DS-6**, naming the records read, the windows examined and how many were
  discarded for which reason. "No usable data" is never reported as an empty training run.
- The feature width a sample presents is `window × len(feature_names)`, and it is recorded. There is
  nothing to check it against: the manifest declares no feature width (FR-004), so the width is
  derived, not verified. A dataset whose files disagree with *each other* about their columns is
  caught by DS-3 instead.
- Too few records to fill one window → **DS-6**, naming the records read and the window stated. This
  is the case a feature-width check would otherwise have been asked to cover.

### `SplitPlan` (core — `caravan/data/windows.py`)

| Field | Type | Meaning |
|---|---|---|
| `train` / `val` / `test` | `tuple[int, ...]` | indices into `WindowPlan.kept`, disjoint, union complete |
| `stratified` | `bool` | as the manifest states |
| `seed` | `int` | from `train.seed`; the split is part of what the seed reproduces |
| `per_label_counts` | `dict[str, dict[str, int]]` | label → split → count, written into the report |

Rules:

- The procedure is the one specified in R6, including the remainder rule, because "shuffle and
  slice" is not reproducible from a report.
- A split part that comes out empty → **DS-8**, naming the part, the label and the counts.

## The model

### `BuiltModel` — `model/built.json`

What `build` reports (FR-003) and what the next stage reads.

| Field | Type | Meaning |
|---|---|---|
| `template` | `str` | the template identifier |
| `input_shape` | `list[int]` | `[window, features]`, or `[features]` without a window |
| `output_units` | `int` | `len(dataset.labels)` |
| `parameter_count` | `int` | trainable plus non-trainable, reported separately as well |
| `layers` | `list[LayerRecord]` | name, kind, output shape, parameter count |
| `framework` | `{name, version}` | recorded because the artifact came from it (FR-022) |

### `TrainedModel` — `model/trained.keras`, plus `metrics.json`

| Field | Type | Meaning |
|---|---|---|
| `epochs_run` | `int` | may be fewer than `train.epochs` when early stopping fired |
| `stopped_early` | `bool` | and `stopped_epoch` when it did |
| `best_epoch` | `int` | the epoch `checkpoints/best.keras` came from, by validation metric |
| `metrics` | `list[QualityMetric]` | see below |
| `effective_settings` | `dict[str, object]` | every training setting as used, manifest or default (FR-008) |

### `QualityMetric`

The entity the spec calls inseparable from what it was measured against (FR-007).

| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | `accuracy`, `precision_macro`, `recall_macro`, `f1_macro`, `recall_per_class` |
| `value` | `float \| dict[str, float]` | a number, or per class |
| `split` | `"val" \| "test"` | never omitted, and never `train` (FR-006a) |
| `dataset_version` | `str` | the fingerprint of R4 |
| `samples` | `int` | how many windows the number is over |

A metric without `split`, `dataset_version` and `samples` is not writable: the writer rejects it.
That is the whole mechanism behind SC-003 — it is not a convention the writer tries to follow.

## The stage machinery

### `StageSpec` (core — `caravan/stages/base.py`)

| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | `build`, `train` |
| `reads` | `tuple[str, ...]` | dotted paths into the resolved manifest — the only fields the stage receives |
| `reads_dataset` | `bool` | whether the dataset version enters the key |
| `upstream` | `str \| None` | the stage whose key enters this one's |
| `artifacts` | `tuple[str, ...]` | relative paths the stage writes, declared as the constitution requires |

Declared sets for this feature, as implemented:

- `build.reads` = `model.template`, `model.params`, `dataset.window`, `dataset.labels`,
  **`train.seed`**
- `build.reads_dataset` = true — the feature width comes from the data (FR-004), so the data is an
  input to the built shape
- `train.reads` = `train.epochs`, `train.batch`, `train.optimizer`, `train.learning_rate`,
  `train.early_stopping`, `train.patience`, `train.seed`, `dataset.split`, **`dataset.labels`**,
  **`dataset.window`**, `dataset.permitted_use`
- `train.upstream` = `build`

**Three fields were added to these sets during implementation**, and the projection is why: a
stage receives only what it declared, so a field it needs and did not declare is missing the
moment the stage runs.

- `train.seed` belongs to **build**, which the plan had wrong. Keras draws the initial weights when
  the model is constructed, so `built.keras` already contains them — reusing a built model across
  seeds would hand back weights the manifest did not ask for. The seed is in both sets, because
  both stages depend on it.
- `dataset.window` and `dataset.labels` belong to **train**, which the plan left to build alone.
  Forming samples needs the window and ordering the output units needs the labels. The cache was
  never at risk here (build's key is train's upstream), but the stage could not have run.

`dataset.source` is deliberately **not** in either set: the path is not part of the identity of a
result, the dataset's content is. Moving a dataset must not retrain; changing it must.

### `StageInputs`

The projection. Built by the runner from `StageSpec.reads` and nothing else, so a stage physically
cannot read an undeclared field (R7). A `KeyError` from a stage is therefore a declaration bug,
caught by the stage's own tests rather than by review.

### `CacheKey` / `CacheEntry` (core — `caravan/stages/cache.py`)

| Field | Type | Meaning |
|---|---|---|
| `key` | `str` | `sha256:` over the canonical JSON in R7 |
| `stage` | `str` | which stage the entry belongs to |
| `inputs` | `dict` | the projection as it was, so an entry explains itself |
| `dataset_version` | `str \| None` | when the stage reads the dataset |
| `upstream_key` | `str \| None` | the previous stage's key |
| `tool_version` | `str` | in the key on purpose (R7) |
| `produced_by_run` | `str` | the run identifier that created the entry |
| `produced_at` | `str` | UTC, seconds, for a person reading the store |

### `StageOutcome`

What the report records per stage: `produced` or `reused`, the key, the upstream key, the artifacts
written, the duration, and `fresh: true` when `--fresh` bypassed the cache (FR-017).

## Rule identifiers introduced here

Feature 001 grouped rules by what they can refuse. This feature adds a group: rules that refuse a
**run** because the data and the manifest disagree, or the data cannot be read. They cannot have an
invalid-manifest fixture, so they get their own fixture directory and their own coverage test,
exactly as the board rules did.

| Rule | Refuses because |
|---|---|
| DS-1 | the dataset reference does not resolve to readable files |
| DS-2 | the header has no `label` column, or no feature column |
| DS-3 | two files disagree about their header |
| DS-4 | a cell is empty or not a number |
| DS-5 | the data's labels and the manifest's labels disagree |
| DS-6 | no usable sample remains after windowing, including too few records for one window |
| DS-7 | — withdrawn before implementation; see below |
| DS-8 | a split part would be empty |
| DS-9 | the author's `permitted_use` forbids training (FR-009) |
| DS-10 | training diverged: the loss stopped being a finite number (FR-012) |

DS-10 was added during implementation. FR-012 requires a diverged run to fail, to say so and to
leave no model behind — which is a refusal, and every refusal here carries a rule identifier, a
field path and a message of the same shape. Giving it one keeps the mechanism single: the stage
raises it like any other run rule, the command line renders it like any other finding, and the
coverage test demands a test for it like any other.

**DS-7 was withdrawn during the analysis pass**, for the same reason CF-5 was in feature 001: it
turned out to be unreachable. It would have compared the data's feature width against "what the
manifest's window implies", and the manifest implies nothing about feature width — the width comes
from the data. The identifier is left in the table rather than renumbering DS-8 and DS-9, and it is
listed in the entailed group so the coverage test does not demand a fixture for it. The case it was
reaching for is covered twice over: DS-3 for two files that disagree about their columns, DS-6 for
too few records to fill a window.

DS-9 is the author's own statement enforced against them, which is the whole of what Principle VI
claims. It names the field, not a licence interpretation.
