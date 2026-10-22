# Phase 1 Data Model: Quantize

Date: 2026-10-22 · Feature: 003 · Decisions: [research.md](./research.md)

The manifest schema gains nothing (Principle IX). These are the in-memory and on-disk shapes.

## Calibration

### `CalibrationPlan` (core — `caravan/stages/quantize.py`)

| Field | Type | Meaning |
|---|---|---|
| `requested` | `int \| None` | `dataset.representative_samples`; **`None` when the manifest asks for no calibration** |
| `available` | `int` | samples in the **training** split (never the test split) |
| `used` | `int` | `min(requested, available)`, or `0` when `requested` is `None` |
| `seed` | `int` | `train.seed`; the draw is reproducible from it |
| `indices` | `tuple[int, ...]` | which training samples, in the order they were drawn; empty when none |

Rules:

- The draw is `random.Random(seed).sample` over the training split's indices, so two runs of one
  manifest calibrate on the same samples.
- `used < requested` is **recorded, not refused** (FR-003). The arbiter of whether calibration was
  enough is the accuracy gate.
- **Only int8 calibrates.** `representative_samples` is `int | None` in the schema and rule CF-4
  requires it only when `export.quantization` is `int8` — so on a valid `float16` or `none`
  manifest it is legitimately `None`, and a plan that computed `min(None, available)` would raise
  on correct input. For those settings the plan is built with `requested=None`, `used=0` and no
  indices, and the conversion is given no representative dataset. The analysis pass caught this
  before it was written.
- `available == 0` cannot occur: feature 002 already refuses an empty split (DS-8).

## The produced model

### `TensorRecord` (extra `verify` — `caravan/runtime/inspect.py`)

What the produced file says about itself, read with the runtime and never from the converter.

| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | the tensor's name as the file carries it |
| `dtype` | `str` | `int8`, `int32`, `float32`, … — as the file says |
| `shape` | `tuple[int, ...]` | |
| `scale` | `float \| None` | quantization scale, where the tensor has one |
| `zero_point` | `int \| None` | |

### `ModelInspection`

| Field | Type | Meaning |
|---|---|---|
| `path` | `Path` | the file that was read |
| `size_bytes` | `int` | measured, not estimated (FR-019) |
| `input` / `output` | `TensorRecord` | including scale and zero point |
| `tensors` | `tuple[TensorRecord, ...]` | every tensor |
| `dtype_counts` | `dict[str, int]` | e.g. `{"int8": 9, "int32": 9}` — the summary a reader checks |
| `fully_integer` | `bool` | true when no tensor is floating point |

Rules:

- **Q-3**: a model whose manifest said `int8` and whose `fully_integer` is false fails the run,
  naming the tensors that are not integers. The stage never describes a model as int8 unless the
  file says so (FR-009).
- `float16` and `none` have no integer expectation; their records are reported as they are.
- Nothing in this type is derived from the conversion's output or logs (FR-006). The converter
  prints `fully_quantize: 0` for a fully quantized model, which is why.

## The measurement

### `SplitMeasurement` (extra `verify` — `caravan/runtime/measure.py`)

| Field | Type | Meaning |
|---|---|---|
| `accuracy` | `float` | correct predictions over samples |
| `confusion` | `tuple[tuple[int, ...], ...]` | rows are truth, columns prediction |
| `samples` | `int` | how many, so the resolution of the figure is visible |
| `split` | `"test"` | this feature measures the test split only |
| `dataset_version` | `str` | the fingerprint of feature 002 |

Rules:

- An integer input tensor is fed integer data, quantized with the model's **own** scale and zero
  point (R4). Feeding float data into an int8 tensor is a silent misreading of bytes, not an error.
- The class decision is the arg-max of the output as stored; no dequantization is needed because it
  is monotonic, and no probability is reported.
- Every figure carries `split`, `dataset_version` and `samples`, so it can be written as the
  `QualityMetric` feature 002 defined — which cannot be constructed without them.

### `AccuracyComparison` (core)

The three figures and the two differences (FR-010, R7).

