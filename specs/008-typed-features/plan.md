# Implementation Plan: Typed Features, Ludwig-Style

**Branch**: `008-typed-features` | **Date**: 2026-10-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-typed-features/spec.md`

## Summary

The manifest moves to `caravan/v0.2` and uses Ludwig's names:
- `input_features` and `output_features`, one column per feature, each with a `type`;
- `preprocessing` with `window_size` and `split`;
- `defaults` per type;
- `trainer` and `random_seed`.

Each input type brings its preprocessing:
- **fitted** on the training part in the `data` stage;
- **built into the model** as three small layers that lower to operators TFLite Micro has;
- **exported** as one model input per feature: float32 for numbers, int32 for codes.

The firmware passes raw values and nothing else. Outputs are `category`, `binary` and `number`,
each with its loss, metrics, device decision and int8 budget.

The spike measured the core of this on the synthetic pilot with **derived** labels. That case
fails the int8 gate today (0.75 / 0.50); with the new form it gives trained 1.000 and int8 1.000.
The model is 28 KB with an embedding of 4 for `can_id`.

## Technical Context

**Language/Version**: Python ≥ 3.13; the train extra stays on 3.13 (TensorFlow 2.21.0, Keras
3.15.1).

**Primary Dependencies**: none added. The preprocessing layers are Caravan code in the train extra,
and the regression metrics are standard library in the core.

**Storage**: files. Each run's `data/preprocessing.json`, and the interface contract gains a
per-input binding.

**Testing**: pytest. The suites keep their split:
- unit, contract, integration and layering: core, every Python;
- `train`: TensorFlow;
- `verify`: runtime.

New synthetic data for `binary` and `number` outputs is derived at test time from the committed
fixture, as feature 007 did for the fixed split.

**Target Platform**: unchanged; TFLM at `f7ed40d` on s32k144, stm32h743 and esp32.

**Project Type**: CLI and library.

**Performance Goals**:
- SC-003: the typed pilot with derived labels passes int8.
- SC-006: `pace-cnn` reaches at least 0.918 int8.
- The pilot's model size is stated (about 28 KB measured), not a goal.

**Constraints**:
- Only TFLM operators. No `Lambda`, no Keras lookup or encoding layers (research R3).
- Statistics come from the training part only.
- The core imports no framework.

**Scale/Scope**: the largest change since feature 006. It touches the schema, reader, data, build,
train, quantize, export, fit, metrics, fixtures, example, port and documents.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I — every field read | every feature key is read: name/type/preprocessing/encoder by `data` and `build`; `window_size` and `split` by `data`, `train`, `quantize`; the budget by `quantize`; `trainer.*` by `train`; `defaults` is resolved into each feature before any stage, so it is read through them; unlisted columns are visibly ignored | pass |
| II — scope | microcontroller models only; types without a device path are refused | pass |
| III — reproducible | fitted preprocessing is merged into the resolved manifest and so into the keys; `random_seed` recorded | pass |
| IV — provenance | metrics per type keep split and dataset version | pass |
| V — budgets | every output states its int8 budget in its own metric; the fit check counts inputs and constants | pass |
| VI — the data is the author's | nothing asked about rights | pass |
| VII — registries | templates and boards unchanged | pass |
| VIII — export contract | per-input name, position, dtype, shape, type and tables; binding by name | pass |
| IX — variable until 1.0.0 | `caravan/v0.2`, change note, the old form refused | pass |
| X — real models | input types for `picket-mlp` and `pace-cnn`; `binary` and `number` outputs for documented application classes (owner decision) | pass |
| XI — no Claude in learning | the spikes and tests train on the committed synthetic fixture and its test-time derivatives; nothing produced is published | pass |
| XII — small core | no dependency, no verb; the preprocessing layers sit in the train extra, the regression metrics in the core (standard library) | pass |
| Cost (4.1.0) | one PR when built and validated; spec work on the branch without CI | pass |

*Re-checked after Phase 1:* the design adds no dependency, no verb and no data, and no deviation is
needed.

## Project Structure

### Documentation

```text
specs/008-typed-features/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── manifest.md       # caravan/v0.2, every key, defaults, rules
│   └── interface.md      # per-input binding, outputs, header, runner
├── spikes/               # the two measurements of research R2–R4
└── tasks.md              # /speckit-tasks
```

### Source code

```text
src/caravan/
├── manifest/
│   ├── version.py                 # SCHEMA_VERSION = "caravan/v0.2"
│   ├── schema/__init__.py         # input_features, output_features, preprocessing, defaults, trainer, random_seed
│   ├── schema/features.py         # new: feature types, per-type preprocessing/encoder/decoder options (replaces io.py)
│   ├── schema/preprocessing.py    # new: window_size, split {random|stratify|fixed}
│   ├── schema/trainer.py          # renamed from train.py, Ludwig names
│   ├── schema/dataset.py          # dataset path only
│   ├── schema/export.py           # + representative_samples
│   ├── schema/removed.py          # v0.1 keys → messages
│   ├── resolve.py                 # defaults applied; fitted values merged
│   └── errors.py                  # CF-14, CF-15, CF-16, DS-14, DS-15; CF-10 retired
├── data/
│   ├── reader.py                  # typed columns: float, int code, text
│   ├── windows.py                 # unchanged logic; fixed split values per R8
│   └── fit.py                     # new, core: zscore/minmax/iq, vocabulary, binary spellings — pure Python
├── metrics/regression.py          # new, core: MAE, MSE, RMSE, R²
├── templates/builders/
│   ├── preprocessing.py           # new, train: Standardize, VocabularyOneHot, AsChannel (+ dense encoder)
│   └── frontend.py                # new, train: inputs → preprocessing → concat → template body
├── convert/
│   ├── batch.py                   # several inputs, dtype kept, Lambda refused
│   └── tflite.py                  # dict calibration; input type unset; float32 outputs
├── stages/
│   ├── data.py                    # windows, split, fit on train; data/preprocessing.json
│   ├── build.py                   # frontend + template; output head per type
│   ├── train.py                   # loss and metrics per output type
│   ├── quantize.py                # boundary check, dict calibration, gate per type
│   ├── fit.py, targets/fit.py     # inputs and constants in the floors
│   └── export.py                  # contract per input
├── export/interface.py, c_array.py, skeleton.py   # binding, header, runner by name
└── runtime/inspect.py, flatbuffer.py              # several inputs with dtypes

