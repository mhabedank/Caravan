# Research: Typed Features, Ludwig-Style

The conditions and limits come from `docs/research/2026-10-24-typed-features-on-mcu.md` (TFLM
kernels at `f7ed40d`, converter probes, Ludwig at `0e84ffa`). This document holds the decisions that
follow from it, and the spike that tested the core of the design.

Measured on 2026-10-24 with Python 3.13.16, TensorFlow 2.21.0, Keras 3.15.1 and ai-edge-litert. The
spike scripts are in `spikes/`, to be run from the repository root.

## R1. The manifest in Ludwig's names

**Decision.** Schema version `caravan/v0.2`:

| Caravan `v0.1` | Caravan `v0.2` | Ludwig |
|---|---|---|
| `inputs[0]` (a tensor with derived columns) | `input_features: [{name, type, preprocessing, encoder}]`, one per column | same |
| `outputs[0]` | `output_features: [{name, type, preprocessing, …}]`, exactly one | same (Ludwig allows several) |
| `inputs[0].window` | `preprocessing.window_size` | `window_size` exists per timeseries feature; here it applies to all rows |
| `dataset.split` (fractions, `stratified`, `column`) | `preprocessing.split: {type: random\|stratify\|fixed, probabilities, column}` | same |
| — | `defaults: {<type>: {preprocessing: …, encoder: …}}` | same |
| `train.epochs` | `trainer.epochs` | same |
| `train.batch` | `trainer.batch_size` | same |
| `train.learning_rate` | `trainer.learning_rate` | same |
| `train.optimizer` | `trainer.optimizer: {type: adam}` | same |
| `train.early_stopping` + `patience` | `trainer.early_stop` (patience; −1 disables) | same |
| `train.seed` | `random_seed` (top level) | Ludwig's API and CLI name |
| `dataset.source` | `dataset` (path) | Ludwig takes it on the command line; Caravan keeps it in the manifest |
| `dataset.representative_samples` | `export.representative_samples` | none; it belongs to quantization |
| `model.{name, version, template, params}` | unchanged | none; a microcontroller architecture is Caravan's own |
| `export.{quantization, formats, targets}` | unchanged | none |
| `outputs[0].accuracy_drop_max` | `output_features[0].accuracy_drop_max`, or `mae_increase_max` for `number` | none; Principle V |

**Rationale.** It is owner decision 2026-10-24: Ludwig's names wherever Ludwig has the concept.
Caravan keeps its own only where Ludwig has nothing. Every exception gets a line in the change note
(SC-002).

**Alternatives considered.**
- *The architecture as Ludwig's `combiner`.* Rejected by the owner. A Ludwig combiner merges
  encoder outputs; Caravan's template is the whole network.
- *Keeping `inputs`/`outputs`.* Rejected: it is what confused the owner.

## R2. One input per feature, with the element type the device has

**Decision.** Each input feature is its own model input of shape (window_size,) per sample, after
the batch of 1 is fixed. The element type depends on the feature type:
- `number`: float32. The converter puts a QUANTIZE at the front, with that feature's own scale.
- `category` and `binary`: int32. The input stays int32 through conversion.

The conversion leaves `inference_input_type` unset, so each input keeps its own type.

**Measured** (spike `spike_typed.py`, synthetic fixture, labels **derived**, the case that fails
the int8 gate today):
- Trained 1.000, int8 1.000 on the 12 test windows. Feature 006 R11 measured 0.75 and 0.50 on the
  same split with the current form.
- The input dtypes after conversion: `can_id` int32, `dlc`/`b0`/`b1`/`b2` float32.
- Operators: CAST, CONCATENATION, DEQUANTIZE, EQUAL, FULLY_CONNECTED, MUL, QUANTIZE, RESHAPE,
  SOFTMAX, SUB, SUM. All are in TFLM.

**Rationale.** One quantisation scale per input tensor is what crushed mixed-range columns (note,
section 3). Codes must stay integers to be compared exactly (note, section 2).

## R3. The preprocessing layers

**Decision.** Three registered custom Keras layers, in `caravan.templates.builders.preprocessing`
(train extra):
- **`Standardize(shift, scale)`** for `number`: `(x − shift) / scale`, giving one channel. zscore,
  minmax and iq differ only in the two constants, fitted on the training part.
- **`VocabularyOneHot(vocab)`** for `category`: `EQUAL` of the int32 code against the constant
  vocabulary, `CAST` to float, and an "unknown" slot `1 − SUM` at index 0, giving V+1 channels.
- **`AsChannel`** for `binary`: `CAST` int32 → float, giving one channel.

