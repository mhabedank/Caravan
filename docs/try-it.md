# Try Caravan

From an empty directory to an int8 model, its C array and its interface contract, in one sequence
of commands. You need Python 3.13 for training (the training framework publishes nothing newer
yet), and `curl` and `tar` to fetch the example. Linux and macOS.

## Install

A fresh virtual environment, and Caravan with both extras, from its GitHub release. The `.`
line activates the environment; every later command runs inside it. If `pip` complains that your
Python is too old, the environment is not active — run `deactivate` and the `.` line again:

```bash
# step: install
python3.13 -m venv caravan-try
. caravan-try/bin/activate
pip install "caravan-ml[train,verify] @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc1/caravan_ml-0.1.0rc1-py3-none-any.whl"
caravan --version
```

`caravan --version` prints `caravan-ml 0.1.0rc1`. The training extra is the large part of the
install.

## Fetch the example

Two directories of the tagged source, the example manifest and the synthetic data it reads. No
`git` needed:

```bash
# step: fetch
curl -sL https://github.com/mhabedank/Caravan/archive/refs/tags/v0.1.0rc1.tar.gz \
  | tar xz --strip-components=1 Caravan-0.1.0rc1/examples Caravan-0.1.0rc1/tests/fixtures/datasets/synthetic
```

## Run

```bash
# step: run
caravan validate examples/picket-mlp.yaml
caravan render examples/picket-mlp.yaml --stdout
caravan export examples/picket-mlp.yaml
```

- `validate` checks the manifest and says `valid`.
- `render` prints the manifest as the pipeline will use it, every default filled in: each
  feature's preprocessing, the trainer, the split. What only the training part can say — the label
  order, the vocabulary of `can_id`, the embedding size — says `derived`.
- `export` runs every stage: it reads the data, splits it, fits each feature's preprocessing on the
  training part, builds the model with that preprocessing inside it, checks that it can fit the
  boards, trains, quantizes to int8, measures what quantization cost, and writes the files below.
  On a laptop it takes well under a minute. Run it again and every stage is reused from the cache.

The last lines of `export` name the run directory, `runs/<time>-<digest>/`.

## What you get

In the run directory:

- `report.json` — the run: every stage, the data, the metrics with what they were measured on,
  the fit check, the quantization verdict, the interface
- `resolved-manifest.yaml` — the manifest as run, with what was fitted filled in
- `data/schema.json` — the features, the output and the ignored columns the data stage found,
  and how the windows were split
- `data/preprocessing.json` — what each feature's preprocessing learned from the training part:
  shift and scale of a number, the vocabulary of a category, the label order
- `metrics.json` — accuracy and the confusion matrix of the trained model, on the test split
- `quantization.json` — the int8 model's accuracy against the trained one, and the gate's verdict
- `export.json` — the operators, which of them each board accelerates, and the model's size
- `framework.log` — what the training framework printed, kept here rather than on your console
- `model/model.tflite` — the int8 model
- `model/model_data.h` — the model as a C array, with a named position for every input and the
  output, each with its element type, and the label names
- `model/model_data.cc` — the array itself
- `model/resolver.h` — exactly the operators this model needs, for the microcontroller runtime
- `model/interface.json` — every input by name, with its position, element type, shape and type,
  what was fitted for it, and what to pass when a reading is missing; what the output means
- `model/fit.json` — the lower bounds on flash and RAM, against each board
- `runner/<board>/main.cc` — a starting point for firmware on each board, filling every input by
  name with raw values

## Your own data

`dataset` is a directory. Caravan reads every `.csv` file in it (and `.tsv`, `.txt`), in path
order, as one sequence of records with a header row. The manifest names columns, as Ludwig does:

- **Each column the model reads is an input feature**, `{name: <column>, type: <type>}`, and its
  type brings its preprocessing. You write nothing around the model; the firmware passes raw values.
  - `number` — a measurement. Standardised inside the model with the mean and deviation of the
    training part (`preprocessing.normalization`: `zscore`, `minmax`, `iq` or `null`). Passed as
    float32.
  - `category` — a code or a name, such as a CAN identifier or a gear. The training part's most
    frequent values (`most_common`, 32) form the vocabulary; anything else is "unknown". Encoded
    inside the model, as an embedding (`encoder: {type: dense}`, the default) or one-hot. Passed as
    int32: the integer itself, or, for text, the code `model/interface.json` lists.
  - `binary` — two states, spelt `yes`/`no`, `true`/`false`, `1`/`0` and the like, or two words of
    your own with `preprocessing.fallback_true_label`. Passed as int32 0 or 1.
- **One column is the output feature**, `{name: <column>, type: category | binary | number}`, with
  its int8 budget: `accuracy_drop_max` for a category or a binary, `mae_increase_max` in the
  column's unit for a number.
- **Every other column is ignored**, and every run lists it under `ignored_columns`.
- `preprocessing.window_size` records form one sample. Windows never overlap, and a window whose
  records disagree on the output is discarded and counted.
- The label order of a category output is by frequency in the training part, as in Ludwig, unless
  `preprocessing.vocab` on the output pins it.
- The split is `preprocessing.split`: `random` or `stratify` (per class of the output) with
  `probabilities` for train, validation and test, or `fixed`, where the data decides: with
  `{type: fixed, column: split}`, every record names its part in that column as `train`,
  `validation` or `test`, or as Ludwig's `0`, `1` or `2`. Use that whenever samples of one subject,
  vehicle or session must not end up on both sides, and whenever your windows came from a recording
  cut with overlap. A window whose records name two parts is discarded and counted, and the split
  column is never a feature.
- Everything a type learns — a shift and a scale, a vocabulary — is fitted on the training part
  only, so the test part says how the model does on data it has never seen.

`caravan validate` checks a manifest without reading the data; the first `build`, `train` or
`export` reads it and says what it found.

## On Python 3.14 or 3.15

Install without the extras, from the same URL without `[train,verify]`. `validate` and `render`
work. A training command stops before it writes anything, with exit code 4, and says which extra
and which Python it needs.
