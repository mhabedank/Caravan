# Contract: what the firmware sees

## `model/interface.json`

```json
{
  "model": {"name": "picket-mlp", "version": "0.2.0"},
  "window_size": 64,
  "inputs": [
    {"name": "can_id", "type": "category", "position": 1, "dtype": "int32", "shape": [1, 64],
     "vocab": [291, 608, 790, 1072, 0, 1073],
     "text_codes": null, "missing": 0},
    {"name": "dlc", "type": "number", "position": 3, "dtype": "float32", "shape": [1, 64],
     "missing": 0.0}
  ],
  "output": {"name": "label", "type": "category", "position": 0, "dtype": "float32",
             "shape": [1, 4], "labels": ["normal", "dos", "fuzzy", "replay"],
             "decision": "argmax"},
  "preprocessing": "inside the model; pass raw values"
}
```

- **`position`**: the index the runtime's `input(i)` takes, read from the converted file's
  signature, never assumed (feature 006). The converter reorders inputs.
- **`dtype`**: what the firmware writes, `float32` for `number` and `int32` for `category` and
  `binary`. No input is int8, so no scale or zero point appears for inputs.
- **`text_codes`**: for a `category` or `binary` column whose values in the data are text, the
  table text → int32 code that the firmware passes. `null` when the values are already integers.
- **`missing`**: the value to pass when a reading is absent (the fitted fill value).
- **`output.dtype`** is float32 (DEQUANTIZE inside the model). The `decision` is:
  - `argmax` for `category`;
  - `threshold: 0.5` for `binary`;
  - `value` for `number`, which is already in the column's unit.

## `model_data.h`

Per input, a position constant and the element type:

```c
#define PICKET_MLP_INPUT_CAN_ID 1   /* int32[64]  — category code */
#define PICKET_MLP_INPUT_DLC    3   /* float32[64] — raw value */
```

For the output: its position, the label array for `category`, and the threshold for `binary`.

## Runner skeleton

```c
fill_int32(interpreter.input(PICKET_MLP_INPUT_CAN_ID), can_id_window);
fill_float(interpreter.input(PICKET_MLP_INPUT_DLC), dlc_window);
// … every input by name, raw values, no scaling
interpreter.Invoke();
```

The skeleton contains no scale, zero point, mean or vocabulary (SC-005).
