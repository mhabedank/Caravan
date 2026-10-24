# Schema changes

The manifest is the public interface of the framework. How it may change depends on where Caravan
is (constitution 4.0.0, Principle IX).

## Before 1.0.0: variable, with a change note

Until Caravan 1.0.0 the schema, the command line, the run report and the artifacts may change
without migration and without compatibility. What holds in every phase:

- every manifest declares its schema version (`apiVersion`);
- the author's file is never rewritten;
- an unknown field is refused with its path and the accepted fields;
- a manifest whose version this build does not implement — older, newer, **or none declared** — is
  refused with rule V-1, naming the implemented version and pointing here. It is never migrated and
  never read as some other version;
- a breaking change gets a new version identifier and a section below: what changed, and the edit
  an author makes by hand.

A run stays reproducible without migration because every provenance record carries the Caravan
version that produced it (Principle III): an old manifest runs with the Caravan it was written for.

## The procedure for a breaking change

1. **Decide that the change is breaking.** A new optional field with a default is not: existing
   manifests keep validating. A renamed field, a removed field, a changed meaning or a narrowed
   type is.
2. **Change the version identifier** in `caravan/manifest/version.py` (`SCHEMA_VERSION`) and in
   the schema's `apiVersion` literal. Rewrite the fixtures under `tests/fixtures/manifests/` in the
   new form; nothing in the test suite keeps the old one alive.
3. **Give a removed or moved field its own message** in `caravan/manifest/schema/removed.py`, so an
   author who still writes it learns that it is gone, not that it is misspelt.
4. **Write the change note** as a section below.
5. **Check the entailment:** if the change makes a rule unreachable, move the rule out of
   `MANIFEST_REJECTION_RULES` rather than leaving a fixture that can never fail. A rule whose field
   the change removes is retired, not deleted.

## From 1.0.0: stable

1.0.0 is a deliberate amendment of the constitution. From it, a breaking change requires a new
version identifier and a registered migration that upgrades an older manifest in memory, with a
notice for every field it drops, moves or adds — the full rules of Principle IX, written before the
first change that needs them.

## A rule that cannot fire is not a rule

`DS-7` and `X-5` live in `ENTAILED_RULES` with the reasoning recorded: no state of the schema can
reach them, so they have no fixture.

## A rule that is retired stays reserved

`CF-3`, `CF-5`, `CF-7`, `CF-8` and `DS-9` were removed in feature 006 with the compliance layer;
`V-2`, which read a manifest without a version as the oldest known one, was retired by constitution
4.0.0; `CF-10`, one input and one output, was retired by feature 008, which allows several input
features and gives the single output its own rule, `CF-17`. They sit in `RETIRED_RULES`: in no rule group, in no fixture's expectation, raised by no
module (`tests/unit/test_retired_rules.py`). An identifier that came back with another meaning
would make an old run report lie.

`tests/unit/test_fixture_coverage.py` enforces both directions: every rule that can reject a
manifest has a fixture, and no identifier that cannot reject one has a fixture claiming it does.

## `caravan/v0` → `caravan/v0.1` (feature 006, 2026-10-23)

Constitution 3.0.0 removed the compliance layer (Principle VI) and every field no stage reads
(Principle I), and made the manifest declare what goes into the model and what comes out. The
messages for the removed fields come from `caravan/manifest/schema/removed.py`.

### What changes, and the edit an author makes by hand

| Previous form | New form | Why |
|---|---|---|
| `model.topic`, `model.task` | — | no stage read them; the output's `kind` says what the model does |
| `compliance` | — | Caravan carries no compliance layer; a project that needs one adds it on top |
| `dataset.license`, `dataset.permitted_use` | — | Caravan does not check data rights and does not claim to |
| `verify`, `bench`, `publish` | — | no stage reads them yet; each returns with its stage |
| `dataset.window` | `inputs[0].window` | a window describes how the input is cut |
| `dataset.labels` | `outputs[0].labels` (optional) | labels are derived from the data; a list only pins their order |
| `export.accuracy_drop_max` | `outputs[0].accuracy_drop_max` (**required**) | the budget is per output, and stated (Principle V) |
| the `label` column | `outputs[0].column`, default `label` | the output names the column it reads |
| every other column | `inputs[0].columns`, default all but the output's | the input names the columns it reads |