The `dense` encoder is a `Dense(embedding_size, use_bias=False)` on the one-hot. That is an
embedding computed as a matrix product, so it lowers to FULLY_CONNECTED, which CMSIS-NN and ESP-NN
accelerate. It avoids GATHER and the SELECT v1 that Keras `Embedding` produces. The channels are
concatenated, giving (window_size, channels), and the template body follows unchanged.

**Rationale.** These are exactly the operators the probes found convertible and present in TFLM.
No `Lambda` is used (it breaks `fix_batch`), and no Keras lookup or encoding layer
(`IntegerLookup`, `StringLookup`, `CategoryEncoding`, `Embedding`; note, section 2).

**Found during implementation (2026-10-24, TF 2.21.0).** The converter does not quantize the
output of a CAST. Written as above, the one-hot's SUM, SUB and CONCATENATION stayed float32, and
where a CAST fed the concatenation of all features directly (a `binary` input, a `onehot` encoder)
the converter even dequantized the other features to concatenate in float. A RELU right after the
CAST — the identity on 0 and 1 — is where the converter inserts its QUANTIZE: the only float32
tensor of the branch is then the CAST's output, consumed by that QUANTIZE, and everything after it
is int8. Measured on a probe with every code of a vocabulary and four unseen ones: the converted
one-hot is exact (largest error 0). The quantize stage's integer check accordingly allows a float32
tensor only at the model's boundary or where every consumer is a QUANTIZE (R5).

## R4. Encoder default for `category`, and its size

**Measured** (spike `spike_embedding.py` and `spike_typed.py`, same split, `can_id` with a
vocabulary of 32):

| Encoder | Trained | int8 | Model file |
|---|---|---|---|
| `onehot` (33 channels per step) | 1.000 | 1.000 | 87,080 B |
| `dense`, `embedding_size` 8 | 1.000 | 1.000 | 36,568 B |
| `dense`, `embedding_size` 4 | 1.000 | 1.000 | **28,192 B** |

**Decision.** The default encoder is `dense`, as in Ludwig. `embedding_size` defaults to
`min(vocab size, 4)` (spec, Assumptions).

**Note.** The typed pilot is about twice the size of today's pilot (14,856 B). The categorical
column now carries information it did not before: the numeric `can_id` was meaningless as a
magnitude. That size is stated, not hidden; the release note will compare.

## R5. Output types and the model's boundary

**Decision.** The model's outputs are float32 (the converter's DEQUANTIZE at the end), so the
firmware applies no scale and zero point:
- **`category`**: softmax over the labels. The decision is the arg-max.
- **`binary`**: one sigmoid unit. The decision is `score ≥ threshold` (default 0.5).
- **`number`**: one linear unit. An optional output `normalization` (default `null`, as in Ludwig)
  is fitted on the training part and inverted inside the model. An optional `clip: [lo, hi]` bounds
  it (MAXIMUM/MINIMUM).

The boundaries change, and so does what "fully quantized" means (feature 003): every tensor
between the input conversions and the output conversion must be int8 or int32. The inputs are
float32 or int32, followed by QUANTIZE for float. The outputs come after a DEQUANTIZE. The quantize
stage's inspection checks exactly this.

**The int8 gate per type**, measured on the test part:
- `category` and `binary`: accuracy lost to quantization ≤ `accuracy_drop_max`.
- `number`: the increase of the mean absolute error ≤ `mae_increase_max`, in the column's unit.

The per-layer error table works unchanged: it compares tensors, not metrics.

**Training per type**, in Ludwig's names:
- `category`: sparse categorical cross-entropy, optional `class_weights`.
- `binary`: binary cross-entropy, optional `positive_class_weight`.
- `number`: `loss: {type: mean_squared_error | mean_absolute_error | huber}`.

**Metrics:**
- `category`: accuracy, precision/recall/F1 macro and per class (as today).
- `binary`: accuracy, precision, recall, F1.
- `number`: MAE, MSE, RMSE, R², in a new standard-library module `caravan.metrics.regression`
  (core, like the classification one).

## R6. Fitting on the training part, once

**Decision.** The `data` stage now does four things:
1. reads the typed columns;
2. cuts the windows;
3. splits them (it reads `preprocessing.window_size`, `preprocessing.split` and `random_seed`);
4. fits each feature's preprocessing on the **training part only** and writes it to
   `data/preprocessing.json`: shift and scale, vocabulary with frequencies, binary spellings,
   output normalisation, and what was cut by `most_common`.

`build`, `train` and `quantize` read the fitted values from the merged resolved manifest, the way
feature 006 merges derived labels, so the fitted values are part of their cache keys. `train` and
`quantize` recompute the same split with the same function, as today.

