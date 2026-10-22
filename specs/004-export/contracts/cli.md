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
| 4 | the environment is incomplete: a part that installs separately is not there |

## Which parts, and an honesty note about the command versus the stage

The **export stage** needs only the runtime that reads a model file: no conversion, no training
framework. That is what lets its whole proving half run in the `measure` matrix, and it is asserted
by tests rather than asserted here (FR-031, SC-009).

The **command** needs both halves, exactly as `caravan quantize` does, because it runs the pipeline
that produces the model it exports — build, train, quantize, export — and three of those four
convert or train. So:

```
$ caravan export manifest.yaml
manifest.yaml: export needs TensorFlow, which installs separately
    pip install "caravan-ml[train,verify]"
```

Exit 4, no run directory, no partial artifact.

**What this costs, stated plainly**: an author on Python 3.14 holding a quantized model from a 3.13
machine cannot export it with this command, even though the stage that would do the work needs
nothing the 3.14 install lacks. The reason is the environment check, which asks for every part the
plan *could* need rather than every part the plan *will* need — a cached upstream result makes the
difference, and the check happens before the cache is consulted.

Fixing it is a change to the pipeline runner, not to this stage, and it collides with two
invariants feature 002 wrote down deliberately: the run directory is created before the dataset is
resolved, so a disagreeing dataset lands in a report; and a missing extra creates no run directory
at all. Computing cache keys early enough to know which stages will actually run requires the
dataset, so one of the two has to move. That is its own piece of work with its own reasoning, and
it is recorded as an obligation rather than improvised here.

## What this command never does

- It does not convert. The model it exports is the model the accuracy gate measured, byte for byte.
- It does not compile, link or run anything it emits.
- It does not reach the network: no stage before publication may (Principle VIII).
- It does not state a latency, a flash figure or a memory figure for a target.
- It does not write an artifact for a format it cannot produce, nor for a run whose gate failed.