By hand, the pilot goes from

```yaml
apiVersion: caravan/v0
model: {name: picket-mlp, version: 0.1.0, topic: automotive-security, task: can-ids,
        template: mlp, params: {hidden: [32, 16], dropout: 0.1}}
dataset: {source: data/, window: 64, labels: [normal, dos, fuzzy, replay],
          representative_samples: 500}
export: {targets: [s32k144, stm32h743, esp32], accuracy_drop_max: 0.02}
compliance: {...}
```

to

```yaml
apiVersion: caravan/v0.1
model: {name: picket-mlp, version: 0.1.0, template: mlp, params: {hidden: [32, 16], dropout: 0.1}}
inputs: [{name: frames, kind: series, window: 64}]
outputs: [{name: attack, kind: class, labels: [normal, dos, fuzzy, replay], accuracy_drop_max: 0.02}]
dataset: {source: data/, representative_samples: 500}
export: {targets: [s32k144, stm32h743, esp32]}
```

The names (`frames`, `attack`) are the author's choice; they become the names a firmware author
binds by (`model/interface.json`, the C header).

### Two things to know

- **Pin the labels to keep an old model.** Derived labels are sorted as text. A manifest that
  stated another order and drops the list trains a model whose output units are in a different
  order — a different model. Keep the stated list under `outputs[0].labels` to build exactly the
  model it built before. On the synthetic fixture the difference decides whether the int8 gate
  passes (`specs/006-declared-io/research.md`, R11).
- **State the budget.** The previous form defaulted `accuracy_drop_max` to 0.02; the new form has
  no default, so write the value you relied on.

A manifest still in the previous form is refused with V-1 at `apiVersion`; a previous-form field
written into a `caravan/v0.1` manifest is refused at its own path with the reason in the table
above.

## `caravan/v0.1` → `caravan/v0.2` (feature 008, 2026-10-24)

The manifest uses Ludwig's names wherever Ludwig has the concept (owner decision 2026-10-24). Each
column the model reads is one **input feature** with a **type**, and each type brings its
preprocessing: fitted on the training part, built into the model, so the firmware passes raw values
(`specs/008-typed-features/`). The messages for the moved keys come from
`caravan/manifest/schema/removed.py`.

### What changes, and the edit an author makes by hand

| `caravan/v0.1` | `caravan/v0.2` | Ludwig |
|---|---|---|
| `inputs[0]` (one tensor, columns derived) | `input_features: [{name, type, preprocessing, encoder}]`, one per column | same |
| `outputs[0]` | `output_features: [{name, type, ...}]`, exactly one | same (Ludwig allows several) |
| `inputs[0].window` | `preprocessing.window_size` | per timeseries feature in Ludwig; here for all rows |
| `inputs[0].columns`, `outputs[0].column`, `kind` | the feature's `name` (the column) and `type` | same |
| `outputs[0].labels` | `output_features[0].preprocessing.vocab` | same |
| `dataset.source` | `dataset` | on Ludwig's command line; Caravan keeps it in the manifest |
| `dataset.split` (fractions, `stratified`, `column`) | `preprocessing.split: {type: random\|stratify\|fixed, probabilities, column}` | same |
| — | `defaults: {<type>: {preprocessing, encoder}}` | same |
| `dataset.representative_samples` | `export.representative_samples` | none; it calibrates the quantization |
| `train.epochs`, `train.learning_rate` | `trainer.epochs`, `trainer.learning_rate` | same |
| `train.batch` | `trainer.batch_size` | same |
| `train.optimizer` | `trainer.optimizer.type` | same |
| `train.early_stopping` + `train.patience` | `trainer.early_stop` (patience; `-1` never stops) | same |
| `train.seed` | `random_seed` (top level) | same |

