# Typed columns with their preprocessing on a microcontroller — what TFLite Micro allows

Date: 2026-10-24. Prompted by decision D7 (`docs/design/2026-10-23-owner-decisions.md`): inputs and
outputs name their columns Ludwig-style, each with a type, and each type brings its preprocessing,
ideally inside the model on TFLite Micro (TFLM). The owner asked for the conditions and limits
before specifying anything.

Three sources:
- **TFLM's kernels**, read at the commit Caravan pins, `f7ed40df` (2026-10-22). ESP-NN was read at
  `espressif/esp-tflite-micro` `dd40859`.
- **Measurements** of what the converter does with preprocessing inside a Keras model, under
  Caravan's own int8 settings: TF 2.21.0, Keras 3.15.1, ai-edge-litert, untrained models,
  synthetic inputs. The script and its output are in `2026-10-24-typed-features-probes/`.
- **Ludwig's source**, `ludwig-ai/ludwig` `0e84ffa` (2026-09-26), for how each type is processed
  and what is kept after training.

## The short answer

Most of the per-type preprocessing *can* run inside the model on TFLM, but not the way Keras
offers it, and not through one input tensor.

| Need | Inside the model on TFLM? | How |
|---|---|---|
| number: standardise (z-score, min-max) | **yes** | SUB/MUL in the graph. The precision of mixed scales is the catch; see 3 |
| category: raw code → class | **yes, if the code arrives as int32** | compare against the vocabulary as a constant: `EQUAL(int32)` → `CAST(bool→float)`, exact (error 0.0) |
| category: unknown value | **yes** | an extra slot `1 − sum(one-hot)` (SUM, SUB, CONCATENATION) |
| category: embedding | **yes** | a gather on an int8 table (`GATHER`, int32 indices); not Keras `Embedding` |
| binary | **yes** | it is a number, 0 or 1 |
| strings (labels like "walking", "yes") | **no** | TFLM allocates no string tensor; string mapping stays on the host |
| hash-table lookup (`IntegerLookup`, `StringLookup`) | **no** | TFLM has no HASHTABLE ops; full-int8 calibration cannot run Flex ops |
| `ONE_HOT`, `BUCKETIZE`, `SELECT` (v1) | **no** | not in TFLM; each has a builtin workaround (below) |
| int64 anywhere | **no in practice** | CAST, GATHER and ARG_MAX have no int64 path |
| output: class index → name, threshold, inverse scaling | outside the graph, trivially | the label table is already in the C header |

Preprocessing ops run on reference kernels on every board. CMSIS-NN and ESP-NN accelerate only int8
ADD and MUL without broadcast, and CMSIS-NN int8 MAXIMUM/MINIMUM. For a handful of values per time
step that cost is small, and each op lands in the generated operator resolver, as today.

## 1. What TFLM supports (`f7ed40d`)

| Op | Kernel | Types |
|---|---|---|
| QUANTIZE | `quantize_common.cc` | float32 → int8/int16; one scale per tensor |
| DEQUANTIZE | `dequantize_common.cc` | int8/int16/uint8 → float32 |
| CAST | `cast.cc` | among int8, int16, int32, uint32, float32, bool; **no int64** |
| ADD, SUB, MUL | `add.cc`, `sub.cc`, `mul.cc` | float32, int32, int8, int16 |
| EQUAL, NOT_EQUAL, LESS, GREATER… | `comparisons.cc` | bool, float32, int32, int64, int8 |
| GATHER, GATHER_ND | `gather.cc`, `gather_nd.cc` | params float32 or int8; **indices int32 only** |
| EMBEDDING_LOOKUP | `embedding_lookup.cc` | ids int32, table float32 or int8 |
| SELECT_V2 | `select.cc` | x/y float32, int8, int16 (no int32); **SELECT v1 absent** |
| CONCATENATION, STRIDED_SLICE, SLICE, SPLIT, SUM | as named | float32, int8, int32 (SUM: float32, int8, int16) |
| ONE_HOT, BUCKETIZE, HASHTABLE_* | **absent** | — |
| LOG, SQRT, FLOOR, ROUND | `elementwise.cc` etc. | float32 only |