tests/ (new or rewritten)
├── unit/test_features_schema.py, test_fit_preprocessing.py, test_regression_metrics.py
├── contract/test_manifest_v02.py, test_interface_inputs.py
├── train/test_preprocessing_layers.py   # every layer lowers to TFLM ops only; exact one-hot; standardise
├── train/test_typed_pilot.py            # SC-003; raw-value agreement (SC-004)
├── train/test_output_types.py           # binary and number outputs end to end (SC-007)
├── train/test_input_order.py            # converter reorders inputs; calibration and binding by name
└── fixtures/manifests/                  # all rewritten to v0.2; new invalid fixtures for the new rules

examples/picket-mlp.yaml, ports/pace-cnn/{pace-cnn.yaml,convert.py,README.md}   # v0.2; converter stops standardising
docs/manifest-changes.md, docs/try-it.md, README.md                              # v0.2
```

**Structure Decision**: a single project, as before. `schema/io.py` (feature 006) is replaced by
`schema/features.py`, and `schema/train.py` is renamed to `trainer.py`. Before 1.0.0 nothing old
is kept.

## Phase order

1. **Schema and resolver** (`caravan/v0.2`, defaults, rules), with every manifest fixture rewritten.
   Core only, test-first.
2. **Fitting** (`data/fit.py`, core) and the reader's typed columns; the `data` stage writes
   `data/preprocessing.json`.
3. **Preprocessing layers and front-end** (train extra). A test proves each layer lowers only to
   TFLM operators and is exact.
4. **Build and train** per output type; regression metrics.
5. **Conversion and quantize**: several inputs, dict calibration, boundaries, gate per type.
6. **Export**: contract, header, runner by name; fit floors.
7. **Fixtures, example, port, documents.** Then the `pace-cnn` port in the new form (SC-006).
8. **Validation**: full suite, the CI matrix locally, the guide test. Then one PR (constitution
   4.1.0).

## Complexity Tracking

No violations.
