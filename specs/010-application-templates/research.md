# Research: Templates for the Application Classes

Feature 010. Measured on 2026-10-29 with TensorFlow 2.21.0, Keras 3, ai-edge-litert 2.3 and
Caravan's own converter (`caravan.convert.tflite`, batch fixed to one) and readers
(`caravan.runtime.inspect`, `caravan.runtime.flatbuffer`). The scripts are not committed; what they
established is recorded here, and the tests of this feature assert the parts that can regress.

## R1. The keyword-spotting reference, and the figure in the research note

**Decision**: the two-dimensional template's keyword-spotting check (SC-006) uses the MLPerf Tiny
reference as its code defines it, read on 2026-10-29 from
`mlcommons/tiny`, `benchmark/training/keyword_spotting/keras_model.py`, function `ds_cnn`: input
49 × 10 × 1; a convolution of 64 filters, kernel (10, 4), stride (2, 2), `same`, normalisation,
ReLU; four blocks of a 3 × 3 depthwise convolution (`same`), normalisation, ReLU, a 1 × 1 convolution
of 64 filters, normalisation, ReLU; average pooling over the whole remaining plane; flatten; dense
softmax over 12 labels. Convolutions keep their bias.

**Measured**: 24,908 parameters, normalisation statistics included (hand count:
2,624 + 256 + 4 × (640 + 256 + 4,160 + 256) + 780 = 24,908); 43,048 bytes as int8; operators
QUANTIZE, CONV_2D × 5, DEPTHWISE_CONV_2D × 4, AVERAGE_POOL_2D, FULLY_CONNECTED, SOFTMAX, DEQUANTIZE;
computed working-memory floor 16,000 bytes.

