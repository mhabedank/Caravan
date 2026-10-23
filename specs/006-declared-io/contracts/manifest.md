# Contract: the manifest, schema version `caravan/v0.1`

## The pilot, in the new form

```yaml
apiVersion: caravan/v0.1

model:
  name: picket-mlp
  version: 0.1.0
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1

inputs:
  - name: frames
    kind: series
    window: 64

outputs:
  - name: attack
    kind: class
    accuracy_drop_max: 0.02

dataset:
  source: ../../datasets/synthetic
  split:
    train: 0.7
    val: 0.15
    test: 0.15
    stratified: true
  representative_samples: 500

train:
  epochs: 50
  batch: 256
  optimizer: adam
  early_stopping: true

export:
  quantization: int8
  formats: [flatbuffer, c_array]
  targets: [s32k144, stm32h743, esp32]
```

The file has 33 non-blank, non-comment lines, against 43 in the previous form (SC-001 asks for
at most 34). Every field in it is read by some stage (`data-model.md`, *Stages*). The labels come
from the `label` column, and the input columns are every other column. The budget is stated, not
defaulted, as Principle V requires.

## The full form of a declaration

```yaml
inputs:
  - name: frames            # required; [a-z][a-z0-9_]{0,31}; what a runner binds by
    kind: series            # required; the only input kind in this feature
    columns: [can_id, dlc, b0, b1, b2]   # optional; default: every column but the output's
    window: 64              # optional; required exactly when the template consumes a window (CF-6)

outputs:
  - name: attack            # required; same pattern; unique across inputs and outputs (CF-9)
    kind: class             # required; the only output kind in this feature
    column: label           # optional; default "label"
    labels: [normal, dos, fuzzy, replay]  # optional; pins the order; default: derived, sorted
    accuracy_drop_max: 0.02 # required, no default (Principle V); the accuracy gate's budget
```

## Validation rules this contract adds

| Rule | Fires when | Path | Message form |
|---|---|---|---|
| CF-9 | a name breaks the pattern, or repeats across inputs and outputs | `inputs[i].name` / `outputs[i].name` | "a declaration name must be …; found …" |
| CF-10 | more than one input or output, or a kind not implemented | `inputs` / `outputs` / `…kind` | "one input and one output are implemented; several arrive with the first named model or documented application that needs them (Principle X, docs/research/2026-10-23-multi-io-on-mcu.md)" |
| CF-11 | a column is stated by the input and is the output's column | `inputs[0].columns` | "column … is the output's answer and cannot also be an input" |

The windowed-template rule CF-6 keeps its meaning and moves to `inputs[0].window`.

## Removed fields

A removed field written in the new form is rejected at its own path with this message, not with
the generic "unknown field". That is FR-001: the author learns that the field is gone, not that it
is misspelt.

| Path | Message |
|---|---|
| `compliance` | removed in caravan/v0.1: Caravan carries no compliance layer (constitution 3.0.0, Principle VI); a project that needs one adds it on top |
| `model.topic`, `model.task` | removed in caravan/v0.1: no stage read it; the output's kind says what the model does |
| `dataset.license`, `dataset.permitted_use` | removed in caravan/v0.1: Caravan does not check data rights and does not claim to (Principle VI) |
| `dataset.labels` | moved in caravan/v0.1 to `outputs[0].labels`, which is optional: labels are derived from the data |
| `dataset.window` | moved in caravan/v0.1 to `inputs[0].window` |
| `export.accuracy_drop_max` | moved in caravan/v0.1 to `outputs[0].accuracy_drop_max`: the budget is per output (Principle V) |
| `verify`, `bench`, `publish` | removed in caravan/v0.1: no stage reads it yet; it returns with its stage (Principle I) |

## No migration from `caravan/v0`

Constitution 4.0.0 (Principle IX): before Caravan 1.0.0 nothing is migrated. A manifest that
declares `caravan/v0`, any other version this build does not implement, or no version at all, is
refused with V-1 at `apiVersion`:

```text
picket-mlp.yaml: apiVersion — schema version not implemented by this build; this build reads only
caravan/v0.1 and does not migrate older forms before Caravan 1.0.0 — docs/manifest-changes.md says
what to edit by hand, found 'caravan/v0'
    accepted: caravan/v0.1
```

The file is never written. `docs/manifest-changes.md` holds the change note: every field of the
previous form, where it went, and the edit an author makes by hand. The invalid fixtures of the
retired rules were deleted with the rules: the fields they tested no longer exist, and a
previous-form manifest is refused before any of them would be read.

## The resolved manifest

Key order as in the table of `data-model.md`. `render` emits `derived` where a run would put a
derived value:

```yaml
inputs:
- name: frames
  kind: series
  columns: derived
  window: 64
outputs:
- name: attack
  kind: class
  column: label
  labels: derived
  accuracy_drop_max: 0.02
```

A run's `resolved.yaml` holds the values the `data` stage found, for example
`labels: [dos, fuzzy, normal, replay]`. A resolved manifest from `render` therefore differs from a
run's in exactly these two places, and in no other.
