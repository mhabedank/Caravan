# Caravan

A declarative pipeline for small machine learning models that run on microcontrollers.

One YAML manifest per model declares the data, what goes into the model and what comes out, and the
boards it must fit. The pipeline does the rest: architecture from a template, a fit check against
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

Early. Five of the pipeline's verbs exist: `validate` and `render` (feature 001), `build` and
`train` (002), and `quantize` (003) — the first stage with a budget that decides whether a run
produces an artifact at all. The core still loads no machine-learning framework.

## Install

```bash
pip install caravan-ml                      # the command is `caravan`
pip install "caravan-ml[verify]"            # plus reading and running exported models
pip install "caravan-ml[train,verify]"      # plus training and converting, on Python 3.13
```

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
picket-mlp.yaml: trained — 26 of 50 epochs, stopped early at 26 (best: 21)
    test, 12 windows, dataset sha256:8fac6d55c7e…  accuracy 0.667  f1_macro 0.581
    build: reused the result of run 20261022T182748Z-b271d5b3
```

A dataset is raw, record-level delimited text. The output names the column holding the class
(`label` unless it says otherwise), and the class names are read from it, sorted, unless the
manifest pins their order; the input reads every other column unless it names its own. Caravan does
the windowing, and a window whose records disagree about the label is discarded and counted rather
than labelled. `specs/002-build-and-train/contracts/dataset.md` and
`specs/006-declared-io/contracts/manifest.md` are the whole contract.

`quantize` converts the trained model and then **judges** it: three accuracies on the test split —
trained, converted, quantized — and the gate is the difference between the last two, because that
difference is the loss from quantization and nothing else. Over the threshold and the run fails
with no model written, and the per-layer error table says which layer lost the accuracy. Nothing
can lower the threshold but an edit to the manifest.

```text
picket-mlp.yaml: quantized int8 — 15,664 bytes from 162,375 (model/quantized.tflite)
    tensors: int32 9, int8 9 — fully integer, input int8 scale 8.015686
    calibration: 56 of 500 requested, drawn from 56 available in the train split, seed 42
      trained 0.667  converted 0.667  quantized 0.667
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
apiVersion: caravan/v0.1
model:
  name: picket-mlp
  version: 0.1.0
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1
inputs:
  - name: frames
    kind: series
    window: 64
outputs:
  - name: attack
    kind: class
    accuracy_drop_max: 0.02
dataset:
  source: datasets/car-hacking/
  representative_samples: 500
export:
  targets: [s32k144, stm32h743, esp32]
```

The output's kind says what the model does; its budget is stated, not defaulted, because a budget
nobody wrote down is a budget nobody chose. The names `frames` and `attack` are what a firmware
author binds by: the export writes them, with each tensor's position, shape, scale and zero point
and the label order, into `model/interface.json` and the C header.

Caravan carries no compliance layer. The rights to the data, and the use of a model trained on it,
are the author's; Caravan neither asks about them nor claims to have checked them.

Until Caravan 1.0.0 the manifest may change without migration. A manifest in another form, such as
the previous `caravan/v0`, is refused with the version this build reads, and
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