- **Several inputs** of different types in one model are allowed. `input(i)` reads subgraph 0's
  list (`micro_interpreter.h` L88–91), and nothing limits the number of inputs; only the arena
  does.
- **Strings:** `TfLiteTypeSizeOf` has no size for kTfLiteString, so a string tensor cannot be
  allocated (`memory_helpers.cc`, `micro_common.cc`). This was read in the code, not run.

## 2. What the converter makes of it (measured)

Mode (a) is Caravan's settings: full int8 with int8 input and output. Mode (b) is the same but
leaves the input type unset.

- **Keras `Normalization`** becomes SUB and MUL in int8; both modes run. In (b) the firmware passes
  float32 and a QUANTIZE comes first.
- **A hand-written `(x−mean)/std`** in a registered custom layer becomes SUB only: the division
  folds into the next layer's weights.
- **`IntegerLookup`** fails: `'tf.HashTableV2' op is neither a custom op nor a flex op`. With Flex
  ops allowed it converts, but neither calibration nor the runtime can execute it.
  **`StringLookup`** crashes the converter (segfault) in mode (a).
- **Comparison one-hot** `cast(equal(x[..., None], vocab), float32)` on an **int32** input converts
  in both modes. The input stays int32 even under (a), and the one-hot is exact.
  - On a **float** input the converter quantises the code first, so EQUAL compares int8 values and
    the one-hot is wrong (error 1.0).
  - Codes must therefore enter as int32.
- **`CategoryEncoding(one_hot)`** lowers to ONE_HOT with int64, which is not in TFLM, and LiteRT
  even computes it wrongly ("off" cells read 0.502).
- **Keras `Embedding`** lowers to LESS, ADD and **SELECT v1**, which is not in TFLM. A custom layer
  around `tf.gather` gives GATHER only (1,880 bytes), which is in TFLM.
- **A window (1, 64, 5)** with the CAN ID as column 0 and four numeric columns: slicing, comparison
  one-hot, normalisation, concatenation, then a Conv1D head. It converts, runs, and every op is in
  TFLM (about 7.1 KB). Precision is the problem, as in 3.
- **Two inputs**, a float32 window and an int32 code window, convert and run. In mode (a) the
  numeric input becomes int8 and the code input stays int32.

## 3. The precision limit: one quantisation scale per input tensor

An input tensor has one scale, and the QUANTIZE (or int8 input) comes *before* any normalisation
in the graph. Columns of very different ranges that share one input tensor are crushed. This is
what research R11 of feature 006 saw on the synthetic CAN data (input scale 8.016).

| Layout | Measured error after normalisation |
|---|---|
| 5 columns, ranges from std 400 down to std 0.05, one tensor | up to **3.4 std units** (a and b alike) |
| same columns, all on one scale (control) | 0.03 (a), 0.12 (b) |
| **one input tensor per column** | about **0.02 std units** near the mean; clipped beyond the calibrated range (±2–2.7 σ) |

So "inside the model" works for numbers when **each numeric column (or each group of columns
sharing a scale) is its own input tensor**. A window of 64 steps over five columns becomes five
inputs of shape (1, 64), not one of (1, 64, 5). Concatenation happens inside the graph, after
normalisation.

## 4. Defects in today's Caravan this would hit

Measured or read during the probe:
- **`fix_batch` silently undoes an adapted `Normalization`.**
  - After `clone_model` and `set_weights`, `.mean` stays 0 and the variance stays 1; output
    differed by up to 1,869.
  - Statistics passed as constructor arguments survive.
  - No current template uses `Normalization`, so this is latent.
- **`fix_batch` refuses a Python-lambda `Lambda` layer** (safe-mode deserialisation). Preprocessing
  must therefore be registered custom layers.
- **`fix_batch` handles only `model.inputs[0]`**, so several inputs are not supported yet.
- **Input order is not preserved**: five inputs `f0..f4` came out as `f2, f0, f4, f3, f1`.
  - Caravan's representative dataset yields a list, which the converter matches to its internal
    order, so calibration silently swapped scales between inputs (error up to 2.8 std units).
  - Yielding a dict keyed by input name fixes it.
  - Feature 006's interface contract already binds by name and records positions read from the
    file; it must also record each input's dtype (int32, float32, int8).

