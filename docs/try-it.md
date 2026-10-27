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
pip install "caravan-ml[train,verify] @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc3/caravan_ml-0.1.0rc3-py3-none-any.whl"
caravan --version
```

`caravan --version` prints `caravan-ml 0.1.0rc3`. The training extra is the large part of the
install.

## Fetch the example

Two directories of the tagged source, the example manifest and the synthetic data it reads. No
`git` needed:

```bash
# step: fetch
curl -sL https://github.com/mhabedank/Caravan/archive/refs/tags/v0.1.0rc3.tar.gz \
  | tar xz --strip-components=1 Caravan-0.1.0rc3/examples Caravan-0.1.0rc3/tests/fixtures/datasets/synthetic
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
- `model/test_windows.h` — windows of the test part as raw values, with what the int8 model
  answered on this machine, for a board to run and compare (`export.test_windows`; the board guide,
  `guides/lora32.md`, uses it)
- `runner/<board>/main.cc` — a starting point for firmware on each board, filling every input by
  name with raw values

## Your own data

[Your own project](guides/own-project.md) goes from a CSV of your own to a manifest, one decision
at a time. Every field is in the [manifest reference](reference/manifest.md).

## On Python 3.14 or 3.15

Install without the extras, from the same URL without `[train,verify]`. `validate` and `render`
work. A training command stops before it writes anything, with exit code 4, and says which extra
and which Python it needs.