**Recorded honestly**: the research note of 2026-10-23 (Part A) gives "DS-CNN, 38.6K parameters,
52.5 KB". The MLPerf code does not produce that parameter count. Where 38.6K comes from was not
re-checked; the DS-CNN of "Hello Edge" (Zhang et al., 2017), from which the MLPerf reference
derives, is the likely source, and whether the figure counts parameters or bytes there is open. The
note gets a line under Part A saying so (FR-001's table cites the measured count), not a silent
change.

**Alternatives**: checking against 38.6K — rejected, it is not the architecture the benchmark ships.

## R2. The head of the two-dimensional template

**Decision**: `average` is built as average pooling over the whole plane followed by a flatten,
not as a global average.

**Measured** on the R1 architecture: the global average converts to `MEAN`, the full-plane pooling
to `AVERAGE_POOL_2D`; parameters and bytes are equal (43,016 against 43,048 bytes). `MEAN` has no
accelerated kernel in either built-in library; `AVERAGE_POOL_2D` has one in both (`cmsis-nn` and
`esp-nn`, `pooling.cc`, read 2026-10-22). So the same head is accelerated everywhere, which
`conv1d`'s reduction is not. It is also exactly what the MLPerf reference does.

`flatten` stays the second choice, as in `conv1d`.

## R3. The plane: a window, or an image

**Decision**: the template convolves a plane with channels. From a window, the plane is the window's
rows by the input columns with one channel, reached by one reshape in the model; from an image, it is
the image with its channels, no reshape.

**Measured**: a window of 49 × 10 reshaped to 49 × 10 × 1 converts to RESHAPE and the convolution,
nothing else (two RESHAPE nodes, one from the batch fix). Both are mapped resolver methods.

**The fit check needs both axes.** `conv1d` checks the window against its blocks
(`caravan.templates.sequence.walk`). The two-dimensional template walks each axis separately with
the same arithmetic — kernel, stride, padding and pooling per axis — because the formulas are
separable. At validation, the row axis is the window (or a stated image height) and the column axis
is known when every input's channel count is: one for `number` and `binary`, the embedding size for a
`dense` category, the pinned vocabulary plus one for a `onehot` category; an image's width when
stated. An axis not yet known is checked by the build stage, before training, with the same rule
and message (CF-6).

## R4. Separable blocks, normalisation and bias

**Decision**: a block of kind `separable` is a depthwise convolution with the block's kernel and
stride, then a 1 × 1 convolution with the block's filters, each followed by its optional
normalisation and a ReLU — the DS-CNN and MobileNetV1 pattern. Convolutions keep their bias, as in
`conv1d` and in the MLPerf keyword-spotting code.

**Why the bias stays**: normalisation folds into the convolution together with its bias (feature
005 measured the fold), so the converted file is the same either way; what changes is the
parameter count Keras reports. Keeping it makes the R1 reference match exactly and keeps the two
convolutional templates alike. The Keras MobileNet reference drops the bias, so SC-013 compares
against its count plus the number of convolution bias terms, computed in the test.

**Measured** (R1): every operator a separable block produces — DEPTHWISE_CONV_2D, CONV_2D — has an
accelerated kernel in both built-in libraries and a resolver method.

**Keras 3 detail**: `DepthwiseConv2D` is not a subclass of `Conv2D`, so the fit stage's layer
records would count it as excluded and lose its weights and its activation memory. The fit stage
learns it (checked in `stages/fit.py`; a test asserts a separable block's weights are counted).

## R5. The Visual Wake Words reference

**Decision**: SC-013 uses MobileNetV1 at width 0.25, 96 × 96 × 3, two labels, as Keras ships it
(`keras.applications.MobileNet(alpha=0.25, input_shape=(96, 96, 3), classes=2, weights=None)`),
which is the MLPerf Tiny VWW reference architecture.

**Measured**: Keras counts 219,058 parameters. The template expresses it as a standard 3 × 3
convolution of 8 filters at stride 2 and thirteen separable blocks (pointwise filters 16, 32, 32, 64,
64, 128, 128 × 5, 256, 256; stride 2 at blocks 2, 4, 6 and 12), normalisation in every block, average
head. Its count is 219,058 plus one bias per convolution (R4); the test computes that number from
the block list rather than trusting either side.

## R6. An image reaches the model as raw 8-bit pixels

**Problem measured first.** An 8-bit model input that the model itself casts to float puts a float
copy of the image into the working memory: for 32 × 32 × 3 the floor was 15,360 bytes, of which
12,288 are the float copy; at 96 × 96 × 3 that copy would be 110,592 bytes.

**Decision**: the Keras model takes pixel values as float (0–255) and scales them by 1/255 itself;
the converter is told that the input is `uint8` (`inference_input_type`), and calibration starts with
one black and one white frame before the training samples.

**Measured**:

| Variant | Input as the file states it | Floor (32 × 32 × 3) | Operators before the first convolution |
|---|---|---|---|
| uint8 input, model casts | uint8, no scale | 15,360 | CAST, QUANTIZE |
| converter uint8, calibration spans 0–255 | uint8, scale 1.0, zero point 0 | 6,672 | QUANTIZE |
| converter uint8, calibration spans 10–240 | uint8, **scale 0.941**, zero point 0 | 6,672 | QUANTIZE |
| converter uint8, black and white frames first, then 10–240 | uint8, **scale 1.0, zero point 0** | 6,672 | QUANTIZE |
| converter int8, calibration spans 0–255 | int8, scale 1.0, zero point −128 | 6,672 | none |
| fake-quant layer pinning 0–255 | uint8, scale 1.0 | 15,360 | QUANTIZE, DEQUANTIZE × 2 |

So:
- the input's scale comes from what calibration saw, and real images need not contain a pure black
  and a pure white pixel — without the two frames the device would have to rescale (row 3);
- with them, the scale is exactly 1 and the zero point 0: the firmware passes the camera's bytes;
- the 1/255 scaling folds into the requantization — no MUL remains;
- an `int8` input would save the one QUANTIZE and a copy of the image, at the price of the firmware
  subtracting 128 from every pixel. Owner decision D7 ("dass der Nutzer nicht noch extra Aufwand
  hat") decides it: `uint8`. The int8 figure is recorded so the trade can be revisited if a board
  runs short by exactly one frame.

The quantize stage reads the produced file and refuses the run if an image input's scale is not 1 or
its zero point not 0 (new rule Q-6): the contract's promise of raw pixels is checked, not assumed.

TFLite Micro's `QUANTIZE` accepts uint8 input and int8 output (`kernels/quantize_common.cc`, read
2026-10-29). The `inspect` module's list of boundary input types gains `uint8`; a uint8 input was
otherwise counted as "not fully integer" (row 2 above reported `fully_int=False` for that reason
alone).

The two frames also enter the calibration of every layer after the input. Their effect is what the
accuracy gate measures, like any calibration choice; the record names them.

## R7. Decoding and resizing images

**Decision**: images are decoded and resized with the training framework the `train` extra already
installs (`tf.io.decode_image` with `expand_animations=False`, which reads PNG, JPEG, BMP and the
first frame of GIF; `tf.image.rgb_to_grayscale` and `grayscale_to_rgb`; `tf.image.resize`, bilinear,
for `interpolate`, and `tf.image.resize_with_crop_or_pad` for `crop_or_pad`, Ludwig's two
`resize_method` values). Results are rounded and clipped to 0–255.

**Why there**: reading the data already needs the `train` extra (the reader uses numpy), so no
installation that reads images lacks the framework. No dependency is added (Principle XII).

**Size taken from the data**: when height, width or channels are not stated, every image is read
once and the value is taken if all agree; disagreement is refused with the values found. The data
stage records the values, and the pipeline merges them into the resolved manifest under the
feature's `preprocessing.fitted`, as it does for vocabularies.

**Alternatives**: Pillow — a dependency for something the extra already does; a resize layer in the
model — memory the image already strains, and the camera crops and bins anyway (research note,
Part D).

## R8. The anomaly score inside the model

**Decision**: the autoencoder reconstructs the input *as the model sees it after preprocessing*; a
registered layer computes the mean squared difference between reconstruction and that input, over
the window, and the model's one output is that score.

**Measured** on a synthetic 5 × 40 set (normal: a four-dimensional pattern plus noise; abnormal:
three columns shifted) with `hum-fan`'s architecture:

- **35,280 parameters**, exactly the zoo's hand-built model (`configs/condition-monitoring/
  sound-anomaly/hum-fan.yaml`: encoder 64, 64; code 8; decoder 64, 64; 200 inputs);
- fully integer; 54,040 bytes;
- operators QUANTIZE, MUL, ADD (the standardisation), RESHAPE, FULLY_CONNECTED × 6,
  SQUARED_DIFFERENCE, MEAN, DEQUANTIZE, and a STRIDED_SLICE from indexing the mean into a column —
  avoided by keeping the reduced dimension (the builder reduces with `keepdims`).

`SQUARED_DIFFERENCE` needs a resolver method: `AddSquaredDifference` exists in
`micro_mutable_op_resolver.h` and the kernel accepts int8 (`kernels/squared_difference.cc`), both
read 2026-10-29. Neither built-in accelerated library has it or `MEAN`; coverage records them as
reference fallbacks, as for `conv1d`'s reduction.

**Training without a custom loss**: the score is never negative, so the mean absolute error against
a target of zero *is* the mean score. The model compiles with a stock loss and loads without
special code beyond the registered layer.

## R9. Calibration for anomaly models

**Decision**: calibration draws from every training-part window, normal or not — which is what the
existing calibration plan already does (`plan_calibration` over `split.train`). Only *training*
uses normal windows alone.

**Measured** with the R8 model:

| Calibrated on | Largest abnormal score | Distinct int8 scores | AUC float → int8 |
|---|---|---|---|
| normal training windows only | 0.035 (= the largest normal one: **saturated**) | 96 | 0.9803 → 0.9738 |
| all training-part windows | 0.330 | 153 | 0.9803 → 0.9788 |

Calibrating on normals alone clips every abnormal score to the top of the normal range: the
ranking survives only where an abnormal window happens to land below that ceiling. With all
windows the score keeps its range, and the drop is a quarter.

The input preprocessing (shift and scale) is fitted on **normal** training windows: that is what
the model learns as normal, and an abnormal outlier should not move the normalisation.

## R10. Separation, threshold, gate

**Separation**: the area under the ROC curve, abnormal as the positive class — the measure of MLPerf
Tiny's anomaly task and of DCASE Task 2. Computed by Caravan from ranks (the Mann–Whitney form, ties
given their average rank): about twenty lines of standard library in `caravan.metrics`, no new
dependency.

**Gate**: `auc_drop_max`, the AUC lost from the converted float model to the int8 model, judged
like `accuracy_drop_max` (rounded to six decimals, `<=` passes). An empty normal or abnormal side in
the test part makes the AUC undefined, so the gate cannot decide and the run fails (Q-5).

**Threshold**: the 95th percentile of the int8 model's scores on the validation part's normal
windows (`hum-fan` uses the 95th; MLPerf leaves the threshold to the user). Computed in the quantize
stage, because the device runs the int8 model and a threshold from the float model's scores would be
on a different scale. The author may state `threshold_percentile`. The threshold is recorded in
`quantization.json` and the interface contract; the detection rate and the false-alarm rate on the
test part at that threshold are reported beside the AUC.

**Labels**: the output names the condition column; `preprocessing.normal_label` says which value is
normal, default `normal` (the spelling of MIMII and of DCASE). A value not present in the data is
refused, naming the values found. Every other value is abnormal; counts are reported per value.

## R11. The dataset fingerprint covers the images

**Decision**: when an input is an image, `resolve_dataset` also hashes every file the image column
names, in sorted order, after the tables. It reads the tables with the standard library's `csv`, so
the cache still works without the framework. A named file that does not exist, or resolves outside
the dataset directory, is refused there (DS-1), which is the earliest point the run can know.

Image directories beside the tables are already ignored by the table discovery, because they hold no
`.csv`, `.tsv` or `.txt` file (`_holds_data`).

## R12. Combinations, and where they are refused

| Combination | Rule | Why |
|---|---|---|
| a template that cannot serve the output type (`autoencoder` with `category`; `mlp` with `anomaly`) | **CF-18** (new) | a template declares the output types it serves |
| an image input beside other inputs | **CF-19** (new) | one plane per model; several inputs with an image are out of scope |
| an image input with `preprocessing.window_size` | **CF-19** | a record is one sample |
| an image input with a template that does not take images | **CF-19** | a template declares whether it does |
| a window too short, or too few columns, for a two-dimensional configuration | CF-6 | the existing rule, extended to the second axis |
| a stated image size too small for the configuration | CF-6 | the same arithmetic |
| no normal window in the training part | **DS-16** (new) | nothing to learn as normal |
| an image file missing, unreadable, outside the dataset, in a format not read | **DS-17** (new), or DS-1 at fingerprinting | the record and the file are named |
| images of different sizes with no size stated | **DS-17** | the values found are named |
| an image input whose int8 scale is not 1 or zero point not 0 | **Q-6** (new) | the contract's raw-pixel promise is checked |

The template states what it serves (`output_types`, `takes_images`) as two new fields of the
parameter spec, with defaults that keep `mlp` and `conv1d` as they are; no stage branches on a
template identifier (FR-030).

## R13. Fixtures

Three synthetic datasets, generated deterministically by committed scripts, as `synthetic` is:

- `frames`: three classes of 12 × 8 planes with class-dependent diagonal, horizontal and vertical
  ridges plus noise, one record per frame, eight `number` columns;
- `anomaly`: 5 × 8 windows, normal from a low-dimensional pattern with noise, abnormal with shifted
  columns, a `condition` column (`normal`, `fault`), roughly 15 % abnormal;
- `images`: 16 × 16 RGB PNG files of three classes (a filled square, a horizontal bar, a cross on
  noise), a `labels.csv` naming file and class. Written with `zlib` and `struct`, so the generator
  needs nothing but the standard library. JPEG reading is tested by encoding at test time with the
  framework, so no JPEG file is committed.

## R14. Schema version

Adding an input type, an output type, two templates and five keys changes the meaning of no manifest
that was valid before. Principle IX asks for a new version on a *breaking* change; this is not one,
so the schema stays `caravan/v0.2`. An older build refuses the new types and templates with CF-14
and T-1, which is the behaviour Principle IX wants. `docs/manifest-changes.md` records the additions.