## 5. What Ludwig does, and what carries over

Ludwig's config has `input_features` and `output_features`, each `{name, type, preprocessing,
encoder|decoder, loss}`, a `combiner` (default `concat`) and a `defaults:` block per type. After
preprocessing it writes `training_set_metadata.json`: per feature the fitted statistics (`mean`,
`std`, `min`, `max`, `str2idx`, `idx2str`, …) and the resolved preprocessing. Prediction replays
exactly that. For Caravan, that file is what has to reach the device, as constants in the graph.

| Ludwig type | Preprocessing (fitted) | On a microcontroller |
|---|---|---|
| `number` | `normalization`: zscore (default), minmax, iq, log1p; `missing_value_strategy`; `outlier_strategy` | zscore, minmax, iq: yes (one affine op). log1p: float LOG only, leave out at first |
| `binary` | strings → bool on the host (`fallback_true_label`) | yes, as 0/1 |
| `category` | vocabulary by frequency, `most_common`, `<UNK>`; encoders dense (embedding), onehot, sparse | yes, with int32 codes, comparison one-hot, gather embedding |
| `timeseries` | one cell holds a whole sequence as text, or `window_size` over rows | the row-per-step window is what Caravan does; text cells: no |
| `set`, `bag`, `sequence`, `text` | tokenizers, dynamic vocabularies | no |
| output `category` | softmax cross-entropy, `class_weights`, `top_k` | argmax; names in the header |
| output `binary` | sigmoid, `threshold` | yes |
| output `number` | MSE, optional normalisation inverted | yes |

Two deliberate differences from Ludwig:
- **Fit on the training part only.** Ludwig fits its statistics on train, validation and test
  together (`data/preprocessing.py` L1569–1591), which leaks the test split into the
  preprocessing.
- **Always reserve index 0 for unknown.** Ludwig's code adds `<UNK>` only when `most_common` cuts
  the vocabulary, although its docs say index 0 is always `<UNK>`. On a device an unseen code must
  have a defined place.

## 6. Conditions for the specification

1. **Raw values in, nothing to write in firmware.**
   - The firmware passes, per column and time step, an **int32** for a `category` or `binary`
     column and a **float32** for a `number` column.
   - Everything else is in the graph: normalisation, the comparison one-hot, the unknown slot, the
     embedding.
   - Strings never reach the device. A category whose raw values are strings needs its codes
     assigned on the host, and the interface contract ships the table.
2. **One input tensor per column** (or per group of columns sharing a scale), shape (1, window).
   This is the price of exact categories and of numeric precision, and TFLM allows it.
3. **Custom layers only:** standardise, comparison one-hot, gather embedding. No `Lambda`, no Keras
   lookup or encoding layers.
4. **Caravan's conversion path changes:**
   - `fix_batch` must handle several inputs and keep the statistics;
   - the representative dataset yields dicts keyed by input name;
   - the interface contract records each input's name, dtype, shape and position.
5. **Statistics are fitted on the training part only** and recorded, like Ludwig's metadata, in the
   run directory and in the interface contract.
6. **A first type set:**
   - inputs: `number`, `binary`, `category`;
   - outputs: `category`, `binary`, `number`;
   - the window stays the one way rows become samples.

   Set, bag, sequence and text are out of scope (no device path).
7. **Open for the specification:**
   - the manifest's exact shape: Ludwig's `input_features` naming, or Caravan's `inputs`, and where
     the window is declared;
   - the default numeric preprocessing (zscore like Ludwig);
   - the vocabulary cap (`most_common`) and its default for a microcontroller;
   - whether columns of one scale may be grouped into one tensor to save inputs;
   - how missing values are filled;
   - whether `log1p` is in.

## Not verified

- String-tensor allocation failing in TFLM, and mixed-type inputs running on TFLM itself: both are
  from reading the source, not from a run on a board or in the TFLM test harness. The models ran in
  LiteRT.
- The ESP-NN `mul.cc` type coverage was not checked.
