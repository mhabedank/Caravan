# Data Model: Release 0.1.0

## Split — core (`manifest/schema/dataset.py`)

`dataset.split` takes one of two forms. Which one is decided by whether `column` is present.

| Field | Fractions form | Fixed form |
|---|---|---|
| `train`, `val`, `test` | float > 0, sum 1.0 (CF-1); defaults 0.7 / 0.15 / 0.15 | **not accepted** (CF-12) |
| `stratified` | bool, default `true` | **not accepted** (CF-12) |
| `column` | absent | non-empty string; must not be an input or output column (CF-13) |

In the fixed form, `train.seed` keeps seeding training but no longer decides the split.

Read by the `data` stage (which window belongs where), and through the split plan by `train` and
`quantize` (training part, calibration from training only, test part).

## SplitPlan — core (`data/windows.py`)

| Field | Fractions form | Fixed form |
|---|---|---|
| `train`, `val`, `test` | indices drawn by seed | indices from the column |
| `stratified` | as stated | `false` |
| `seed` | `train.seed` | `null` |
| `source` | `"fractions"` | `"column:<name>"` |
| `per_label_counts` | label → part → count | the same |

**WindowPlan** gains `discarded_mixed_split: int` — windows whose records name different parts.
These are counted separately from `discarded_mixed`, which counts windows whose records disagree on
the label.

## Run report — `dataset_resolved` additions

| Key | Meaning |
|---|---|
| `split_source` | `fractions` or `column:<name>` |
| `windows_discarded_mixed_split` | count; `0` in the fractions form |

## Data schema (`data/schema.json`) additions

| Key | Meaning |
|---|---|
| `split_column` | the column, or `null` |
| `ignored_columns` | now also excludes the split column, which is read, not ignored |

## Framework log — run directory

| File | Written when | Holds |
|---|---|---|
| `framework.log` | any stage ran, without `--framework-output` | everything written to file descriptors 1 and 2 while the stages ran: framework, converter, warnings |

The report lists it under `artifacts.framework_log`. It is absent when every stage was reused and
nothing wrote to either descriptor. It is never part of a cache entry: a reused stage writes nothing
into it.

## Rules

| Identifier | Group | Fires when |
|---|---|---|
| CF-12 | manifest | `dataset.split` states `column` together with a fraction or `stratified` |
| CF-13 | manifest | `dataset.split.column` equals `outputs[0].column` or appears in `inputs[0].columns` |
| DS-13 | run (dataset) | the split column is missing from a data file, or a record holds a value other than `train`, `val`, `test` |

An empty part in the fixed form reuses the existing empty-split rule, with the column named in the
finding.

## Release record (not code)

| Item | Where |
|---|---|
| version | `pyproject.toml`, `caravan.__version__`, equal to the tag without its `v` |
| tag | `v0.1.0rc1`, `v0.1.0rc2` …, `v0.1.0`; never moved |
| GitHub release | per tag; candidates marked pre-release; wheel and sdist attached; body = release note |
| release note | `docs/releases/0.1.0.md`: what, where it runs, known limits, the gate, the port's result |
