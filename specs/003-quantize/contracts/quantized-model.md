# Contract: The Quantized Model, and What Is Read Back From It

Date: 2026-10-22 · Feature: 003 · Decisions: R1, R2, R4, R9 in [research.md](../research.md)

## What is produced

```text
runs/<run>/
├── model/
│   ├── built.keras            # from feature 002
│   ├── trained.keras          # from feature 002 — the input to this stage
│   └── quantized.tflite       # NEW
├── quantization.json          # NEW — the record the report is built from
└── quantization-error.csv     # NEW, and only when the gate failed
```

The file extension is the one the format actually has. The *format identifier* in the manifest
stays `flatbuffer`, because the constitution forbids vendor product names for identifiers that
outlive a release — and this product has been renamed twice in two years.

## How it is produced

The converter takes the trained model directly. Both documented paths produce byte-identical output
(research R1), so the shorter one is used.

Per quantization setting:

| `export.quantization` | What is produced | Integer expectation |
|---|---|---|
| `int8` | full integer: int8 weights, int8 input and output, calibrated | every tensor int8 or int32 |
| `float16` | float16 weights, float input and output | none |
| `none` | converted, not quantized | none |

Only `int8` has a model that asks for it. The other two exist because the schema accepts them, and a
stage that crashed on two of three settings would be a schema contract that is not kept.

## How what was produced is established

**By reading the file.** Not from the converter's return value, not from its options, and above all
not from its log. The converter prints

```text
fully_quantize: 0, inference_type: 6, input_inference_type: INT8, output_inference_type: INT8
```

for a model whose every tensor is int8 or int32 (verified 2026-10-22 by reading the produced file).
A stage that read that line as a verdict would report the opposite of the truth.

So `quantization.json` records what the runtime says the file contains:

```json
{
  "model": {
    "path": "model/quantized.tflite",
    "size_bytes": 15664,
    "trained_size_bytes": 57448,
    "setting": "int8",
    "fully_integer": true,
    "dtype_counts": {"int8": 9, "int32": 9},
    "input":  {"name": "serving_default_input:0", "dtype": "int8", "shape": [1, 64, 5],
               "scale": 0.9999967217445374, "zero_point": -128},
    "output": {"name": "StatefulPartitionedCall:0", "dtype": "int8", "shape": [1, 4],
               "scale": 0.00390625, "zero_point": -128},
    "tensors": ["…one record per tensor…"]
  },
  "calibration": {
    "requested": 500, "available": 56, "used": 56,
    "split": "train", "seed": 42
  },
  "accuracy": {
    "split": "test", "samples": 12, "dataset_version": "sha256:8fac…",
    "trained": 0.666667, "converted": 0.666667, "quantized": 0.666667,
    "conversion_drop": 0.0, "quantization_drop": 0.0,
    "threshold": 0.02, "verdict": "pass",
    "resolution": 0.083333
  },
  "tools": {
    "converter": {"name": "tensorflow", "version": "2.21.0"},
    "runtime": {"name": "ai-edge-litert", "version": "2.3.0"},
    "python": "3.13.16"
  }
}
```

Rules the writer enforces:

- `fully_integer` is computed from the tensor records, never from the setting that was requested.
- A model whose setting is `int8` and whose `fully_integer` is false fails the run (**Q-3**), naming
  the tensors that are not integers.
- `resolution` is `1 / samples`: the smallest accuracy difference this split can express. It is
  recorded because a threshold finer than the resolution cannot be judged, and a reader deserves to
  see that without recomputing it.
- `calibration.split` is always `train`. There is no code path that calibrates on the test split.
- Sizes are read from the filesystem. No ratio is computed (research R9).

## How it is measured

The input tensor is integer, so it is fed integer data, quantized with the model's **own** scale and
zero point:

```python
q = clip(round(x / scale) + zero_point, -128, 127).astype(int8)
```

Handing float data to an int8 tensor is not an error — it is a silent reinterpretation of bytes, and
the accuracy that comes out would be nonsense shaped like a measurement. The class decision is the
arg-max of the output as stored; dequantizing is unnecessary because arg-max is monotonic under it,
and no probability is reported.

The same runtime measures the converted float model and the quantized one, so the difference between
those two numbers is the quantization and nothing else (research R7).

## What the next feature reads

The export stage reads `model/quantized.tflite` and, from the manifest, `export.formats` and
`export.targets`. It reads nothing else from this run. The analysis stage will read the same file
plus `quantization.json`, and will use the same `verify` extra to do it — which is most of why that
extra exists here rather than later.
