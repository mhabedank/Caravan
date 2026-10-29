# Data Model: Templates for the Application Classes

What this feature adds to the manifest, the run's artifacts and the export. Everything not named
here is unchanged from feature 008 and 009.

## Template parameter spec (core, `caravan/templates/registry.py`)

Two fields join `TemplateParameterSpec`, each with a default that keeps `mlp` and `conv1d` exactly as
they are:

| Field | Type | Default | Read by |
|---|---|---|---|
| `output_types` | tuple of output type names | `("category", "binary", "number")` | manifest validation (CF-18) |
| `takes_images` | bool | `False` | manifest validation (CF-19) |
| `plane_fit` | callable `(params, rows, columns) -> None \| (problem, accepted)`, either axis `None` when unknown | `None` | manifest validation and the build stage (CF-6) |

`consumes_window` keeps its meaning for windowed inputs; with an image input the window rule is
CF-19's, not CF-6's.

## Template `conv2d`

Parameters (`caravan/templates/conv2d.py`):

| Key | Type | Default | Rule |
|---|---|---|---|
| `blocks` | list of block, at least one | — | |
| `head` | `average` \| `flatten` | `average` | `average` is full-plane average pooling (research R2) |

Block:

| Key | Type | Default | Meaning |
|---|---|---|---|
| `kind` | `standard` \| `separable` | `standard` | separable: depthwise with `kernel`/`stride`, then 1 × 1 with `filters` |
| `filters` | int > 0 | — | output channels |
| `kernel` | int > 0, or [rows, columns] | — | an int means square |
| `stride` | int > 0, or [rows, columns] | 1 | |
| `padding` | `valid` \| `same` | `valid` | |
| `normalise` | bool | `false` | after each convolution of the block, folds at conversion |
| `pool` | int > 0, or [rows, columns], or null | null | max pooling after the block |
| `dropout` | 0 ≤ x < 1 | 0 | no layer at 0 |

`output_types`: category, binary, number. `takes_images`: true. `consumes_window`: true (a window
input needs one; an image input forbids one, CF-19).

The plane: a window gives rows = `window_size`, columns = the sum of the input features' channels,
one channel; an image gives height × width × channels.

## Template `autoencoder`

Parameters (`caravan/templates/autoencoder.py`):

| Key | Type | Default | Meaning |
|---|---|---|---|
| `encoder` | list of int > 0, at least one | — | dense widths, ReLU |
| `code` | int > 0 | — | the bottleneck, linear |
| `decoder` | list of int > 0 | the encoder reversed | dense widths, ReLU |
| `dropout` | 0 ≤ x < 1 | 0 | after each hidden layer; no layer at 0 |

`output_types`: anomaly. `takes_images`: false. `consumes_window`: true. A code at least as wide as
the input is accepted and reported (it reconstructs trivially; the AUC shows it).

## Input type `image`

```yaml
input_features:
  - name: image          # the column naming each record's file, relative to the dataset directory
    type: image
    preprocessing:       # every key optional
      height: 96
      width: 96
      num_channels: 3    # 1 or 3
      resize_method: interpolate   # or crop_or_pad
```

| Key | Default | Notes |
|---|---|---|
| `height`, `width` | taken from the data when every image agrees, else refused (DS-17) | |
| `num_channels` | taken from the data when every image agrees, else refused | 1 or 3 |
| `resize_method` | `interpolate` | Ludwig's names |
| `missing_value_strategy`, `fill_value` | not accepted | a record without its image is refused (DS-17) |

Fitted values, written by the data stage into `data/preprocessing.json` and merged into the resolved
manifest under `preprocessing.fitted`:

```json
{"height": 96, "width": 96, "num_channels": 3, "resize_method": "interpolate",
 "taken_from_data": ["height", "width"], "images": 1200, "resized": 37, "converted": 4,
 "formats": {"png": 1200}}
```

