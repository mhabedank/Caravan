# Manifest reference

One YAML file per model version, schema `caravan/v0.2`.

## A first manifest

```yaml
apiVersion: caravan/v0.2

model:
  name: my-classifier
  version: 0.1.0
  template: mlp
  params:
    hidden: [32, 16]

# One feature per CSV column the model reads.
input_features:
  - {name: dlc, type: number}
  - {name: b0, type: number}
  - {name: b1, type: number}

# The column to predict, and how much accuracy int8 may cost.
output_features:
  - name: label
    type: category
    accuracy_drop_max: 0.02

preprocessing:
  window_size: 64

# A directory of your own CSV files, each with a header row, relative to this file.
dataset: my-data

export:
  quantization: int8
  targets: [esp32]
  representative_samples: 500
```

`model` picks the template and its size. `input_features` and `output_features` name the columns the
model reads and the one it predicts, each with a type. `export` sets the quantization and the board.
Run `caravan validate` on the file to check it before you run anything else. The
[complete example](#a-complete-example) at the bottom shows every block.

The manifest reference is a lookup. Each section of the manifest has its own page, which opens with
a table of its fields for scanning and then gives every field an entry that answers four questions:

- **Does** — what it changes about the model or the run.
- **Default** — why the default is what it is.
- **Change it** — the situation that calls for another value.
- **Extremes** — what goes wrong at either end.

If you are choosing rather than looking up, start with a topic guide:
[feature types](../../topics/feature-types.md) for `number`, `category`, `binary`, `image` and
`anomaly`;
[templates](../../topics/templates.md) for `mlp`, `conv1d`, `conv2d` and `autoencoder`;
[applications](../../topics/applications.md) for which template serves which kind of problem;
[budgets and gates](../../topics/budgets-and-gates.md) for the two checks that can stop a run.

**Two terms used throughout.** The {term}`training part` is the share of windows the model learns
from; validation and test are the other two. {term}`derived` means the value is learned from the
training part by the `data` stage and written into each run's `resolved-manifest.yaml`.

{cmd}`caravan render` with `--stdout` prints any manifest with every default filled in, which is
faster than reading the reference when you only want to know what you are running.

The names follow [Ludwig](https://ludwig.ai)'s wherever Ludwig has the concept, because Caravan
borrowed the idea of declaring a type per column rather than inventing a vocabulary for it. Only
types and options that can run inside a model on a microcontroller exist here.

## The sections

One page per top-level section of the manifest:

```{toctree}
:maxdepth: 1
:titlesonly:

top-level
model
input-features
output-features
preprocessing
defaults
trainer
export
```

## A complete example

The example from [part 1 of the tutorial](../../intro/tutorial01.md), on the synthetic data that comes with Caravan:

```yaml
apiVersion: caravan/v0.2

model:
  name: picket-mlp
  version: 0.2.0
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1

input_features:
  - name: can_id
    type: category
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

dataset: ../tests/fixtures/datasets/synthetic

trainer: {epochs: 50, batch_size: 256, learning_rate: 0.001, early_stop: 5}
random_seed: 42

export:
  quantization: int8
  formats: [flatbuffer, c_array]
  targets: [s32k144, stm32h743, esp32]
  representative_samples: 500
  test_windows: 16
```
