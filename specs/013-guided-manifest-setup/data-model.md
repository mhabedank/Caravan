# Data Model: A Guided Way to Write the Manifest

**Feature**: 013-guided-manifest-setup · **Date**: 2026-11-16

Nothing here is persisted except the written manifest. All other entities live for one run of
`caravan init`. Names are the plan's; the implementation may choose others.

---

## ColumnProfile

What the profiler observed of one column in the sample (research R3, R4). Shown to the author, never
written to the manifest.

| Field | Type | Meaning |
|---|---|---|
| `name` | str | the header cell, as written |
| `rows_seen` | int | rows read for this column |
| `empty` | int | cells that were empty |
| `numeric` | bool | every non-empty cell parses as a number |
| `integer` | bool | every non-empty cell parses as an integer |
| `distinct` | tuple[str, ...] | up to 257 distinct values, in first-seen order |
| `distinct_capped` | bool | the set stopped at 257 |
| `proposal` | `number` \| `category` \| `binary` \| `None` | `None` means "leave out" |
| `reason` | str | the sentence shown with the proposal (R4 table) |
| `image_like` | bool | R4 rule 3 matched |

**Rules**: `proposal` and `reason` come from the first matching rule of R4, in order. A column whose
name does not match the feature name form (`NAME_PATTERN` in `manifest/schema/features.py`) cannot
become a feature and is proposed as left out with that reason, because the manifest names a feature by
its column.

## DataProfile

| Field | Type | Meaning |
|---|---|---|
| `root` | Path | the data directory, or the file's directory |
| `files` | tuple[Path, ...] | the data files, in the order the pipeline reads them |
| `columns` | tuple[ColumnProfile, ...] | in header order |
| `rows_read` | int | |
| `complete` | bool | the sample reached the end of the data |

**Rules**: every file has the same header, or profiling stops with the files and columns that
differ (spec edge case). A directory with no data file, a missing path, or a file without a header
stops profiling with the path and what is wrong.

## TemplateStarter

Added to `caravan.templates.registry` as an optional field of `TemplateParameterSpec` (research R7).

| Field | Type | Meaning |
|---|---|---|
| `params` | Mapping[str, Any] | validated by the template's own parameter model |
| `window` | int \| None | records per window; `None` for a template that consumes none |
| `rank` | int | lower is proposed first among fitting templates; ties by identifier |
| `note` | str | one line on when to choose this template |

**Rules**: a starter's `params` MUST validate against its template's parameter model, and its
`window` MUST pass the template's `window_fit` — a test checks every registered starter, built-in or
third-party, the same way.

## Answer set

The complete set of choices the manifest is written from. Identical whether answered in the dialogue,
by options, or by proposals (research R6), and the writer sees nothing else.

| Answer | Type | Source of the proposal | Asked |
|---|---|---|---|
| `dataset` | Path | — (the first answer) | yes |
| `output` | column name | R5 | yes |
| `output_type` | one of `OUTPUT_TYPES` | R5 | yes |
| `normal_label` | str \| None | the value `normal` when present | only for `anomaly` without a `normal` value |
| `inputs` | ordered list of (column, type) | R4, every column but the output | yes, as one list |
| `template` | identifier | lowest `starter.rank` among fitting templates | yes |
| `params` | mapping | `starter.params` | yes |
| `window` | int \| None | `starter.window`, raised to fit (R7) | yes, when the template consumes one |
| `boards` | ordered list of identifiers | R8 | yes |
| `budget` | float | R8, by output type | yes |
| `name` | str | R8 | yes |
| `version` | str | `0.1.0` | summary only |
| `representative_samples` | int | 100 | summary only |
| `manifest_path` | Path | `<name>.yaml` | yes |

**Validation per answer** (each refused answer is asked again with the reason):
- `output`, `inputs`: a column of the data; feature names match `NAME_PATTERN`; the output is not an
  input (rule CF-11).
- `output_type`: offered only from R5's list.
- `template`: offered only when `output_type in spec.output_types` and the inputs contain no image
  (`init` sets up none, R4 rule 3).
- `params`: the template's parameter model accepts it.
- `window`: a positive integer the template's `window_fit` / `plane_fit` accepts.
- `boards`: registered identifiers, no repeats.
- `budget`: in the schema's range for its key (`BUDGET_KEYS`).
- `name`: the model name form (`manifest/schema/model.py`).
- `manifest_path`: its directory exists; an existing file needs the overwrite confirmation.

## Guided session

| Field | Type | Meaning |
|---|---|---|
| `answers` | Answer set, partially filled | |
| `given` | set of answer names | answered by an option; never asked, not revisited by "back" |
| `position` | index into the question list | |
| `history` | list of positions | for "back" (`<`) |
| `mode` | `dialogue` \| `no-input` | |

**States**: `profiling` → `asking` (questions in order; `<` pops `history`) → `summary` (confirm,
or a question number to revisit) → `writing` (temporary file, validate, `os.replace`) → `done`.
From `writing`, a validation finding returns to `asking` at the owning question in `dialogue` mode,
or ends with exit 1 in `no-input` mode. An interrupt or end of input in any state before `done`
ends with nothing written.

## Written manifest

An ordinary manifest of `caravan/v0.2` (contracts/manifest-output.md), indistinguishable in kind
from a hand-written one, and valid by construction (R9).