Model input: named after the feature, shape (height, width, channels), **uint8, scale 1, zero point
0** in the converted file (research R6). Inside the Keras model it is float32 0–255, scaled by 1/255.

Constraints (CF-19): the only input feature; no `window_size`; a template with `takes_images`.

## Output type `anomaly`

```yaml
output_features:
  - name: condition            # the column telling normal from abnormal
    type: anomaly
    preprocessing:
      normal_label: normal     # default "normal"
    threshold_percentile: 95   # default 95
    auc_drop_max: 0.02         # required: the int8 budget (CF-16)
```

| Key | Type | Default | Read by |
|---|---|---|---|
| `preprocessing.normal_label` | text | `normal` | data, train, quantize, export |
| `threshold_percentile` | 0 < x < 100 | 95 | quantize |
| `auc_drop_max` | 0 ≤ x ≤ 1 | required | quantize (the gate) |

Fitted (`data/preprocessing.json`): `{"normal_label": "normal", "values": {"fault": 412, "normal":
2588}, "abnormal_labels": ["fault"]}`.

Targets: 0 for normal, 1 for any other value. Stratified splits draw per condition value.

The model's output, named after the feature: one float32 per window, the mean squared difference
between the reconstruction and the preprocessed input.

## Run artifacts

`metrics.json` (train) for an anomaly output, per split `val` and `test`:
`auc`, `normal_windows`, `abnormal_windows`, and `score_mean_normal`, `score_mean_abnormal`;
`dataset.training_windows`, the count training actually used: the training part, or its normal
windows for an anomaly output.

`quantization.json` for an anomaly output:

```json
"gate": {"metric": "auc", "trained": 0.98, "quantized": 0.979, "change": 0.0015,
         "budget": 0.02, "verdict": "pass", "samples": 600, "split": "test"},
"auc": {"trained": ..., "converted": ..., "quantized": ..., "conversion_drop": ...,
        "quantization_drop": ..., "threshold": 0.02, "verdict": "pass",
        "normal": 300, "abnormal": 300},
"threshold": {"rule": "percentile", "percentile": 95, "value": 0.0297,
              "computed_on": "int8 scores of the validation part's normal windows", "windows": 300},
"detection": {"split": "test", "true_positive_rate": 0.92, "false_alarm_rate": 0.04}
```

For an image input, `calibration` gains `"bounds_frames": 2` and `model.inputs[*]` shows uint8 with
scale 1.0 and zero point 0.

`model/fit.json`: unchanged shape; the input record of an image counts 1 byte per element, and
depthwise convolutions are counted as convolutions.

## Interface contract (`model/interface.json`, contract version 3)

Version 3 because two entries gain fields a reader must understand; nothing is removed.

Input entry of an image:

```json
{"name": "image", "type": "image", "dtype": "uint8", "shape": [1, 96, 96, 3],
 "scale": 1.0, "zero_point": 0, "height": 96, "width": 96, "num_channels": 3,
 "channel_order": "RGB", "layout": "rows, then columns, then channels",
 "frame": "pass frames of exactly this size; the model does not resize"}
```

Output entry of an anomaly:

```json
{"name": "condition", "type": "anomaly", "dtype": "float32", "shape": [1, 1],
 "decision": "threshold", "threshold": 0.0297, "abnormal_when": "score >= threshold",
 "normal_label": "normal", "score": "mean squared reconstruction error of the window"}
```

`window_size` and `stride` are `null` for an image model. The header gains, for an anomaly output,
`constexpr float <array>_output_<name>_threshold`, as a binary output has.

## Test windows (`model/test_windows.h`)

- An image model's window is one image; the C type is `uint8_t` (`kTfLiteUInt8`, member `uint8`).
- An anomaly model selects round-robin by normal and abnormal; the decision is
  `score >= threshold`, as for a binary output.

## Dataset identity

`DatasetFiles.version` covers the tables and, for an image input, every file the image column names,
in sorted order (research R11). `DatasetFiles.images` lists them for the reader.
