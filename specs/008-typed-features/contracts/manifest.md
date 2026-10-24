# Contract: the manifest, schema version `caravan/v0.2`

## The pilot

```yaml
apiVersion: caravan/v0.2

model:
  name: picket-mlp
  version: 0.2.0
  template: mlp
  params: {hidden: [32, 16], dropout: 0.1}

input_features:
  - name: can_id
    type: category                    # a code, not a magnitude
  - {name: dlc, type: number}
  - {name: b0, type: number}
  - {name: b1, type: number}
  - {name: b2, type: number}

output_features:
  - name: label
    type: category
    accuracy_drop_max: 0.02

preprocessing:
  window_size: 64
  split: {type: stratify, column: label, probabilities: [0.7, 0.15, 0.15]}

dataset: ../../datasets/synthetic

trainer: {epochs: 50, batch_size: 256, learning_rate: 0.001, early_stop: 5}
random_seed: 42

export:
  quantization: int8
  formats: [flatbuffer, c_array]
  targets: [s32k144, stm32h743, esp32]
  representative_samples: 500
```

A column not listed under a feature, the split column and the output column are not used. Every
run lists them under `ignored_columns`.

## Input features

| Key | Types | Default | Meaning |
|---|---|---|---|
| `name` | all | required | the column; `[a-z][a-z0-9_]{0,31}` (CF-9) |
| `type` | — | required | `number`, `binary`, `category` (CF-14 otherwise) |
| `preprocessing.normalization` | number | `zscore` | `zscore`, `minmax`, `iq`, `null` |
| `preprocessing.missing_value_strategy` | number, binary, category | `fill_with_const` | also `fill_with_mean` for number |
| `preprocessing.fill_value` | number, binary, category | `0`, `false`, `<UNK>` | as in Ludwig |
| `preprocessing.most_common` | category | `32` | vocabulary cap; the rest is "unknown" |
| `preprocessing.vocab` | category | derived | pins the vocabulary and its order |
| `preprocessing.fallback_true_label` | binary | none | which unusual spelling is true |
| `encoder.type` | category | `dense` | `dense` (embedding) or `onehot` |
| `encoder.embedding_size` | category | `min(vocab, 4)` | the embedding's width |

## Output feature (exactly one)

| Key | Types | Default | Meaning |
|---|---|---|---|
| `name`, `type` | — | required | the column; `category`, `binary`, `number` |
| `preprocessing.vocab` | category | derived | pins the label order |
| `loss.class_weights` | category | none | list in label order or a map label → weight |
| `loss.positive_class_weight` | binary | none | as in Ludwig |
| `threshold` | binary | `0.5` | the device decision |
| `loss.type` | number | `mean_squared_error` | also `mean_absolute_error`, `huber` |
| `preprocessing.normalization` | number | `null` | fitted on train, inverted in the model |
| `clip` | number | none | `[low, high]` |
| `accuracy_drop_max` | category, binary | required | int8 budget (CF-16 if on `number`) |
| `mae_increase_max` | number | required | int8 budget in the column's unit (CF-16 if on another type) |

## Global preprocessing

| Key | Default | Meaning |
|---|---|---|
| `window_size` | required by the registered templates (CF-6) | consecutive rows per sample; windows never overlap |
| `split.type` | `random` | `random`, `stratify`, `fixed` |
| `split.probabilities` | `[0.7, 0.15, 0.15]` | train, validation, test; > 0, sum 1 (CF-1); not with `fixed` (CF-12) |
| `split.column` | — | `stratify`: must be the output's column (CF-15); `fixed`: values `0`/`1`/`2` or `train`/`validation`/`test`; never a feature (CF-13) |

## Defaults

```yaml
defaults:
  number: {preprocessing: {normalization: minmax}}
  category: {encoder: {type: onehot}}
```

A feature's own value wins, then `defaults`, then the table above. `render` shows every feature
fully resolved. `defaults` applies to input features, with `preprocessing` and `encoder`; the
output's few keys are stated on the output itself.

## Trainer and seed

`trainer`:
- `epochs` (50);
- `batch_size` (256);
- `learning_rate` (0.001);
- `optimizer.type` (`adam`, `sgd`, `adamw`);
- `early_stop` (5; −1 disables).

`random_seed` (42) is top-level. It seeds the split, the calibration sample and training.

## Removed from `caravan/v0.1`, each with its own message

| `v0.1` | `v0.2` |
|---|---|
| `inputs` | `input_features`, one entry per column |
| `outputs` | `output_features` |
| `inputs[0].window` | `preprocessing.window_size` |
| `inputs[0].columns`, `outputs[0].column`, `kind` | the feature's `name` and `type` |
| `outputs[0].labels` | `output_features[0].preprocessing.vocab` |
| `dataset.source` | `dataset` |
| `dataset.split` | `preprocessing.split` |
| `dataset.representative_samples` | `export.representative_samples` |
| `train.*` | `trainer.*` with Ludwig's names; `train.seed` → `random_seed` |

A `caravan/v0.1` manifest as a whole is refused with V-1 and the change note.

## Rules

| Identifier | Status |
|---|---|
| CF-1, CF-2, CF-4, CF-6, CF-9, CF-11, CF-12, CF-13, B-1, T-1, T-2, V-1 | kept; paths as above |
| CF-10 | retired: several input features are allowed. Exactly one output is enforced by CF-16's group under a new identifier, CF-17 |
| CF-14 | new: unimplemented feature type |
| CF-15 | new: `stratify` on a column other than the output's |
| CF-16 | new: budget key does not match the output type |
| CF-17 | new: not exactly one output feature |
| DS-12 | kept: a feature names a column the data lacks |
| DS-13 | kept: fixed-split value not in `0/1/2` or `train/validation/test` |
| DS-14 | new: an output class occurs outside the training part only |
| DS-15 | new: a `binary` column with more than two spellings and no `fallback_true_label` |
