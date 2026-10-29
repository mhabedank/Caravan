# Implementation Plan: Templates for the Application Classes

**Branch**: `010-application-templates` (developed on `claude/amazing-ptolemy-ik9fss`) | **Date**:
2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-application-templates/spec.md`, scope D decided by
the owner on 2026-10-29.

## Summary

Three additions take Caravan from five of the twelve application classes to nine:

1. **`autoencoder`** template and **`anomaly`** output type. The model reconstructs its
   preprocessed input and computes the anomaly score itself, so the device gets the score. Training
   uses normal windows only; calibration uses all; the gate judges the AUC; the threshold is a
   percentile of the int8 scores of validation normals. `hum-fan`'s architecture builds with
   exactly its 35,280 parameters.
2. **`conv2d`** template. It convolves a plane — a window seen as rows × columns, or an image —
   with standard and depthwise-separable blocks. Its average head is full-plane pooling, which is
   accelerated on both built-in libraries, unlike a global mean. The MLPerf keyword-spotting
   reference builds with 24,908 parameters at 43 KB int8.
3. **`image`** input type. A table column names image files; they are decoded and resized on the
   host; the converted model takes **raw uint8 pixels at scale 1, zero point 0**. This holds because
   calibration starts with a black and a white frame — without them the measured scale was 0.941.

Everything was measured before it was planned ([research.md](research.md)).

## Technical Context

**Language/Version**: Python ≥ 3.13; the train extra stays on 3.13 (TensorFlow 2.21.0, Keras 3).

**Primary Dependencies**: none added. Images are decoded by the framework the `train` extra already
brings (R7); the AUC is standard library (R10); the fixture generators use `zlib` and `struct`.

**Storage**: files. New: fixtures `tests/fixtures/datasets/{frames,anomaly,images}`, three example
manifests in `examples/`.

**Testing**: pytest, in the existing suites — unit, contract, integration and layering (core, every
Python), `train` (TensorFlow), `verify` (runtime). New end-to-end tests run each example manifest
from validation to export.

**Target Platform**: unchanged; TFLM on s32k144, stm32h743, esp32.

**Project Type**: CLI and library.

**Performance Goals**: none new. Reference counts are checks, not goals (SC-003, SC-006, SC-013).

**Constraints**:
- only operators TFLM has, each with a resolver method (one new: `SQUARED_DIFFERENCE`);
- the core imports no framework; the parameter halves stay core;
- no stage branches on a template identifier: template capabilities are fields of the spec,
  differences by input or output type are branches on the *type*;
- the fit check must stay a lower bound: an image input counts 1 byte per element.

**Scale/Scope**: about 1,500 lines of source across templates, schema, data, stages and export;
three fixtures; three examples; documentation pages. The largest single piece is the image path
(reader, fit, fingerprint, converter flag, contract, test windows).

## Constitution Check

*GATE: checked before research and again after design. Both pass.*

| Principle | How this plan complies |
|---|---|
| I. Declarative manifest | Templates by identifier with parameters; `image` and `anomaly` are feature types in Ludwig's form; every new key is read by a stage (table in data-model.md); image size taken from the data when the data settles it, so it is not asked again. |
| II. Embedded targets only | All four classes served run on microcontrollers (research note Part A). Detection, segmentation and signal outputs (NPU class) stay out. |
| III. Reproducible | The fingerprint covers the image files (R11); seeds unchanged; calibration's two bounds frames are deterministic and recorded. |
| IV. Labeled numbers | No accuracy claimed for a real dataset; reference counts are computed in tests; the research note's 38.6K figure is flagged rather than repeated (R1). |
| V. Budgets are gates | The anomaly output brings `auc_drop_max`; an undecidable AUC fails (Q-5); the fit check applies to all new templates with correct byte counts. |
| VI. Data is the author's | No new metadata is asked; `normal_label` has a default; no licence field. |
| VII. Templates are data | Two templates by discovery; capabilities as spec fields, not a list of identifiers in the core. |
| VIII. No lock-in | Contract version 3 states the image input (uint8, size, channel order, no resize) and the anomaly decision; raw pixels are verified in the file (Q-6). |
| IX. Manifest contract | Additive change, schema stays `caravan/v0.2` (R14); change note in `docs/manifest-changes.md`. |
| X. Built for real models | `autoencoder`: `hum-fan` + the anomaly class. `conv2d`: the keyword-spotting class (Speech Commands v2, CC BY 4.0). `image`: VWW and image classification (MLPerf Tiny) + owner decision D5. Separable blocks: the KWS and VWW references both need them. Nothing else is offered: no residual, no dilation, no ReLU6, no resize-in-model. |
| XI. No Claude in model learning | Unaffected: no data generation or labelling by any model; fixtures are arithmetic. |
| XII. Small core | No dependency, no extra; the layering test covers the new core modules. |

No deviation. Complexity tracking is empty.

## Design

### Template capabilities instead of identifiers

`TemplateParameterSpec` gains `output_types`, `takes_images` and `plane_fit` (data-model.md). The
manifest checks CF-18 and CF-19 against them, and CF-6 calls `plane_fit` with the axes it knows. The
build stage calls `plane_fit` again with the built input's shape, so an axis unknown at validation
is still refused before training.

### The front-end (`templates/builders/frontend.py`)

- Image input: `keras.Input(shape=(h, w, c), dtype=float32)`, `Rescaling(1/255)`; the body gets the
  shape (h, w, c).
- Windowed inputs with a body that wants a plane: the body itself reshapes `(window, channels)` to
  `(window, channels, 1)` as its first layer, so the front-end stays template-agnostic (the body's
  first layers are applied to the concatenated tensor, as today).
- `anomaly` output: the body's layers are applied in full (no head replaced); a registered
  `ReconstructionError` layer takes the body's output and the preprocessed tensor and returns the
  mean squared difference with the reduced axis kept. The output dict is keyed by the output's name.

### Builders

- `builders/conv2d.py`: reshape if the input is 2-D; per block: `Conv2D` or `DepthwiseConv2D` +
  1 × 1 `Conv2D`, optional `BatchNormalization` before each `ReLU`, optional `MaxPooling2D`,
  optional `Dropout`; head `AveragePooling2D(full plane)` + `Flatten`, or `Flatten`; `Dense`
  softmax over the labels (replaced by the front-end for binary and number).
- `builders/autoencoder.py`: `Flatten`, encoder `Dense`+ReLU (+dropout), `Dense(code)`, decoder
  `Dense`+ReLU (+dropout), `Dense(prod(shape))`, `Reshape(shape)`.

### Data

- **Reader**: an `image` column is read as text (the path), like a category.
- **Images** (`data/images.py`, train extra): decode, convert channels, resize, report; inspect sizes
  for the data stage's fit. Paths resolved against the dataset root; outside or missing → DS-17 (or
  DS-1 at fingerprinting).
- **Fit**: `fit_image` (sizes stated or taken), `fit_output_anomaly` (normal label present, counts).
  For an anomaly output the input features are fitted on the **normal** training windows.
- **Samples**: `assemble_inputs` returns (samples, h, w, c) float32 pixel arrays for an image;
  `assemble_targets` returns 0/1 for anomaly.
- **Fingerprint**: `resolve_dataset(..., image_columns=...)` hashes the named files (R11).

### Stages

- **data**: fits as above; reports counts per condition.
- **build**: unchanged apart from calling `plane_fit` with the built shape.
- **fit**: depthwise convolutions counted; an image input at 1 byte per element.
- **train**: for anomaly, train and validation take normal windows only, targets are zeros and the
  loss is the mean absolute error (= the mean score, R8); metrics are the AUC and the counts.
- **quantize**: converter told `uint8` input when the model has an image input, calibration
  prepended with the two bounds frames, input scale and zero point verified (Q-6); for anomaly the
  AUC gate, the threshold from int8 validation normals, the detection rates.
- **export**: contract version 3 (image input entry, anomaly output entry); header threshold for
  anomaly; test windows for uint8 and for anomaly.

### Metrics

`caravan/metrics/anomaly.py` (core): `auc(normal, abnormal)` by ranks with ties averaged;
`percentile(values, p)` by linear interpolation (the definition numpy uses by default, so the
documented rule is the familiar one); `detection(normal, abnormal, threshold)`.

### Fixtures and examples

Generators in `tests/fixtures/datasets/<name>/make.py` (standard library), committed data
(research R13). Examples `examples/anomaly-autoencoder.yaml`, `examples/frames-conv2d.yaml`,
`examples/images-conv2d.yaml` point at them.

### Documentation

- `docs/applications.md` (new): the twelve classes, the template and type serving each, an example
  manifest each, or the reason none serves it (FR-001, FR-035).
- `docs/reference/manifest.md`: the image input keys, the anomaly output keys, `conv2d` and
  `autoencoder` parameters.
- `docs/reference/rules.md`: CF-18, CF-19, DS-16, DS-17, Q-6, the extended CF-6, CF-14, CF-16, Q-5.
- `docs/compatibility.md`: templates table, types table (image no longer "not needed yet").
- `docs/roadmap.md`: the three items delivered; `smallcnn` renamed and delivered as `conv2d`;
  recurrent template recorded as a candidate not built, with the reason.
- `docs/manifest-changes.md`: the additions under `caravan/v0.2`.
- `docs/research/2026-10-23-mcu-ml-landscape.md`: one line under Part A on the 38.6K figure.

## Project Structure

### Documentation (this feature)

```text
specs/010-application-templates/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R14, the measurements
├── data-model.md        # manifest keys, artifacts, contract v3
├── quickstart.md        # runnable validation
├── contracts/
│   └── rules.md         # new and extended rules, listing summaries
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/caravan/
├── templates/
│   ├── registry.py            # + output_types, takes_images, plane_fit
│   ├── conv2d.py              # new: parameter half, plane_fit
│   ├── autoencoder.py         # new: parameter half
│   ├── plane.py               # new: two-axis walk over sequence.py's arithmetic
│   └── builders/
│       ├── conv2d.py          # new
│       ├── autoencoder.py     # new
│       ├── preprocessing.py   # + ReconstructionError
│       └── frontend.py        # image branch, anomaly head
├── manifest/
│   ├── schema/features.py     # image, anomaly; keys per type
│   ├── schema/__init__.py     # CF-6 two axes, CF-14, CF-16, CF-18, CF-19
│   ├── resolve.py             # defaults of the new keys
│   └── errors.py              # CF-18, CF-19, DS-16, DS-17, Q-6
├── data/
│   ├── fingerprint.py         # image files in the version
│   ├── reader.py              # image column as text
│   ├── images.py              # new, train extra: decode, convert, resize
│   ├── fit.py                 # fit_image, fit_output_anomaly
│   ├── reader_bridge.py       # image arrays, anomaly targets
│   └── test_part.py           # anomaly: labels for the split
├── metrics/anomaly.py         # new: auc, percentile, detection
├── stages/{data,build,fit,train,quantize,export}.py
├── convert/tflite.py          # uint8 image input
├── runtime/inspect.py         # uint8 at the input boundary
└── export/{interface,methods,test_windows}.py

tests/
├── fixtures/datasets/{frames,anomaly,images}/   # new, with make.py
├── fixtures/manifests/invalid/                   # cf-18, cf-19 (three), cf-6 columns
├── unit/                                         # plane walk, auc, rules, fingerprint, fit
├── train/                                        # builders, reference shapes, end to end
└── verify/                                       # uint8 runtime feed
examples/{anomaly-autoencoder,frames-conv2d,images-conv2d}.yaml
docs/applications.md (new) and the pages listed above
```

**Structure Decision**: the existing single-package layout; every addition goes where its kind
already lives.

## Complexity Tracking

None. No principle is bent.
