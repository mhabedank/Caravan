# Manifest reference

One YAML file per model version, schema `caravan/v0.2`. Each table below covers one section:
- every field, its type, its default and its allowed values;
- **read by:** the pipeline stage whose result depends on the field. Changing a field re-runs that
  stage and the stages after it, and nothing before it;
- the [rules](rules.md) that check it.

`caravan render` shows any manifest with every default filled in.

**Two terms used below:**
- **The training part** is the share of windows the model learns from. Validation and test are the
  other two (see [`preprocessing.split`](#preprocessing)).
- **`derived`** means the value comes from the training part. It is fitted by the `data` stage and
  recorded in each run's `resolved-manifest.yaml`.

The names follow Ludwig wherever Ludwig has the concept. Only types and options that can run inside
a model on a microcontroller exist ([compatibility](../compatibility.md)).

## Top level

| Field | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `apiVersion` | string | — (required) | `caravan/v0.2` | every stage | [V-1](rules.md#v-1) |
| `dataset` | string | — (required) | a directory of `.csv`, `.tsv` or `.txt` files with a header row, or a single such file, relative to the manifest | data | [DS-1](rules.md#ds-1) to [DS-15](rules.md#ds-15) |
| `random_seed` | integer | `42` | any | data, build, train, quantize, export | — |

A manifest of the previous schema, `caravan/v0.1`, is refused with V-1 and a pointer to
[the change note](../manifest-changes.md). Each key that moved is refused at its old path, naming
its new one.

## `model`

| Field | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `model.name` | string | — (required) | your model's name | export | — |
| `model.version` | string | — (required) | your model's version | export | — |
| `model.template` | string | — (required) | `mlp`, `conv1d`, `conv2d`, `autoencoder` (`caravan templates`) | build | [T-1](rules.md#t-1), [CF-6](rules.md#cf-6), [CF-18](rules.md#cf-18), [CF-19](rules.md#cf-19) |
| `model.params` | mapping | `{}` | the template's parameters, below | build | [T-2](rules.md#t-2), [CF-6](rules.md#cf-6) |

**`mlp`:**
- `hidden`, a list of layer widths, at least one;
- `dropout`, from 0 up to but not including 1, default 0.

**`conv1d`:**
- **`blocks`:** a list, at least one, each with:
  - `filters`;
  - `kernel`;
  - `stride` (1);
  - `padding` (`valid` or `same`);
  - `normalise` (`false`);
  - `pool` (none);
  - `dropout` (0).
- **`head`:** `average` (default) or `flatten`.

**`conv2d`** (feature 010). A convolution over a plane: a window seen as rows by input columns, or
an image. Answers `category`, `binary` and `number`; the only template that takes an image.
- **`blocks`:** a list, at least one, each with:
  - `kind`: `standard` (default) or `separable` — a depthwise convolution with the block's kernel
    and stride, then a 1 x 1 convolution with its filters;
  - `filters`;
  - `kernel`: an integer for a square, or `[rows, columns]`;
  - `stride` (1), an integer or `[rows, columns]`;
  - `padding` (`valid` or `same`);
  - `normalise` (`false`), after each convolution of the block;
  - `pool` (none), max pooling after the block, an integer or `[rows, columns]`;
  - `dropout` (0).
- **`head`:** `average` (default), average pooling over the whole remaining plane, or `flatten`.

A plane too small for the blocks on either axis is refused ([CF-6](rules.md#cf-6)): at validation
when the manifest gives the size, otherwise by the build stage, before training.

**`autoencoder`** (feature 010). Anomaly detection from normal data. Answers the `anomaly` output
and nothing else ([CF-18](rules.md#cf-18)).
- `encoder`, a list of dense widths from the input towards the code, at least one;
- `code`, the width of the linear bottleneck;
- `decoder`, a list of widths back out, default the encoder reversed;
- `dropout`, from 0 up to but not including 1, default 0.

## `input_features[]`

One entry per column the model reads. A column no feature names is ignored, and every run lists it
under `ignored_columns`.

| Field | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `input_features[].name` | string | — (required) | a column of the data, of the form `[a-z][a-z0-9_]{0,31}`, each column once | data, build, train, quantize, export | [CF-9](rules.md#cf-9), [CF-11](rules.md#cf-11), [CF-13](rules.md#cf-13), [DS-12](rules.md#ds-12) |
| `input_features[].type` | string | — (required) | `number`, `category`, `binary`, `image` | data, build, train, quantize, export | [CF-14](rules.md#cf-14), [CF-19](rules.md#cf-19) |
| `input_features[].preprocessing.normalization` | string or null | `zscore` (number) | `zscore`, `minmax`, `iq`, `null`; `number` only | data, build | — |
| `input_features[].preprocessing.missing_value_strategy` | string | `fill_with_const` | `fill_with_const`, `fill_with_mean` (number only) | data | — |
| `input_features[].preprocessing.fill_value` | number, string or boolean | `0.0` (number), `<UNK>` (category), `false` (binary) | a value of the column's kind | data | — |
| `input_features[].preprocessing.most_common` | integer | `32` (category) | ≥ 1; `category` only | data | — |
| `input_features[].preprocessing.vocab` | list | `derived` (category) | the vocabulary in your order, which pins it; `category` only | data | — |
| `input_features[].preprocessing.fallback_true_label` | string | none (binary) | the spelling that means true; `binary` only | data | [DS-15](rules.md#ds-15) |
| `input_features[].preprocessing.height` | integer | `derived`: the images' height when they all agree | ≥ 1; `image` only | data, build, fit, export | [DS-17](rules.md#ds-17), [CF-6](rules.md#cf-6) |
| `input_features[].preprocessing.width` | integer | `derived`: the images' width when they all agree | ≥ 1; `image` only | data, build, fit, export | [DS-17](rules.md#ds-17), [CF-6](rules.md#cf-6) |
| `input_features[].preprocessing.num_channels` | integer | `derived`: the images' channels when they all agree | `1` (grey) or `3` (RGB); `image` only | data, build, export | [DS-17](rules.md#ds-17) |
| `input_features[].preprocessing.resize_method` | string | `interpolate` | `interpolate` (bilinear), `crop_or_pad`; `image` only | data | — |
| `input_features[].encoder.type` | string | `dense` (category) | `dense` (an embedding), `onehot`; `category` only | build | — |
| `input_features[].encoder.embedding_size` | integer | `derived`: the smaller of the vocabulary size and 4 | ≥ 1; `dense` only | build | — |

**What each type does inside the model.** The firmware passes raw values, one per column and time
step:
- **`number`:** passed as float32. Standardised with the training part's statistics:
  - `zscore`: the mean and the standard deviation;
  - `minmax`: the minimum and the range;
  - `iq`: the median and the interquartile range.

  A missing reading is filled with `fill_value`, or with the training mean for `fill_with_mean`.
- **`category`:** passed as int32. The vocabulary is the training part's `most_common` most
  frequent values, ordered by frequency and then by text; everything else is "unknown". The firmware
  passes:
  - for an integer column, the integer itself;
  - for a text column, the code `interface.json` lists.
- **`binary`:** passed as int32, 0 or 1.
  - Ludwig's spellings are recognised: `yes`/`no`, `true`/`false`, `1`/`0`, `on`/`off` and the
    like.
  - For two spellings of your own, the one that sorts second is true, unless you state
    `fallback_true_label`.
- **`image`** (feature 010): the column names an image file per record, relative to the dataset
  directory, as Ludwig reads images. PNG, JPEG, BMP and GIF are read.
  - The model takes **raw 8-bit pixels** at the declared size, rows then columns then channels:
    uint8 at scale 1 and zero point 0, the camera's bytes. The scaling is inside the model.
  - Images of another size are brought to it for training (`resize_method`); the device passes
    frames of exactly that size, and the model does not resize.
  - An image is the model's only input, one record is one sample, and no `window_size` is stated
    ([CF-19](rules.md#cf-19)).

## `output_features[]`

Exactly one entry: the column the model answers ([CF-17](rules.md#cf-17)).

| Field | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `output_features[].name` | string | — (required) | a column of the data | data, build, train, quantize, export | [CF-9](rules.md#cf-9), [CF-11](rules.md#cf-11) |
| `output_features[].type` | string | — (required) | `category`, `binary`, `number`, `anomaly` | data, build, train, quantize, export | [CF-14](rules.md#cf-14), [CF-18](rules.md#cf-18) |
| `output_features[].preprocessing.vocab` | list | `derived`: by frequency in the training part | every class of the data, in your order, which pins it; `category` only | data | [DS-5](rules.md#ds-5), [DS-11](rules.md#ds-11), [DS-14](rules.md#ds-14) |
| `output_features[].preprocessing.fallback_true_label` | string | none | `binary` only | data | [DS-15](rules.md#ds-15) |
| `output_features[].preprocessing.normal_label` | string | `normal` | the column's value that means normal; `anomaly` only | data, train, quantize, export | [DS-16](rules.md#ds-16) |
| `output_features[].preprocessing.normalization` | string or null | `null` | `zscore`, `minmax`, `iq`, `null`; `number` only | data, train | — |
| `output_features[].loss.type` | string | `mean_squared_error` | `mean_squared_error`, `mean_absolute_error`, `huber`; `number` only | train | — |
| `output_features[].loss.class_weights` | list or mapping | none | one weight per class, or class → weight; `category` only | train | — |
| `output_features[].loss.positive_class_weight` | number | none | > 0; `binary` only | train | — |
| `output_features[].threshold` | number | `0.5` | between 0 and 1, exclusive; `binary` only | quantize, export | — |
| `output_features[].clip` | list of two numbers | none | `[low, high]`; `number` only | build, export | — |
| `output_features[].accuracy_drop_max` | number | — (required for `category` and `binary`) | 0 to 1 | quantize | [CF-16](rules.md#cf-16), [Q-4](rules.md#q-4) |
| `output_features[].mae_increase_max` | number | — (required for `number`) | ≥ 0, in the column's unit | quantize | [CF-16](rules.md#cf-16), [Q-4](rules.md#q-4) |
| `output_features[].auc_drop_max` | number | — (required for `anomaly`) | 0 to 1 | quantize | [CF-16](rules.md#cf-16), [Q-4](rules.md#q-4), [Q-5](rules.md#q-5) |
| `output_features[].threshold_percentile` | number | `95` | between 0 and 100, exclusive; `anomaly` only | quantize | — |

**The int8 budget.**
- `accuracy_drop_max` is how much test accuracy quantization may cost, for example `0.02` for two
  points.
- `mae_increase_max` is how much the mean absolute error may grow.
- `auc_drop_max` is how much of the area under the ROC curve quantization may cost: how well the
  anomaly score separates normal from abnormal test windows.
- Exceeding any of them fails the run; no option lowers or skips the gate ([budgets](../budgets.md)).

**Decisions.** What the model's answer means, in `interface.json` and on a board:
- a category takes the argmax;
- a binary compares with `threshold`;
- a number is the value itself;
- an anomaly score is abnormal at or above its threshold.

**The `anomaly` output** (feature 010). It names the column that tells normal from abnormal; every
value other than `normal_label` is abnormal.
- The model's output is the **anomaly score**: the mean squared difference between the window as the
  model saw it and its reconstruction, computed inside the model.
- Training learns from the normal windows of the training part only; calibration uses all of them.
- The threshold is the `threshold_percentile`-th percentile of the int8 model's scores on the
  validation part's normal windows. `quantization.json` records it, with the detection and false
  alarm rates on the test part, and `interface.json` states it.

## `preprocessing`

| Field | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `preprocessing.window_size` | integer | none | ≥ 1; required by templates that consume a window (all four do), left out with an image input | data, build, train, quantize, export | [CF-6](rules.md#cf-6), [DS-6](rules.md#ds-6) |
| `preprocessing.split.type` | string | `random` | `random`, `stratify`, `fixed` | data, train, quantize, export | [CF-12](rules.md#cf-12), [CF-15](rules.md#cf-15) |
| `preprocessing.split.probabilities` | list of three numbers | `[0.7, 0.15, 0.15]` | train, validation, test; each > 0, summing to 1; not with `fixed` | data, train, quantize, export | [CF-1](rules.md#cf-1), [CF-12](rules.md#cf-12), [DS-8](rules.md#ds-8) |
| `preprocessing.split.column` | string | the output's column for `stratify` | for `stratify`, the output's column; for `fixed`, the column naming each record's part | data, train, quantize, export | [CF-12](rules.md#cf-12), [CF-13](rules.md#cf-13), [CF-15](rules.md#cf-15), [DS-13](rules.md#ds-13) |

**Windows.** `window_size` consecutive records form one sample.
- Windows never overlap.
- A window whose records disagree on the output is discarded and counted.

**Splits.**
- **`random`:** splits windows by `probabilities`.
- **`stratify`:** does so per class of the output.
- **`fixed`:** lets the data decide. Every record names its part in `column`, as `train`,
  `validation` or `test`, or as Ludwig's `0`, `1` or `2`.
  - Use it when samples of one subject, vehicle or session must stay on one side.
  - A window whose records name two parts is discarded.
  - The split column is never a feature.

## `defaults`

Preprocessing and encoder settings for every input feature of one type. A feature's own value
still wins, and the type's built-in default applies last. `<type>` is `number`, `category`,
`binary` or `image`.

| Field | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `defaults.<type>.preprocessing.normalization` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.missing_value_strategy` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.fill_value` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.most_common` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.vocab` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.fallback_true_label` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.height` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.width` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.num_channels` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.preprocessing.resize_method` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.encoder.type` | as for a feature | — | as for a feature | through each feature | — |
| `defaults.<type>.encoder.embedding_size` | as for a feature | — | as for a feature | through each feature | — |

## `trainer`

| Field | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `trainer.epochs` | integer | `50` | ≥ 1 | train | — |
| `trainer.batch_size` | integer | `256` | ≥ 1 | train | — |
| `trainer.learning_rate` | number | `0.001` | > 0 | train | [DS-10](rules.md#ds-10) |
| `trainer.optimizer.type` | string | `adam` | `adam`, `sgd`, `adamw` | train | — |
| `trainer.early_stop` | integer | `5` | epochs without improvement of the validation loss before stopping; `-1` never stops | train | — |

## `export`

| Field | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `export.targets` | list of strings | — (required) | board identifiers (`caravan boards`), each once | build (fit check), export | [B-1](rules.md#b-1), [CF-2](rules.md#cf-2), [F-1](rules.md#f-1) |
| `export.quantization` | string | `int8` | `int8`, `float16`, `none` | build (fit check), quantize, export | [Q-3](rules.md#q-3) |
| `export.formats` | list of strings | `[flatbuffer, c_array]` | `flatbuffer`, `c_array` (`onnx` is refused) | export | [X-1](rules.md#x-1) |
| `export.representative_samples` | integer | none; required for `int8` | ≥ 100: how many training windows calibrate the int8 quantization. When the training part holds fewer, all of them are used and the report says so | quantize | [CF-4](rules.md#cf-4) |
| `export.test_windows` | integer | `0` | 0 to 64; above 0 needs `c_array` in `export.formats` | export | — |

**`export.test_windows`** writes `model/test_windows.h`:
- that many windows of the test part, every class in turn, as raw values;
- with what the data says and what the int8 model answered on your computer.

A [board run](../guides/lora32.md) compares the board's answers with these.
- When the test part holds fewer windows, all of them are written, and `export.json` says so.
- The default `0` writes none, so your data enters an export only when you ask.

## A complete example

The example from [Try it](../try-it.md), on the synthetic data that comes with Caravan:

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