**Rationale.** It differs from Ludwig on purpose: Ludwig fits on all parts together, which leaks
the test part into the preprocessing (note, section 5).

## R7. Vocabulary order

**Decision.** Values are ordered by frequency in the training part, descending, with ties broken
by the value's text. This is Ludwig's order, made deterministic.
- **Inputs**: index 0 is always "unknown" and `most_common` (default 32) caps the vocabulary.
- **Outputs**: there is no "unknown". A class that occurs in the data but not in the training part
  stops the run (DS rule), because nothing could learn it.
- **Pinning**: `preprocessing.vocab` pins the order, as `outputs[0].labels` did. For an output, the
  vocabulary is the label order.

## R8. The fixed split's values

**Decision.** `preprocessing.split: {type: fixed, column: split}` accepts, per record, Ludwig's
values `0`, `1`, `2` and the words `train`, `validation`, `test`. `val` (feature 007's spelling)
becomes `validation`, as in Ludwig. The `pace-cnn` converter writes the words.

## R9. Conversion path

**Decision.**
- **`fix_batch`** rebuilds every input with batch 1, keeping each input's dtype and name. It
  refuses `Lambda`. It never relies on adapt-state, because statistics are constructor arguments
  (R3).
- **The representative dataset** yields dicts keyed by input name. A list was silently matched to
  the converter's internal order (note, section 4).
- **`inference_input_type`** is left unset and `inference_output_type` is left float32 (R2, R5).

## R10. The interface contract and the header

**Decision.** Per input:
- name, position (read from the file's signature, as in feature 006), element type (float32 or
  int32), shape (window_size), Caravan type;
- for `category`: the vocabulary and, when the data's values are text, the text→code table the
  device uses;
- for `binary`: the spelling→0/1 table;
- for `number`: the fill value for a missing reading.

Per output: name, type, decision (arg-max, threshold or value), labels. The C header gets one
position constant and one element-type comment per input, the label array, and for `binary` the
threshold. The runner skeleton fills each input by name with raw values (SC-005).

**Missing values on the device.** `missing_value_strategy` fills missing cells of the training data
on the host. A reading cannot be missing inside a fixed-size input tensor. The contract states the
fill value a firmware author passes when a reading is absent. That is the only preprocessing fact
the firmware sees, and it is a constant.

## R11. The fit check

**Decision.** The floors now count:
- **Flash**: every input's preprocessing constants (vocabularies; the embedding counts as a dense
  kernel) as well as the layer weights.
- **RAM**: every input tensor at its element size (4 bytes × window_size for float32 and int32) and
  the concatenated features tensor.

As today, a floor is a lower bound, and F-1 fails only when it exceeds a board.

## R12. Rules

**Retired, reserved:**
- CF-10 (exactly one input): several input features are now allowed, though still exactly one
  output.
- CF-13 as written for `dataset.split.column`: it is re-raised for `preprocessing.split.column`.

**Kept, with new paths:** CF-1 (probabilities sum to 1), CF-6 (window vs template), CF-9 (names),
CF-11 (a column both in and out), CF-12 (fixed split with probabilities).

**New:**
- **CF-14**: a feature type this build does not implement. The message names the implemented types
  and the reason.
- **CF-15**: `stratify` on a column other than the output's. Not implemented: only stratifying by
  the class is.
- **CF-16**: an output type and budget that do not match (for example `mae_increase_max` on a
  `category`).
- **DS-14**: a class of the output occurs outside the training part only.
- **DS-15**: a `binary` column with more than two spellings and no `fallback_true_label`.
- **CF-17**: not exactly one output feature. It takes over the output half of the retired CF-10.

DS-12 (a named column missing from the data) keeps its meaning for features.

## R13. Schema version and change note

**Decision.** `caravan/v0.2`. A `caravan/v0.1` manifest is refused with V-1 and the change note
(constitution 4.0.0). `docs/manifest-changes.md` gains a section with the table of R1 and the
by-hand edit of the pilot.

## R14. What is touched, and what stays

**Touched:**
- the schema and resolver;
- the reader (typed columns: numbers as float, codes as int, text kept as text until mapped);
- the data stage (fitting);
- the build stage (preprocessing front-end, several inputs);
- the train stage (losses per output type);
- the quantize stage (boundaries, dict calibration, gate per type);
- the export (contract, header, runner);
- the fit floors;
- the metrics (regression);
- the fixtures, the example, the `pace-cnn` port and the documents.

**Stays:** the templates' bodies (`mlp`, `conv1d`), the stage cache, the run directory, the gate's
error table, the operator resolver and the kernel coverage.

## R15. Cash budget

None. Local compute and the existing CI runners; no paid service, no key.
