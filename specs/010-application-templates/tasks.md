# Tasks: Templates for the Application Classes

**Input**: Design documents from `/specs/010-application-templates/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/rules.md, quickstart.md

**Tests**: included. The spec's success criteria are stated as assertions (SC-002 to SC-015), and
the project requires a fixture per rule and an end-to-end run per stage change.

**Organization**: by user story. US1 (anomaly) and US2 (conv2d) are both P1 and independent of
each other; US3 (images) builds on US2's template.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (fixtures)

- [X] T001 [P] Write the generator and commit the `frames` fixture in `tests/fixtures/datasets/frames/make.py` and `records.csv`: three classes (`ridge_diag`, `ridge_row`, `ridge_col`) of 12 × 8 planes, one record per frame (12 records per sample, columns `c0`–`c7` as numbers, `label`), seeded noise, about 150 samples per class, standard library only (research R13)
- [X] T002 [P] Write the generator and commit the `anomaly` fixture in `tests/fixtures/datasets/anomaly/make.py` and `records.csv`: windows of 5 records × 8 number columns (`m0`–`m7`), a `condition` column `normal` or `fault`, normal from a 2-dimensional pattern plus noise, `fault` with three columns shifted, about 15 % fault windows, records of one window share the condition
- [X] T003 [P] Write the generator and commit the `images` fixture in `tests/fixtures/datasets/images/make.py`, `labels.csv` and `img/*.png`: 16 × 16 RGB PNG files written with `zlib` and `struct`, three classes (`square`, `bar`, `cross`) on noise, about 60 per class, `labels.csv` with columns `image` (relative path) and `label`

---

## Phase 2: Foundational (blocking)

- [X] T004 Add `output_types` (default `("category", "binary", "number")`), `takes_images` (default `False`) and `plane_fit` (default `None`) to `TemplateParameterSpec` in `src/caravan/templates/registry.py`
- [X] T005 Add rule identifiers CF-18, CF-19, DS-16, DS-17, Q-6 with their one-line meanings in `src/caravan/manifest/errors.py`
- [X] T006 [P] Implement `auc(normal, abnormal)` (ranks, ties averaged, `None` when a side is empty), `percentile(values, p)` (linear interpolation) and `detection(normal, abnormal, threshold)` in `src/caravan/metrics/anomaly.py`, standard library only, with tests in `tests/unit/test_metrics_anomaly.py` (known small cases, ties, empty side)
- [X] T007 [P] Add `uint8` to `BOUNDARY_INPUT_DTYPES` in `src/caravan/runtime/inspect.py`; add `"SQUARED_DIFFERENCE": "AddSquaredDifference"` (read 2026-10-29) in `src/caravan/export/methods.py`
- [X] T008 Add `image` to `INPUT_TYPES` and `anomaly` to `OUTPUT_TYPES` with their keys in `src/caravan/manifest/schema/features.py`: input keys `height`, `width` (int > 0), `num_channels` (1 or 3), `resize_method` (`interpolate` | `crop_or_pad`) apply to image only, and `missing_value_strategy`/`fill_value` do not apply to image; output keys `preprocessing.normal_label` (non-empty text), `threshold_percentile` (0 < x < 100), `auc_drop_max` (0 ≤ x ≤ 1) apply to anomaly only
- [X] T009 Extend validation in `src/caravan/manifest/schema/__init__.py`: CF-16 (`auc_drop_max` for anomaly, the others refused on it and it on the others), CF-18 (template's `output_types`), CF-19 (image the only input; no window with an image; template `takes_images`), the window rule skips CF-6's "window required" when the input is an image; resolve the defaults (`normal_label: normal`, `threshold_percentile: 95`, `resize_method: interpolate`, image sizes `derived`) in `src/caravan/manifest/resolve.py`
- [X] T010 [P] Add invalid fixtures with expected findings in `tests/fixtures/manifests/invalid/`: `cf-18-template-output.yaml`, `cf-19-image-beside-input.yaml`, `cf-19-image-with-window.yaml`, `cf-19-image-template.yaml`, `cf-16-auc-on-category.yaml`, each with its `.expected.json`

**Checkpoint**: the foundation validates new manifests and refuses the new combinations.

---

## Phase 3: User Story 1 — Detect anomalies from normal data alone (P1) 🎯 MVP

**Goal**: an `autoencoder` template and an `anomaly` output, from manifest to export, the score
computed in the model.

**Independent test**: `examples/anomaly-autoencoder.yaml` runs from validation to export on the
`anomaly` fixture; the gate passes; with the int8 model's scores reversed at the measurement seam, the run fails at Q-4 (on the fixture int8 loses nothing, so a zero budget alone would pass).

- [X] T011 [P] [US1] Write the parameter half `src/caravan/templates/autoencoder.py`: `encoder` (list of int > 0, min one), `code` (int > 0), `decoder` (list of int > 0, default the encoder reversed), `dropout` (0 ≤ x < 1, default 0); `output_types=("anomaly",)`, `consumes_window=True`, summary per contracts/rules.md
- [X] T012 [P] [US1] Add the registered `ReconstructionError` layer (mean squared difference over all non-batch axes, reduced dimension kept, shape (batch, 1)) in `src/caravan/templates/builders/preprocessing.py`
- [X] T013 [US1] Write the builder `src/caravan/templates/builders/autoencoder.py` (Flatten, encoder Dense+ReLU, Dense(code) linear, decoder Dense+ReLU, Dense(prod(shape)), Reshape(shape); dropout only when > 0) and the anomaly head in `src/caravan/templates/builders/frontend.py` (body applied whole, score from body output and preprocessed tensor, output keyed by the output's name)
- [X] T014 [US1] Fit and targets in `src/caravan/data/fit.py`, `src/caravan/data/reader_bridge.py`, `src/caravan/data/test_part.py` and `src/caravan/stages/data.py`: `fit_output_anomaly` (normal label present else DS-16 naming the values found; counts per value; abnormal labels), targets 0/1, input features fitted on **normal** training windows, DS-16 when the training part has no normal window
- [X] T015 [US1] Train in `src/caravan/stages/train.py`: for anomaly, train and validate on normal windows only, targets zeros, loss `mean_absolute_error`; metrics per split `auc`, `normal_windows`, `abnormal_windows`, `score_mean_normal`, `score_mean_abnormal`; record `training_windows`, the windows training learned from (all outputs; the normal ones for anomaly)
- [X] T016 [US1] Quantize in `src/caravan/stages/quantize.py`: read `output_features[0].auc_drop_max?` and `threshold_percentile?`; gate metric `auc` (converted − quantized, Q-5 when a side is empty); threshold = percentile of int8 scores of validation normal windows; `detection` rates on the test part; calibration unchanged (all training-part windows, research R9)
- [X] T017 [US1] Export in `src/caravan/export/interface.py`, `src/caravan/stages/export.py` and `src/caravan/export/test_windows.py`: contract version 3; anomaly output entry (`decision: threshold`, `threshold`, `abnormal_when`, `normal_label`, `score`); header threshold constant; test windows round-robin over normal/abnormal, decision `score >= threshold`
- [X] T018 [US1] Add `examples/anomaly-autoencoder.yaml` on the `anomaly` fixture (encoder [32, 16], code 4, window 5, `auc_drop_max: 0.05`, all three boards)
- [X] T019 [P] [US1] Unit tests in `tests/unit/test_autoencoder_template.py`: parameter validation, decoder default, CF-18 both ways, CF-16 for anomaly
- [X] T020 [US1] Train tests in `tests/train/test_anomaly_pipeline.py`: `hum-fan`'s architecture has 35,280 parameters (SC-003); the example runs end to end with the gate passing, reports AUC float/int8 and the drop (SC-004); the exported contract gives the decision from one comparison (SC-005); a lost separation (injected at the measurement seam) fails Q-4 with no model; no normal window → DS-16; operators all have resolver methods and coverage verdicts

**Checkpoint**: US1 complete and testable alone.

---

## Phase 4: User Story 2 — Classify a plane of feature frames (P1)

**Goal**: a `conv2d` template over a window seen as rows × columns.

**Independent test**: `examples/frames-conv2d.yaml` runs end to end on the `frames` fixture.

- [X] T021 [P] [US2] Write `src/caravan/templates/plane.py`: walk a plane's rows and columns through blocks with per-axis kernel, stride, padding and pool over `sequence.py`'s arithmetic; report the axis, block and size left; the smallest fitting size per axis
- [X] T022 [US2] Write the parameter half `src/caravan/templates/conv2d.py`: blocks of `kind` (`standard` | `separable`, default `standard`), `filters` (int > 0), `kernel` (int > 0 or [rows, columns]), `stride` (default 1), `padding` (`valid` | `same`, default `valid`), `normalise` (default false), `pool` (null, int or pair), `dropout` (0 ≤ x < 1); `head` (`average` | `flatten`, default `average`); `takes_images=True`; `plane_fit` with either axis possibly unknown
- [X] T023 [US2] Call `plane_fit` in CF-6 at validation with the axes known from the manifest (rows = window; columns = sum of known channel counts) in `src/caravan/manifest/schema/__init__.py`, and again at build with the built input shape in `src/caravan/stages/build.py`
- [X] T024 [US2] Write the builder `src/caravan/templates/builders/conv2d.py`: reshape a 2-D input to (rows, columns, 1); per block Conv2D or DepthwiseConv2D + 1×1 Conv2D, BatchNormalization before each ReLU when `normalise`, MaxPooling2D, Dropout; head AveragePooling2D over the remaining plane + Flatten, or Flatten; Dense softmax
- [X] T025 [US2] Count DepthwiseConv2D as a convolution in `src/caravan/stages/fit.py` (research R4)
- [X] T026 [US2] Add `examples/frames-conv2d.yaml` on the `frames` fixture (window 12, a standard block and a separable block, average head)
- [X] T027 [P] [US2] Unit tests in `tests/unit/test_conv2d_template.py` and `tests/unit/test_plane.py`: parameter refusals named per block, the plane walk on both axes, CF-6 on the columns axis (and an invalid fixture `cf-6-columns.yaml`)
- [X] T028 [US2] Train tests in `tests/train/test_conv2d_pipeline.py`: the example end to end with the gate passing; the MLPerf KWS reference at 49 × 10 × 12 labels has 24,908 parameters (SC-006); every operator mapped and covered (SC-007); depthwise weights counted by the fit stage

**Checkpoint**: US1 and US2 both work independently.

---

## Phase 5: User Story 3 — Classify images (P2)

**Goal**: an `image` input type feeding `conv2d`, raw uint8 pixels on the device.

**Independent test**: `examples/images-conv2d.yaml` runs end to end on the `images` fixture.

- [X] T029 [US3] Fingerprint the image files in `src/caravan/data/fingerprint.py`: `resolve_dataset(..., image_columns=())` reads the tables with `csv`, collects the named files, refuses missing or outside-the-root files with DS-1 naming record and file, hashes them sorted; pass the image columns from wherever `resolve_dataset` is called
- [X] T030 [US3] Write `src/caravan/data/images.py` (train extra): decode PNG/JPEG/BMP/GIF with `tf.io.decode_image(expand_animations=False)`, convert channels, resize (`interpolate` bilinear, `crop_or_pad`), round and clip to 0–255; inspect sizes; DS-17 for unreadable files, unsupported formats and disagreeing sizes with none stated
- [X] T031 [US3] Read an image column as text in `src/caravan/data/reader.py`; `fit_image` in `src/caravan/data/fit.py` and the data stage (stated or taken sizes, counts of resized and converted, formats); image arrays (samples, h, w, c) float32 in `src/caravan/data/reader_bridge.py`; window `None` for image models
- [X] T032 [US3] Image branch of the front-end in `src/caravan/templates/builders/frontend.py`: input (h, w, c) float32 named after the feature, `Rescaling(1/255)`, body given (h, w, c)
- [X] T033 [US3] Conversion in `src/caravan/convert/tflite.py` and `src/caravan/stages/quantize.py`: `inference_input_type=uint8` when the model has an image input; calibration prepended with one black and one white frame, recorded as `bounds_frames: 2`; Q-6 when the file's image input is not scale 1, zero point 0
- [X] T034 [US3] Image input bytes in the fit check (1 byte per element) in `src/caravan/stages/fit.py` and `src/caravan/targets/fit.py`
- [X] T035 [US3] Export: image input entry (`height`, `width`, `num_channels`, `channel_order`, `layout`, `frame`) and `window_size: null` in `src/caravan/export/interface.py`; `uint8_t` test windows in `src/caravan/export/test_windows.py`; uint8 feed in `src/caravan/runtime/measure.py` if needed
- [X] T036 [US3] Add `examples/images-conv2d.yaml` on the `images` fixture (sizes taken from the data, two blocks, average head)
- [X] T037 [P] [US3] Unit tests in `tests/unit/test_image_fingerprint.py`: a changed image changes the version, an unchanged one does not (SC-015); missing and outside files refused with record and file (SC-014)
- [X] T038 [US3] Train tests in `tests/train/test_image_pipeline.py`: the example end to end with the gate passing (SC-012); the input is uint8 scale 1 zero point 0; JPEG read (encoded at test time); disagreeing sizes refused (DS-17); MobileNetV1 0.25 at 96 × 96 × 3 builds with Keras's 219,058 plus its convolution biases (SC-013); an image counted at one byte per pixel fits where floats would not, and a 160 × 160 × 3 image is refused before training (F-1). The spec first expected the VWW reference itself to be refused on `s32k144`; measured, its floors are below the board, and SC-013 was corrected (research R5)

**Checkpoint**: all three additions work.

---

## Phase 6: User Story 4 — See which application each template serves (P2)

- [X] T039 [P] [US4] Write `docs/applications.md`: the twelve classes, the template and types serving each, the example manifest, or the reason none serves it; add it to the site index in `docs/index.md`
- [X] T040 [P] [US4] Document the new keys, templates and rules in `docs/reference/manifest.md` and `docs/reference/rules.md`
- [X] T041 [P] [US4] Update `docs/compatibility.md` (templates, types), `docs/roadmap.md` (delivered items, `smallcnn` → `conv2d`, recurrent template not built and why), `docs/manifest-changes.md` (additions under `caravan/v0.2`), and the line on the 38.6K figure in `docs/research/2026-10-23-mcu-ml-landscape.md`

---

## Phase 7: User Story 5 — Add templates without touching the core (P3)

- [X] T042 [US5] Tests in `tests/layering/` and `tests/unit/`: the new core modules import no framework; `caravan templates` lists four with their summaries; no stage source contains a template identifier literal (SC-009, SC-010)

---

## Phase 8: Polish

- [X] T043 Run the whole suite, `ruff check` and `ruff format --check`; fix what they find
- [X] T044 Check the docs tests (`tests/` doc-sync tests) against the new pages and examples; update README's status line (four templates)

---

## Dependencies

- Phase 1 and Phase 2 before the stories; T004 before T011/T022; T008–T009 before T014 and T031.
- US1 and US2 are independent. US3 needs US2 (the template that takes images).
- US4 and US5 after the stories they describe.

## Parallel examples

- Setup: T001, T002, T003 together.
- Foundation: T006 and T007 beside T004–T005.
- US1: T011 and T012 together, then T013.
- US2: T021 beside US1's work; T027 beside T024.

## Implementation strategy

MVP is US1: `hum-fan` is the named model, and it alone makes the anomaly class buildable. US2 adds
keyword spotting; US3 adds images on top of US2. One pull request when all are built and the local
validation has passed (constitution, Resources & Cost Discipline).