| Field | Type | Meaning |
|---|---|---|
| `trained` | `float` | the trained model, measured with the training framework |
| `converted` | `float` | the converted model before quantization, measured with the runtime |
| `quantized` | `float` | the model that would be deployed, measured with the runtime |
| `conversion_drop` | `float` | `trained - converted` — what conversion cost |
| `quantization_drop` | `float` | `converted - quantized` — **what the gate judges** |
| `threshold` | `float` | `export.accuracy_drop_max`, an absolute difference |
| `verdict` | `"pass" \| "fail"` | `quantization_drop <= threshold` |
| `samples` | `int` | the test split's size |
| `resolution` | `float` | `1 / samples`: the smallest difference this split can express |

Rules:

- A **negative** drop (the quantized model scores higher) is recorded as negative, never clamped:
  clamping would hide a measurement worth looking at.
- `threshold` is absolute, as `accuracy_drop_max` is written in the schema: 0.02 is two points of
  accuracy, not two percent of it.
- **Q-4**: `verdict == "fail"` fails the run, and no quantized-model artifact survives.
- **Q-5**: a comparison that cannot be computed fails the run. Unknown is not within budget.
- With `quantization: none`, `converted` and `quantized` are the same model and
  `quantization_drop` is zero by construction — the correct reading of "no quantization, no
  quantization loss", and `conversion_drop` is then the only figure with anything to say.

## The diagnostic table

### `LayerErrorRow` (extra `train` — `caravan/convert/debugger.py`)

Produced **only** when the gate fails (FR-016, R6).

| Field | Type | Meaning |
|---|---|---|
| `op_name` | `str` | the operator, as the debugger names it |
| `tensor_name` | `str` | the tensor it writes |
| `num_elements` | `int` | |
| `rmse` | `float` | `sqrt(mean_squared_error)` from the debugger's own columns |
| `scale` | `float` | the tensor's quantization scale |
| `rmse_over_scale` | `float \| None` | the ranking value; `None` where `scale` is zero |
| `max_abs_error` | `float` | |

Rules:

- Rows are ordered by `rmse_over_scale` descending, so the layer most likely to have lost the
  accuracy is first.
- The reference value `1 / sqrt(12)` ≈ 0.289 is reported alongside the table, because a number
  without its reference is not yet information. The LiteRT guide's own example flags rows above
  0.7.
- Neither value becomes a gate. The gate is the author's threshold; this table is the evidence
  that lets them act on it.

## The stage

### `StageSpec` declaration

```python
QUANTIZE = StageSpec(
    name="quantize",
    reads=(
        "export.quantization",
        "export.accuracy_drop_max",
        "dataset.representative_samples",
        "dataset.split",
        "dataset.labels",
        "dataset.window",
        "train.seed",
    ),
    reads_dataset=True,
    upstream="train",
    artifacts=("model/quantized.tflite", "quantization.json"),
)
```

`export.targets` is deliberately absent: adding a board must not re-quantize, because the quantized
model does not depend on which boards it is destined for. The generic projection test of feature
002 covers this stage the moment it is registered, and will fail if the set and the code disagree.

`quantization-error.csv` is **not** a declared artifact: a declared artifact that a stage does not
write is an error (feature 002's cache insists), and this one exists only for a failed run — which
never reaches the cache at all.

## Rule identifiers introduced here

A new group: rules that refuse a run at the quantization stage. Like the DS rules of feature 002
they cannot have an invalid-manifest fixture, so they get their own coverage test.

| Rule | Refuses because |
|---|---|
| Q-1 | the trained model cannot be read, naming the stage that produced it |
| Q-2 | the conversion itself failed, reporting what the converter said |
| Q-3 | a model declared int8 is not fully integer, naming the offending tensors |
| Q-4 | **the accuracy gate failed**: the loss from quantization exceeds the manifest's threshold |
| Q-5 | the comparison could not be measured, so the budget cannot be shown to hold |

**Q-1 is about an unreadable model, not a missing one.** A missing `model/trained.keras` cannot
occur: the stage runner of feature 002 runs the upstream stage first, and a cache entry whose
artifacts are absent counts as a miss, so the artifact is always there by the time this stage runs.
What *can* happen is that it is there and will not load — a truncated or corrupt cached file. The
rule is written for that, and the analysis pass narrowed it rather than leaving a second
unreachable rule after DS-7.

Q-4 is also recorded as a `Gate` in the report's existing `gates` list — the mechanism feature 001
built for exactly this — with its name, its result and the two numbers in its detail. The finding
and the gate entry are the same event seen by a person and by a machine.
