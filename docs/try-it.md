# Try Caravan

From an empty directory to an int8 model, its C array and its interface contract, in one sequence
of commands. You need Python 3.13 for training (the training framework publishes nothing newer
yet), and `curl` and `tar` to fetch the example. Linux and macOS.

## Install

A fresh virtual environment, and Caravan with both extras, from its GitHub release:

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
- `render` prints the manifest as the pipeline will use it, every default filled in. The labels
  are as stated; the input columns say `derived`, because the data decides them at run time.
- `export` runs every stage: it reads the data, builds the model, checks that it can fit the
  boards, trains, quantizes to int8, measures what quantization cost, and writes the files below.
  On a laptop it takes well under a minute. Run it again and every stage is reused from the cache.

The last lines of `export` name the run directory, `runs/<time>-<digest>/`.

## What you get

In the run directory:

- `report.json` — the run: every stage, the data, the metrics with what they were measured on,
  the fit check, the quantization verdict, the interface
- `resolved-manifest.yaml` — the manifest as run, with what the data said filled in
- `data/schema.json` — the columns and labels the data stage found
- `metrics.json` — accuracy and the confusion matrix of the trained model, on the test split
- `quantization.json` — the int8 model's accuracy against the trained one, and the gate's verdict
- `export.json` — the operators, which of them each board accelerates, and the model's size
- `framework.log` — what the training framework printed, kept here rather than on your console
- `model/model.tflite` — the int8 model
- `model/model_data.h` — the model as a C array, with named input and output positions and the
  label names
- `model/model_data.cc` — the array itself
- `model/resolver.h` — exactly the operators this model needs, for the microcontroller runtime
- `model/interface.json` — names, positions, shapes, scales and zero points of the input and the
  output, and how raw data becomes an input
- `model/fit.json` — the lower bounds on flash and RAM, against each board
- `runner/<board>/main.cc` — a starting point for firmware on each board, binding by name

## Your own data

`dataset.source` is a directory. Caravan reads every `.csv` file in it (and `.tsv`, `.txt`), in
path order, as one sequence of records:

- a header row; one column holds the answer, `label` unless `outputs[0].column` says otherwise;
- every other column becomes an input, unless `inputs[0].columns` lists the ones to use;
- `inputs[0].window` records form one sample. Windows never overlap, and a window whose records
  disagree on the label is discarded and counted;
- the labels are the distinct values of the label column, sorted, unless `outputs[0].labels` pins
  their order;
- the split is drawn at random from the fractions in `dataset.split`, stratified by label, or
  the data decides it: with `dataset.split: {column: split}`, every record names `train`, `val` or
  `test` in that column. Use that whenever samples of one subject, vehicle or session must not
  end up on both sides, and whenever your windows came from a recording cut with overlap. A window
  whose records name two parts is discarded and counted, and the split column is never an input.

`caravan validate` checks a manifest without reading the data; the first `build`, `train` or
`export` reads it and says what it found.

## On Python 3.14 or 3.15

Install without the extras, from the same URL without `[train,verify]`. `validate` and `render`
work. A training command stops before it writes anything, with exit code 4, and says which extra
and which Python it needs.
