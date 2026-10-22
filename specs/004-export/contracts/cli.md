# Contract: `caravan export`

**Feature**: 004 · **Date**: 2026-10-22

The fourth stage verb, and the first that writes something meant to leave the machine. It follows
the shape the stage verbs already have (`build`, `train`, `quantize`): one manifest, a run
directory, a cache, no option that can skip a rule.

## `caravan export <manifest>`

| Option | Default | Effect |
|---|---|---|
| `--runs-dir <path>` | `runs` | where the run directory is created |
| `--cache-dir <path>` | `.caravan/cache` | where stage results are stored |
| `--fresh` | off | ignore any cached result and produce it again; recorded in the report |
| `--json` | off | findings on standard output as one JSON document |
| `-q`, `--quiet` | off | suppress the human summary; exit code only |

There is no `--format`, no `--target` and no `--skip-coverage`. What is exported and for which
boards is what the manifest says, because a command-line flag that changed it would make the run
report describe something other than the manifest (FR-005 of feature 001, Principle V).

## The human summary

One screen, the same voice as `quantize`:

```
picket-mlp-fixture.yaml: exported 3 operators in 4 nodes — 7,856 bytes
    artifacts: model.tflite, model_data.cc + .h, resolver.h, runner/{s32k144,stm32h743,esp32}/main.cc
    operators: RESHAPE v1, FULLY_CONNECTED v4, SOFTMAX v2
    accelerated: s32k144 2 of 3, stm32h743 2 of 3, esp32 2 of 3 — RESHAPE falls back on all three
    working memory: floor 648 bytes (peak simultaneously live, from the model file)
                    the figure a board needs is larger and is measured, not computed here
    run: runs/20261022T201530Z-b271d5b3
```

The last two lines are not padding. They are the difference between a number a reader can use and a
number a reader can be misled by.

## Exit codes

| Code | When |
|---|---|
| 0 | the artifacts were written, or an unchanged result was reused |
| 1 | a rule said no: `X-1` … `X-5`, or any upstream rule reached through the quantize stage |
| 2 | usage: an unknown option, a missing argument, an unreadable manifest path |
| 3 | a defect in caravan itself, reported as one, with a trace |
| 4 | the environment is incomplete: the part that reads a model file is not installed |

Code 4 here means the `verify` extra, not the training one. Exporting reads a model and writes
text; it never converts, so it does not need the conversion half. That is the layering rule paying
for itself: the command runs on every Python the runtime installs on, not only the one the training
framework allows.

## When a part is missing

```
$ caravan export manifest.yaml
manifest.yaml: export needs the runtime that reads a model file, which installs separately
    pip install "caravan-ml[verify]"
    this part reads and runs exported models; it needs no training framework
```

Exit 4, no run directory, no partial artifact. The message names the one extra the command needs
and not both, as feature 003 established.

## What this command never does

- It does not convert. The model it exports is the model the accuracy gate measured, byte for byte.
- It does not compile, link or run anything it emits.
- It does not reach the network: no stage before publication may (Principle VIII).
- It does not state a latency, a flash figure or a memory figure for a target.
- It does not write an artifact for a format it cannot produce, nor for a run whose gate failed.