The types implemented: inputs `number`, `binary`, `category`; outputs `category`, `binary`,
`number`. A fixed split's column holds Ludwig's `0`, `1`, `2` or the words `train`, `validation`,
`test` — `val` is now `validation`.

By hand, the pilot goes from

```yaml
apiVersion: caravan/v0.1
model: {name: picket-mlp, version: 0.1.0, template: mlp, params: {hidden: [32, 16], dropout: 0.1}}
inputs: [{name: frames, kind: series, window: 64}]
outputs: [{name: attack, kind: class, accuracy_drop_max: 0.02}]
dataset: {source: data/, split: {train: 0.7, val: 0.15, test: 0.15, stratified: true},
          representative_samples: 500}
train: {epochs: 50, batch: 256, early_stopping: true, patience: 5, seed: 42}
export: {targets: [s32k144, stm32h743, esp32]}
```

to

```yaml
apiVersion: caravan/v0.2
model: {name: picket-mlp, version: 0.2.0, template: mlp, params: {hidden: [32, 16], dropout: 0.1}}
input_features:
  - {name: can_id, type: category}      # a code, not a magnitude
  - {name: dlc, type: number}
  - {name: b0, type: number}
  - {name: b1, type: number}
  - {name: b2, type: number}
output_features:
  - {name: label, type: category, accuracy_drop_max: 0.02}
preprocessing:
  window_size: 64
  split: {type: stratify, column: label, probabilities: [0.7, 0.15, 0.15]}
dataset: data/
trainer: {epochs: 50, batch_size: 256, early_stop: 5}
random_seed: 42
export: {targets: [s32k144, stm32h743, esp32], representative_samples: 500}
```

The input and output names are now the columns, and they are what a firmware author binds by
(`model/interface.json`, the C header). A column no feature names is not used, and every run lists
it under `ignored_columns`.

### Where Caravan keeps its own name, and why

Every exception to Ludwig's naming (SC-002):

| Caravan | Why not Ludwig's |
|---|---|
| `model.template`, `model.params` | Ludwig's `combiner` merges encoder outputs; Caravan's template is the whole network for a microcontroller, so it is not a combiner |
| `dataset` in the manifest | Ludwig takes the data on its command line; a Caravan run's provenance names its data |
| `export` (`quantization`, `formats`, `targets`, `representative_samples`) | Ludwig has no deployment to a microcontroller |
| `accuracy_drop_max`, `mae_increase_max` | Ludwig has no int8 budget; Principle V requires one per output |
| `defaults` covers input features only, with `preprocessing` and `encoder` | the output's keys are few and stated on the output itself |
| the dense encoder is a `Dense` without bias on the one-hot | Ludwig's embedding is a table lookup (GATHER, SELECT v1), which TFLite Micro cannot run; the product with the one-hot is the same function and lowers to FULLY_CONNECTED |
| preprocessing is fitted on the training part only | Ludwig fits on all parts together, which leaks the test part into the preprocessing |

### Three things to know

- **Derived labels are now ordered by frequency** in the training part, descending, ties by text —
  Ludwig's order — and no longer alphabetically. A model that relied on the old order pins it under
  `output_features[0].preprocessing.vocab`.
- **The inputs are no longer one tensor.** A firmware that fed one int8 window of all columns now
  fills one input per feature, by its named position, with raw values: float32 for a number, int32
  for a category code or a 0/1. The contract version is 2.
- **The output is float32.** A category's scores, a binary score or a number come out after the
  model's own DEQUANTIZE; the firmware applies no scale and no zero point.

A manifest in the previous form is refused with V-1 at `apiVersion`; a previous-form key written
into a `caravan/v0.2` manifest is refused at its own path, naming the key that replaces it.
