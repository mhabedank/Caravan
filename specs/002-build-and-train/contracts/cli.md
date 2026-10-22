# Contract: Command Line Surface — `build` and `train`

Date: 2026-10-22 · Feature: 002 · Extends [feature 001's CLI contract](../../001-manifest-schema/contracts/cli.md)

Everything in the 001 contract still holds: the streams, the message form, the JSON form, and the
rule that no option skips a rule, lowers a threshold or continues past a failure. This document adds
two verbs, one exit code and three options.

**The verb set, written down.** Principle XII fixes the command line's verbs and requires an
amendment to add one, and until now the set existed only in whichever contract happened to mention
it. It is this, and the pair of these two contract documents is the list the principle refers to:

| Verb | Feature | Sanctioned by |
|---|---|---|
| `validate`, `render`, `templates`, `boards` | 001 | the pipeline contract's stage list and the rejection messages that promise a listing |
| `build`, `train` | 002 | the pipeline contract's stage list |
| *planned*: `quantize`, `analyze`, `verify`, `bench`, `card`, `publish` | later | the same list — each arrives with its feature, none by convenience |

A verb not in that table does not exist, and adding one is an amendment, not a feature decision.

## `caravan build <manifest>`

Validates the manifest, resolves the dataset reference, constructs the model from the template's
builder half, and writes it with its shape report into a new run directory.

| Option | Meaning | Default |
|---|---|---|
| `--runs-dir <path>` | where the run directory is created | `./runs` |
| `--cache-dir <path>` | where stage results are stored | `./.caravan/cache` |
| `--fresh` | ignore any cached result for this stage and produce it again | off |
| `--json` | the run's outcome on standard output as one JSON document | off |
| `-q`, `--quiet` | suppress the human summary; exit code only | off |

Human output on success, on standard error:

```text
picket-mlp.yaml: built mlp — input (64, 5), output 4, 5,124 parameters (5,124 trainable)
    dense_1 (64, 5) → 32    2,592
    dropout_1         32         0
    dense_2           16       528
    output             4        68
    run: runs/2026-10-22T17-04-31Z-ab12cd
```

## `caravan train <manifest>`

Everything `build` does, then trains the model and writes the checkpoints, the trained model and the
quality metrics. `build`'s result is reused from the cache when it is unchanged, so `train` does not
rebuild for nothing.

| Option | Meaning | Default |
|---|---|---|
| `--runs-dir <path>` | where the run directory is created | `./runs` |
| `--cache-dir <path>` | where stage results are stored | `./.caravan/cache` |
| `--fresh` | ignore cached results for `build` and `train` and produce both again | off |
| `--json` | the run's outcome on standard output as one JSON document | off |
| `-q`, `--quiet` | suppress the human summary and the per-epoch progress | off |

Human output on success ends with the metrics and what they were measured against:

```text
picket-mlp.yaml: trained mlp — 23 of 50 epochs, stopped early at 23 (best: 18)
    test, 15 windows, dataset sha256:4f1c…  accuracy 0.933  f1_macro 0.921
    recall: normal 1.000  dos 0.750  fuzzy 1.000  replay 0.667
    run: runs/2026-10-22T17-05-02Z-cd34ef
```

A number on this line always carries its split, its sample count and its dataset version, because a
metric without them is not writable at all (see data-model).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | the stage produced or reused its result |
| 1 | a rule said no — an invalid manifest, or one of the DS rules |
| 2 | usage error: unknown option, missing argument, unreadable path |
| 3 | internal failure of the tool itself — a defect, reported as one, with a trace |
| **4** | **the environment is incomplete: a required part is not installed** |

Code 4 is new in this feature and exists because a missing framework is neither a broken rule nor a
defect in the tool (FR-020). A continuous integration job can act on each of the four differently,
which it could not if a missing install arrived as code 1.

## When the training extra is absent

Two different situations, two different messages (research R2). Neither is a traceback.

On a Python the extra supports (3.13), with the framework not installed:

```text
picket-mlp.yaml: build needs the train extra, which is not installed
    install it with: pip install "caravan-ml[train]"
```

On Python 3.14 or newer, where `pip install "caravan-ml[train]"` installs no framework because none
exists for this interpreter:

```text
picket-mlp.yaml: build needs TensorFlow, which publishes no wheel for Python 3.14
    checked 2026-10-22: tensorflow 2.21.0 ships cp310 through cp313
    train on Python 3.13; validate, render and the analysis stages run here
```

The second message names the window and the reason because the user may have just run the install
command and received nothing — a message that only repeated it would send them in a circle. The
check uses `importlib.util.find_spec`, so the core never imports the framework in order to discover
that it is there.

## What these commands never do

- They never modify the manifest, the dataset or any file outside the run directory and the cache
  directory.
- They never reach the network. The contract test of feature 001 covers the new verbs too.
- They never write a model artifact for a run that failed or was interrupted (FR-012); the report
  says the run did not finish.
- They have no option that trains on data the author marked `benchmark-only`, no option that lowers
  a split, and no option that silences a rule. `--fresh` bypasses the cache, and the report records
  that it did.
