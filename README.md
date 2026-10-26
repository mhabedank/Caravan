# Caravan

A declarative pipeline for small machine learning models that run on microcontrollers.

One YAML manifest per model names the columns the model reads, each with a type, as in Ludwig; the
column it answers; and the boards it must fit. Each type brings its preprocessing into the model,
so a firmware passes raw values. The pipeline does the rest: architecture from a template, a fit check against
the boards before training, training, int8 quantization, export with the model's interface
contract, footprint analysis, emulated verification, hardware benchmark and, optionally,
publication. The manifest asks only for what a stage uses: no compliance block, no description
fields, nothing the data already says.

Caravan is the build tool for the embedded models of the
[Mobility Model Zoo](https://github.com/mhabedank/mobility-model-zoo) and lives in its own
repository under Apache-2.0, so that models built with it stay portable and the framework stays
usable outside the zoo.

**Scope, deliberately narrow:** models for microcontrollers and comparable constrained hardware.
Cloud, desktop and LLM models are explicitly out of scope, and so is becoming an inference
runtime, a platform description language, a cycle-accurate simulator or a research-grade
architecture search. See `.specify/memory/constitution.md`.

## Status

**0.1.0rc2, the second release candidate.** Every stage from manifest to C array exists: `validate`,
`render`, `build`, `train`, `quantize` and `export`, with `templates` and `boards` to list what is
registered. Two templates, `mlp` and `conv1d`, and three boards, `s32k144`, `stm32h743` and `esp32`.
`build` checks the model against the boards' flash and RAM before any training, and `export` writes
an interface contract a firmware author binds by. The manifest names its columns as Ludwig does
(`caravan/v0.2`, feature 008): one input per column, its preprocessing fitted on the training part
and built into the model, and outputs of type `category`, `binary` or `number`. rc1 read the
previous form, `caravan/v0.1`. `docs/releases/0.1.0.md` says what is in 0.1.0 and what is not.

Not on the package index. Each version is installed from its GitHub release.

## Try it

`docs/try-it.md` goes from an empty directory to an exported model in one sequence of commands.
With a checkout, the example manifest validates on any supported Python:

```bash
# step: readme
caravan validate examples/picket-mlp.yaml
caravan render examples/picket-mlp.yaml --stdout
```

## Install

From the release, in a virtual environment:

```bash
pip install "caravan-ml @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc2/caravan_ml-0.1.0rc2-py3-none-any.whl"
pip install "caravan-ml[train,verify] @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc2/caravan_ml-0.1.0rc2-py3-none-any.whl"
```

The first line is the core: `validate` and `render`, on Python 3.13 to 3.15. The second adds
training and converting (Python 3.13) and reading exported models (3.13 and 3.14). To build from
the tagged source instead:
`pip install "caravan-ml[train,verify] @ git+https://github.com/mhabedank/Caravan@v0.1.0rc2"`.

The default installation has two runtime dependencies, weighs about 9 MiB and pulls no
machine-learning framework, because checking and resolving a manifest does not need one.

The two extras are very different sizes, and that is the point:

| Extra | Size | Python | For |
|---|---|---|---|
| `verify` | **114 MiB**, 7 packages | 3.13, 3.14 | reading and running an exported model |
| `train` | 1,971 MiB, 41 packages | **3.13 only** | building, training, converting |

Reading an exported model needs no training framework, and the stages after quantization do
nothing else — so they are not dragged along by the conversion's weight. Neither extra reaches
3.15 yet: TensorFlow publishes no wheel above 3.13 and the model runtime none above 3.14, both
checked rather than assumed. `caravan validate` and `caravan render` run on all three.

**The extra needs Python 3.13.** TensorFlow publishes no stable wheel above 3.13, and Python
packaging has no per-extra version window, so the published floor is 3.13 until a stable
TensorFlow ships for the current Python. All of 3.13, 3.14 and 3.15 are supported and tested; on
3.14 and 3.15 the extra installs Caravan's training code and no framework, and `build` and `train`
then say so rather than failing in the resolver. `docs/budgets.md` carries the reasoning and the
condition that closes the window.

## Use

```bash
caravan validate manifest.yaml     # is this manifest sound?
caravan render   manifest.yaml     # what will the pipeline actually use?
caravan build    manifest.yaml     # what model does it describe, and how large is it?
caravan train    manifest.yaml     # train it on the dataset it names
caravan quantize manifest.yaml     # convert it, and judge what the quantization cost
caravan export   manifest.yaml     # write the model, its C array, its resolver and a runner
caravan templates                  # which templates are registered?
caravan boards                     # which target boards are known?
```

`caravan export` is where the pipeline stops being Caravan's business and becomes a firmware
author's. It writes the model, the same bytes the accuracy gate measured; a C array with its
header, aligned the way the runtime requires; an operator resolver holding exactly the operators
the model file declares and no others; and one runner skeleton per target board, naming that
board's runtime and compiler. It also records, per operator and per board, whether that board's
accelerated kernel library supplies a kernel for it — with the source and the date that claim was
read — because an operator with no accelerated kernel falls back to the reference implementation
without saying so.

What it does not do is claim anything it has not done. It does not compile the skeleton, it does
not say which kernel the build will select, and it does not state the working memory the model
needs on a board: it states a computed floor, names the method, and says that the figure a board
requires is measured and not computed here.

Every command exits 0 when it did the work, 1 when a rule says no, 2 on a usage error, 3 on a
defect in the tool itself and 4 when the environment is missing something that installs
separately. Every rejection names the offending field, what was wrong with it and what is accepted
there.

```text
manifest.yaml: export.targets[0] — unknown board "s32k145"
    known boards: esp32, s32k144, stm32h743
```

`render` writes the fully resolved manifest — every default expanded — next to a run report, so
two runs can be compared field by field.

`train` writes the trained model, both checkpoints and the quality metrics into a run directory,
and every number in its report says which split and which dataset version it was measured
against. A stage result is reused when the fields that stage reads and the dataset are unchanged,
so tightening the quantization budget re-runs the quantization and never the training:

```text
picket-mlp.yaml: trained — 50 of 50 epochs (best: 50)
    test, 12 windows, dataset sha256:8fac6d55c7e…  accuracy 1.000  f1_macro 1.000
    build: reused the result of run 20261024T090718Z-f9e0adce
```

A dataset is raw, record-level delimited text. Each column the model reads is an input feature
with a type — `number`, `category` or `binary` — and the output feature names the column it answers;
every other column is ignored, visibly. What a type learns from the data — a shift and a scale, a
vocabulary, a label order — is fitted on the training part only and built into the model. Caravan
does the windowing, and a window whose records disagree about the output is discarded and counted
rather than labelled. The split is drawn at random or per class with Ludwig's `probabilities`, or,
with `{type: fixed, column: split}`, named by the data record by record, so a subject or a
recording never ends up on both sides. `specs/002-build-and-train/contracts/dataset.md` and
`specs/008-typed-features/contracts/manifest.md` are the whole contract.

`quantize` converts the trained model and then **judges** it: three measurements on the test
split — trained, converted, quantized — and the gate is the difference between the last two,
because that difference is the loss from quantization and nothing else. It is accuracy for a
`category` or `binary` output and the mean absolute error, in the column's unit, for a `number`.
Over the budget and the run fails with no model written, and the per-layer error table says which
layer lost it. Nothing can lower the budget but an edit to the manifest.

```text
picket-mlp.yaml: quantized int8 — 27,608 bytes from 269,434 (model/quantized.tflite)
    tensors: bool 1, float32 6, int32 9, int8 41 — integer inside, raw values at the boundary; inputs b2 float32, can_id int32, b1 float32, dlc float32, b0 float32
    calibration: 56 of 500 requested, drawn from 56 available in the train split, seed 42
    test, 12 windows, dataset sha256:8fac6d55c7e…
      accuracy: trained 1.000  converted 1.000  quantized 1.000
      conversion cost 0.000  quantization cost 0.000  accepted 0.020  → pass
```

What it reports about the model is read from the produced file, never from the converter's output:
the converter prints `fully_quantize: 0` while producing a model whose every tensor is an integer,
so its log is not evidence. `specs/003-quantize/contracts/gate.md` has the arithmetic.

## Templates

| Template | For | Produces |
|---|---|---|
| `mlp` | a decider over a window of samples, from hidden layer widths | `RESHAPE`, `FULLY_CONNECTED`, `SOFTMAX` |
| `conv1d` | a convolutional decider over a window, from blocks of filters | `RESHAPE`, `CONV_2D`, `MAX_POOL_2D`, `FULLY_CONNECTED`, `SOFTMAX`, and `MEAN` with the reducing head |

In front of the template sit the features' own layers: QUANTIZE, SUB and MUL for a `number`;
EQUAL, CAST, RELU, SUM, SUB and CONCATENATION for a `category`, then a FULLY_CONNECTED for its
embedding; CAST and RELU for a `binary`; CONCATENATION to join them; DEQUANTIZE at the output. Every
one is an operator TFLite Micro has.

A template is two files and a registration: a typed parameter half in the core, and a builder half
behind the `train` extra. Adding one edits no central list.

`conv1d` is called that although the exported file contains a two-dimensional convolution: the
converter adds a dummy spatial dimension and removes it again, and the runtime has no
one-dimensional convolution at all. The template speaks about the model; the export record says
what the file contains.

Its head is a choice with a measured cost. On a two-block architecture at 128 samples by 9
channels: reducing over time gives 2,502 parameters and six operators; flattening gives 7,878
parameters and five. Neither built-in accelerated kernel library has an implementation for the
reduction, so the smaller model pays one more operator on the reference implementation. `caravan
export` records which, per board, with the source and the date of that claim.

## A manifest

```yaml
apiVersion: caravan/v0.2
model:
  name: picket-mlp
  version: 0.2.0
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1
input_features:
  - name: can_id
    type: category          # an identifier, not a magnitude
  - {name: dlc, type: number}
  - {name: b0, type: number}
  - {name: b1, type: number}
  - {name: b2, type: number}
output_features:
  - name: label
    type: category
    accuracy_drop_max: 0.02
preprocessing:
  window_size: 64
  split: {type: stratify, column: label, probabilities: [0.7, 0.15, 0.15]}
dataset: datasets/car-hacking/
export:
  targets: [s32k144, stm32h743, esp32]
  representative_samples: 500
```

The names are Ludwig's wherever Ludwig has the concept; `docs/manifest-changes.md` lists the few
exceptions and why. The output's type says what the model does; its budget is stated, not
defaulted, because a budget nobody wrote down is a budget nobody chose. The feature names are the
columns, and what a firmware author binds by: the export writes each input's position, element type
and shape, what was fitted for it and the label order into `model/interface.json` and the C header.

Caravan carries no compliance layer. The rights to the data, and the use of a model trained on it,
are the author's; Caravan neither asks about them nor claims to have checked them.

Until Caravan 1.0.0 the manifest may change without migration. A manifest in another form, such as
the previous `caravan/v0.1`, is refused with the version this build reads, and
`docs/manifest-changes.md` says what to edit by hand.

## Where things are

| | |
|---|---|
| `.specify/memory/constitution.md` | the rules: twelve principles, the scope boundary, the gates |
| `specs/<nnn>-<name>/` | one feature's spec, plan, research, data model, contracts and tasks |
| `docs/roadmap.md` | what is planned per version, and the non-goals, each with its reason |
| `docs/design/` | the design document Caravan was started from, frozen as a dated record |
| `docs/research/` | sourced research notes that decisions cite |
| `docs/budgets.md` | the dependency, install and Python-version budgets, with measurements |
| `src/caravan/targets/boards/` | the board descriptions, one data file per board |

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

The suite splits three ways by what a test needs:

```bash
uv run --extra verify pytest          # everything but tests/train, on any supported Python

uv venv --python 3.13 .venv313        # conversion needs 3.13
uv pip install --python .venv313 -e ".[train,verify]" pytest
.venv313/bin/python -m pytest tests   # the whole suite
```

`tests/verify` needs the model runtime and runs on 3.13 and 3.14; `tests/train` needs the training
framework and runs on 3.13 only.

One footgun worth knowing: an editable install records the project's **extras** at install time,
so after adding or renaming one, re-run the `uv pip install -e` line. The layering tests read that
metadata, and a stale environment makes them report an extra that the file already has.
Continuous integration always installs fresh and never sees it. A test that needs a framework lives in one of those two
directories and nowhere else — putting one elsewhere turns two continuous-integration jobs red,
which is how the rule was learned.

See `specs/003-quantize/quickstart.md` for the scenarios that validate the current feature, and
`CONTRIBUTING.md` for the dependency gate a new dependency has to pass.

## Licence

Apache-2.0. See `LICENSE`.
