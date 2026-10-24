# Contract: what the firmware sees

## `model/interface.json`

The values below illustrate the shape. The real ones come from a run (quickstart §3).

```json
{
  "contract_version": 2,
  "model": {"name": "picket-mlp", "version": "0.2.0"},
  "model_file": "model/model.tflite",
  "runtime_binding": "by position in subgraph 0: interpreter.input(position) / interpreter.output(position)",
  "window_size": 64,
  "stride": 64,
  "preprocessing": "inside the model; pass raw values",
  "inputs": [
    {"name": "can_id", "type": "category", "position": 1, "dtype": "int32", "shape": [1, 64],
     "tensor_index": 1, "tensor_name": "serving_default_can_id:0", "scale": null, "zero_point": null,
     "fitted": {"vocab": [291, 608, 790, 1072], "codes": [291, 608, 790, 1072],
                "text_codes": null, "cut": 0, "unknown_index": 0, "missing": -1},
     "encoder": {"type": "dense", "embedding_size": 4},
     "text_codes": null, "missing": -1},
    {"name": "dlc", "type": "number", "position": 3, "dtype": "float32", "shape": [1, 64],
     "fitted": {"normalization": "zscore", "shift": 7.12, "scale": 1.89, "fill": 0.0},
     "missing": 0.0}
  ],
  "outputs": [
    {"name": "label", "type": "category", "position": 0, "dtype": "float32", "shape": [1, 4],
     "labels": ["dos", "fuzzy", "normal", "replay"], "decision": "argmax"}
  ]
}
```

- **`position`**: the index the runtime's `input(i)` takes, read from the converted file's
  signature, never assumed (feature 006). The converter reorders inputs.
- **`dtype`**: what the firmware writes, `float32` for `number` and `int32` for `category` and
  `binary`. No input is int8, so `scale` and `zero_point` are `null` for every input.
- **`text_codes`**: for a `category` column whose values in the data are text, the table text →
  int32 code that the firmware passes. `null` when the values are already integers.
- **`spellings`**: for a `binary` input, the table spelling → 0 or 1.
- **`missing`**: the value to pass when a reading is absent (the fitted fill value; for an integer
  category, an integer in no vocabulary).
- **`fitted`**: everything learned from the training part (FR-012). It is applied inside the model;
  it is here so that a reader can see what the model does to a raw value, not for the firmware to
  repeat.
- **`outputs[0].dtype`** is float32 (DEQUANTIZE inside the model). The `decision` is:
  - `argmax` for `category`, with `labels` in output-unit order;
  - `threshold` for `binary`, with `threshold` (default 0.5) and `true_spelling`;
  - `value` for `number`, which is already in the column's unit, with its `clip`.

## `model_data.h`

Per input, a named position constant with the element type and its meaning in a comment; the same
for the output. A `category` input's comment says the code is an integer, never a rounded number.

```c
constexpr unsigned int g_model_data_input_can_id = 1;  /* int32[64] — category code, an integer and never a rounded number */
constexpr unsigned int g_model_data_input_dlc = 3;  /* float32[64] — raw value */
constexpr unsigned int g_model_data_output_label = 0;  /* float32[4] — argmax */
```

For the output: the label array for `category`, and the threshold for `binary`
(`constexpr float g_model_data_output_<name>_threshold = 0.5f;`).

The constants keep the form feature 006 gave them (`g_model_data_input_<name>`); the `#define`
form this contract first sketched was not adopted, so a firmware written for feature 006's header
reads the same kind of name.

## Runner skeleton

```c
Fill_can_id(interpreter.input(g_model_data_input_can_id)->data.i32, 64);
Fill_dlc(interpreter.input(g_model_data_input_dlc)->data.f, 64);
// … every input by name, raw values, no scaling
interpreter.Invoke();
UseOutput(output->data.f, 4);
```

The skeleton contains no scale, zero point, mean or vocabulary (SC-005).
