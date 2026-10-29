# CLI reference

The command line is `caravan`. Every command takes one manifest, except the two listings. Every
command that runs a stage creates a run directory with a report.

```text
caravan [--version] <command> ...
```

- `--version` prints `caravan-ml <version>` and exits.
- `caravan <command> --help` prints a command's options.

No option skips, forces or silences a check. The only thing an option can bypass is the cache
(`--fresh`).

## By task

| You want to | Run |
|---|---|
| Check a manifest for mistakes, without reading the data | [`validate`](#caravan-validate) |
| See the manifest with every default filled in | [`render`](#caravan-render) |
| Find out whether a model fits your boards before training | [`build`](#caravan-build) |
| Train the model and look at its metrics | [`train`](#caravan-train) |
| Try a different `accuracy_drop_max` against the cached training | [`quantize`](#caravan-quantize) |
| Produce the files a firmware author compiles | [`export`](#caravan-export) |
| See which templates this version registers | [`templates`](#caravan-templates) |
| See the known boards and their flash and RAM | [`boards`](#caravan-boards) |

The usual order of a full run:

```text
caravan validate manifest.yaml
caravan export manifest.yaml
```

`export` runs `build`, `train` and `quantize` first, reusing whatever is cached.

## Exit codes

Every command ends with one of five codes. A continuous integration job can act on each one
differently.

| Code | Meaning |
|---|---|
| `0` | The manifest is valid, and any requested artifact was written. |
| `1` | A rule said no: the manifest is invalid, its declared schema version is unknown, the data disagrees with it, or a gate failed (the int8 accuracy, the fit on a board). The finding names the rule, the field path, what was wrong and what is accepted. |
| `2` | Usage error: an unknown option, a missing argument, an unreadable path. |
| `3` | A defect in Caravan itself, reported as one, with a trace. Not a problem with your manifest. |
| `4` | The environment is incomplete: a part that installs separately (the `train` or `verify` extra) is missing, or this Python is outside its window. Nothing was written. |

## Options shared by the commands

**Report options.** `validate`, `render` and the four stage commands take these:

- `--runs-dir <path>`: where the run directory is created (default `runs`). Each run gets
  `runs/<time>-<digest>/` with `report.json` and `resolved-manifest.yaml`.
- `--json`: the findings on standard output as one JSON document, for a machine to read.
- `-q`, `--quiet`: no human summary; the exit code only.

**Stage options.** `build`, `train`, `quantize` and `export` also take these:

- `--cache-dir <path>`: where stage results are stored (default `.caravan/cache`).
  - Every stage's result is cached under a key made from the manifest fields that stage reads and
    the dataset version.
  - An unchanged stage is reused, not repeated. A change that only a later stage reads, such as a
    budget, never retrains.
- `--fresh`: ignore any cached result and produce everything again. Recorded in the report.
- `--framework-output`: show the training framework's own output on the console. Without it, that
  output goes to `framework.log` in the run directory.

## caravan validate

Checks one manifest without reading the data.

**When you want it.** After every edit. It reads no data, so it is instant, and it catches the
spelling mistakes and type errors that would otherwise surface a minute into a run.

- **What it checks:** the schema version, every field and its type, the template and its
  parameters, the boards, and the rules that need only the manifest.
- **What it prints:** `valid`, or one finding per problem. Each finding gives the rule identifier
  ([rules](rules.md)), the field path, what was wrong and what is accepted.

**Arguments.** `<manifest>`: the manifest file.

**Options.**

- `--no-report`: check only, write nothing at all. No run directory is created.
- `--runs-dir <path>`, `--json`, `-q` / `--quiet`: see above.

**Reads.** The manifest, the template registry and the board descriptions.

**Writes.** A run directory with `report.json`, unless `--no-report` is given.

**Exit codes.** `0` valid; `1` invalid; `2` usage.

## caravan render

**When you want it.** When you want to know what you are *actually* running. It fills in every
default, so it answers "what is the window?" and "what preprocessing will this column get?"
faster than reading the manifest reference. Also the quickest way to see which values can only come
from the data: those print as `derived`.

Writes the manifest as the pipeline will use it, every default filled in.

- **Shown in full:** each feature's preprocessing, the trainer, the split, the export.
- **Shown as `derived`:** what only the training part can say, until a run has fitted it: the
  label order, a category's vocabulary, the embedding size.

**Arguments.** `<manifest>`: the manifest file.

**Options.**

- `--stdout`: write the resolved manifest to standard output instead of a run directory.
- `--runs-dir <path>`, `--json`, `-q` / `--quiet`: see above.

**Reads.** The manifest, the templates and the boards. Not the data.

**Writes.** `resolved-manifest.yaml` and `report.json` in a run directory, or the manifest on
standard output with `--stdout`.

**Exit codes.** `0`; `1` invalid manifest; `2` usage.

## caravan build

**When you want it.** To find out whether a model can fit your boards before spending time on
training. This is the stage that runs the fit check, so a model that is hopeless on your hardware
fails here in seconds rather than after an hour.

Reads the data and builds the model the manifest describes. Then the **fit check**: is the model
small enough for every target board?

- **The data stage, first:**
  - reads the columns the features name;
  - forms windows and splits them into training, validation and test parts;
  - fits each feature's preprocessing on the training part only.
- **The model:** built from the template, with that preprocessing inside it.
- **The fit check:** compares computed lower bounds on flash and working memory with each board.
  A model that cannot fit is refused before any training (rule [F-1](rules.md#f-1)).

**Arguments.** `<manifest>`: the manifest file.

**Options.** `--cache-dir <path>`, `--fresh`, `--framework-output`, `--runs-dir <path>`, `--json`,
`-q` / `--quiet`: see above.

**Reads.** The manifest and the dataset.

**Writes.** In the run directory:
- `data/schema.json`: the features, the output, the ignored columns and the split;
- `data/preprocessing.json`: what each feature learned from the training part;
- the built model;
- `model/fit.json`: the lower bounds against each board;
- `report.json` and `resolved-manifest.yaml`.

**Exit codes.** `0`; `1` a rule (the data disagrees with the manifest, or the fit check fails);
`2` usage; `3` defect; `4` the `train` extra is missing.

## caravan train

**When you want it.** Rarely on its own — `export` runs it. Reach for it directly when you are
iterating on the model or the trainer settings and do not yet care about the export, because it
stops as soon as there is something to look at in `metrics.json`.

Runs `build` if needed, then trains the model on the training part. It stops early when the
validation loss stops improving (`trainer.early_stop`).

**Arguments.** `<manifest>`: the manifest file.

**Options.** `--cache-dir <path>`, `--fresh`, `--framework-output`, `--runs-dir <path>`, `--json`,
`-q` / `--quiet`: see above.

**Reads.** The manifest and the dataset.

**Writes.** The trained model, and `metrics.json` with its metrics on the test part:
- for a category or binary output: accuracy and the confusion matrix;
- for a number output: the mean absolute error (MAE), the mean squared error (MSE), its square
  root (RMSE) and the coefficient of determination (R²).

Plus everything `build` writes.

**Exit codes.** `0`; `1` a rule (for example [DS-10](rules.md#ds-10), training diverged); `2`; `3`;
`4` the `train` extra is missing.

## caravan quantize

**When you want it.** When you are working on the budget rather than on the model. Because a
change only this stage reads never retrains, you can try a different `accuracy_drop_max` and get an
answer in seconds from the cached training.

Runs `train` if needed, then converts the trained model to the manifest's quantization (`int8`).

- **Checking the result:** it reads the result's tensors from the file to prove that it is integer
  inside. The converter's word is never taken for it.
- **Measuring on the test part:**
  - the trained model;
  - the model converted without quantization;
  - the int8 model.
- **The accuracy gate:** fails the run when quantization cost more than the output's budget
  (`accuracy_drop_max` or `mae_increase_max`; rule [Q-4](rules.md#q-4)).
- **On a failed gate:** a per-layer error table shows where the accuracy was lost, and no
  exportable model is left behind.

**Arguments.** `<manifest>`: the manifest file.

**Options.** `--cache-dir <path>`, `--fresh`, `--framework-output`, `--runs-dir <path>`, `--json`,
`-q` / `--quiet`: see above.

**Reads.** The manifest and the dataset. Calibration uses training samples only.

**Writes.**
- `model/quantized.tflite`;
- `quantization.json`: the three measurements, the gate's verdict with its budget, the split and
  the dataset version, and the model's tensor types as read from the file;
- on a failed gate, the per-layer error table.

Plus everything `train` writes.

**Exit codes.** `0`; `1` a rule (the gate, or a model that is not fully integer); `2`; `3`; `4`
the `train` or `verify` extra is missing.

## caravan export

**When you want it.** Almost always. It runs every stage in order, reusing whatever is cached, so
it is both the first command of a new project and the one you repeat afterwards. The other stage
commands exist for when you want to stop part-way.

Runs `quantize` if needed, then writes the files a firmware author compiles. The exported model is
byte for byte the one the accuracy gate measured.

**Arguments.** `<manifest>`: the manifest file.

**Options.** `--cache-dir <path>`, `--fresh`, `--framework-output`, `--runs-dir <path>`, `--json`,
`-q` / `--quiet`: see above.

**Reads.** The manifest. It reads the dataset only for `export.test_windows`.

**Writes**, in the run directory's `model/`:
- `model.tflite`: the int8 model;
- `model_data.h` and `model_data.cc`: the model as a C array, with a named position for every
  input and the output, and the label names;
- `resolver.h`: exactly the operators this model needs, for TensorFlow Lite Micro;
- `interface.json`: every input by name, with its position, element type, shape, what was fitted
  for it and what to pass for a missing reading; and what the output means;
- `test_windows.h`, when `export.test_windows` is above 0: windows of the test part with the int8
  model's answers on your computer, for a [board run](../route/3-onto-a-board.md).

Also written:
- `runner/<board>/main.cc`, one per target board: a starting point for the firmware;
- `export.json`: the operators, which of them each board accelerates, and the working-memory
  floor, which is a lower bound computed from the model file, not the arena a board needs.

**Exit codes.** `0`; `1` a rule (for example [X-4](rules.md#x-4), an operator the runtime cannot
resolve); `2`; `3`; `4` the `verify` extra is missing.

## caravan templates

**When you want it.** To see which templates the version you have actually registers, rather than
which ones the documentation describes. The two can differ across versions.

Lists the registered templates, one per line, with a one-line summary. Takes no arguments and
writes nothing.

## caravan boards

**When you want it.** Before writing `export.targets`, to get the identifiers right, and to see
what each board offers in flash and RAM — which is what the fit check will compare your model
against.

Lists the known boards, one per line: core, clock, RAM, flash, the accelerated kernel library and
the emulator support. Takes no arguments and writes nothing. [Compatibility](../compatibility.md)
says how far each board has been verified.
