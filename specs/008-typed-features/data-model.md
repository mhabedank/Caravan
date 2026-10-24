# Data Model: Typed Features

Each type is tagged **core** (no extra), **train** or **verify**, by Principle XII's layering rule.

## Manifest `caravan/v0.2` — core

See `contracts/manifest.md` for every key and default. The validated model:

| Entity | Fields |
|---|---|
| `Manifest` | `apiVersion`, `model`, `input_features` (≥1), `output_features` (exactly 1), `preprocessing`, `defaults`, `dataset`, `trainer`, `random_seed`, `export` |
| `InputFeature` | `name`, `type` ∈ {number, binary, category}, `preprocessing` (per type), `encoder` (category) |
| `OutputFeature` | `name`, `type` ∈ {category, binary, number}, `preprocessing`, `loss`, `threshold`, `clip`, `accuracy_drop_max` or `mae_increase_max` |
| `GlobalPreprocessing` | `window_size`, `split: {type, probabilities, column}` |
| `Defaults` | per type: `preprocessing`, `encoder` |
| `Trainer` | `epochs`, `batch_size`, `learning_rate`, `optimizer.type`, `early_stop` |

**Resolution order**, which `render` shows and every stage reads:
1. the feature's own value;
2. `defaults` for its type;
3. the type's default.

## Fitted preprocessing — core (`data/fit.py`), written to `data/preprocessing.json`

Fitted on the windows of the training part only (research R6):

| Feature type | Fitted | Applied by |
|---|---|---|
| number | `shift`, `scale` (zscore: mean/std; minmax: min/max−min; iq: q2/q3−q1; scale 0 → 1), `fill` | `Standardize` in the model |
| category (input) | `vocab` (frequency desc., ties by text, capped by `most_common`), `cut` (count), `text_codes` when values are text, `fill` | `VocabularyOneHot`, the encoder |
| binary (input) | `true_spelling`, `false_spelling`, `fill` | `AsChannel` |
| category (output) | `labels` (same order rule, no unknown) | the head, the header |
| number (output) | `shift`, `scale` when `normalization` is set | the inverse in the model |

The pipeline merges the fitted values into the resolved manifest under each feature's
`preprocessing.fitted`, so they are part of the keys of `build`, `train` and `quantize`, like the
derived labels of feature 006.

## Model inputs and outputs — train

| Feature type | Model input | Inside the model | Channels per step |
|---|---|---|---|
| number | float32 (window_size) | QUANTIZE → `Standardize` | 1 |
| binary | int32 (window_size) | `AsChannel` (CAST) | 1 |
| category, `onehot` | int32 (window_size) | `VocabularyOneHot` (EQUAL, CAST, SUM, SUB, CONCATENATION) | V+1 |
| category, `dense` | int32 (window_size) | `VocabularyOneHot` → `Dense(embedding_size, no bias)` | embedding_size |

The concatenated channels give a (window_size, channels) tensor, which goes into the template's
body (`mlp`, `conv1d`).

| Output type | Head | Model output | Loss |
|---|---|---|---|
| category | Dense(labels) + softmax | float32 (labels) | sparse categorical cross-entropy (+ `class_weights`) |
| binary | Dense(1) + sigmoid | float32 (1) | binary cross-entropy (+ `positive_class_weight`) |
| number | Dense(1) [+ inverse normalisation] [+ clip] | float32 (1) | `loss.type` |

## Run report — additions

| Key | Meaning |
|---|---|
| `data.features[]` | per feature: name, type, fitted values, `cut` |
| `data.ignored_columns` | columns no feature, split or output reads |
| `metrics` | per output type (research R5) |
| `quantization.gate` | `metric` (`accuracy` or `mae`), `trained`, `quantized`, `change`, `budget`, `verdict` |
| `interface.inputs[]` | per input: name, position, dtype, shape, type, tables |

## Rules — core

See `contracts/manifest.md`, *Rules*:
- **new**: CF-14, CF-15, CF-16, CF-17, DS-14, DS-15;
- **retired**: CF-10, which stays reserved.
