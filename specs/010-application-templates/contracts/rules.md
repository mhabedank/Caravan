# Contract: New and Extended Rules

Every rule here gets one fixture under `tests/fixtures/manifests/invalid/` (validation rules) or a
test that produces it (run rules), as the project requires of every rule. Messages follow the
project's form: the field path, what was wrong, what is accepted. No library type name, module path
or traceback.

## Validation rules (exit code 2)

### CF-6 — the window or the plane does not fit the template (extended)

Unchanged for `conv1d`. For `conv2d`, both axes are walked:

```
preprocessing.window_size: the conv2d template needs more of the plane than this manifest has:
  the columns axis has 3 columns when block 1 is reached, and that block's kernel spans 4
  accepted: a kernel of 3 or less on the columns axis in block 1; at least 4 columns
```

With an image input the path is `input_features[0].preprocessing.height` or `.width`. When an axis is
unknown at validation (a derived image size, a `onehot` category's vocabulary), the build stage
raises the same rule before training.

### CF-18 — the template cannot serve the output type (new)

```
model.template: the autoencoder template answers anomaly outputs; output_features[0] is a category
  accepted: an anomaly output, or a template answering category: conv1d, conv2d, mlp
```

### CF-19 — an image input in a combination that cannot be built (new)

Three cases, one rule:

```
input_features[1]: an image input must be the model's only input; found 2 inputs
preprocessing.window_size: a model with an image input reads one record per sample, so the window
  must be left out
model.template: the mlp template does not take images
  accepted: conv2d
```

### CF-14, CF-16 (extended)

`image` joins the input types and `anomaly` the output types. An anomaly output states its budget
as `auc_drop_max`; `accuracy_drop_max` and `mae_increase_max` are refused on it, and `auc_drop_max`
on any other output.

## Run rules (exit code 2, from a stage)

### DS-16 — nothing normal to learn from (new)

```
output_features[0].preprocessing.normal_label: the training part holds no window whose condition is
  normal; values found there: fault (82)
```

Also raised when the stated `normal_label` occurs nowhere in the data, naming the values found.

### DS-17 — an image that cannot be read as declared (new)

```
dataset: record 3, column image: notes.txt is not an image this build reads
  accepted: png, jpeg, bmp, gif
input_features[0].preprocessing.height: the images are not all one height (16 in 210 images, 24 in
  3) and no height is stated
  accepted: a stated height, to which every image is resized
```

A path outside the dataset directory is refused at fingerprinting with DS-1, naming the record.

### Q-5 — the gate cannot decide (extended)

For an anomaly output: a test part with no normal or no abnormal window has no AUC.

### Q-6 — an image input does not take raw pixels (new)

```
export.quantization: the converted model's image input "image" has scale 0.941 and zero point 0;
  raw pixels need scale 1 and zero point 0, so the device would have to rescale every frame
```

Not expected to occur (research R6); it exists so that the contract's promise is a check.

## Templates listing (`caravan templates`)

Unchanged form. The summaries name the problem each template is for:

| Template | Summary |
|---|---|
| `autoencoder` | Anomaly detection from normal data: reconstructs a window and scores how unusual it is |
| `conv1d` | Convolutional decider over a window of samples; blocks of filters and a pooling head |
| `conv2d` | Convolution over a plane: feature frames (rows by columns) or an image; standard and separable blocks |
| `mlp` | Feature-based decider over a window of samples; hidden layer widths and dropout |
