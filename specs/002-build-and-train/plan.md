# Implementation Plan: Build and Train

**Branch**: `002-build-and-train` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-build-and-train/spec.md`

## Summary

Two stages and the machinery they need: `caravan build` constructs the model from the template's
builder half and reports its shape and parameter count; `caravan train` trains it on the dataset
the manifest names and writes checkpoints, the trained model and the quality metrics. Around them,
three things that are not stages: the `train` extra that carries the framework, the stage cache
Principle III requires, and the dataset reader that resolves a manifest's dataset reference for the
first time.

The technical approach is decided by one fact and one rule. The fact: no stable TensorFlow wheel
exists for the Python versions this project supported, so the extra carries Python 3.13 and the
published floor moves down with it (research R1, constitution v2.3.0). The rule: the core must
still load no framework, so the builder half, the reader and the metrics all live behind the extra,
and the cache — which must work without a framework — identifies a dataset by hashing its bytes
rather than by reading it (R4).

The cache is where this feature earns or loses Principle III. It is built so that "the fields this
stage reads" is true by construction rather than by review: a stage declares its field set and is
handed a projection of exactly those fields, so it cannot read anything else (R7).

## Technical Context

**Language/Version**: Python. The floor moves from 3.14 to **3.13** for the reason in R1, and
3.13, 3.14 and 3.15 are all tested — the lowered floor is only legitimate if the support claim is
true (Principle XII, condition 1, as amended in v2.3.0). The core must therefore keep running on
3.13, which is a real constraint on what the core may use.

**Primary Dependencies**: unchanged in the default installation — `pydantic` and `ruamel.yaml`, 2
of the 6 the constitution allows. The first extra appears: `train = ["tensorflow>=2.21,<2.22",
"keras>=3.12", "numpy>=1.26"]`, each with a `python_version < "3.14"` marker, so installing the
extra on 3.14 or 3.15 pulls no framework and the stage says why (R2). That is 1 of the 4 extras the
constitution allows. The upper bound on TensorFlow is the one case the constitution permits: 2.22's
release candidate depends on `keras-nightly`, documented in R1, and the bound comes off when 2.22
ships.

**Storage**: files only. Run artifacts go in the per-invocation run directory of feature 001; the
stage cache is a separate directory (`./.caravan/cache` by default) so that a run directory stays
complete on its own (R8). Datasets are read, never written, and never enter the repository.

**Testing**: `pytest`. Three layers as before, plus two that are new in kind: `tests/train/`, which
is collected only where the framework is importable, and one test that asserts the *absence* path —
exit code 4 with an actionable message — which is collected only where it is not. The generic cache
test in R7 walks every leaf of the pilot manifest rather than listing cases.

**Every test that needs the framework lives under `tests/train/`**, without exception. The `test`
job names `unit`, `contract`, `integration` and `layering` explicitly and runs them on all three
Pythons, and `clean-environment` runs the whole tree with no framework installed — so a
framework-dependent test placed in any other directory turns two jobs red. The analysis pass caught
two such tests in the task list before they were written.

**Target Platform**: any machine with a supported Python, for the core. Training additionally needs
Python 3.13 and about 700 MB of installed framework. No hardware, no emulator, no network in any
stage of this feature.

**Project Type**: single Python package exposing a command line application; one optional extra.

**Performance Goals**: build and train end to end on the fixture in under 60 seconds including the
framework's import (SC-001). A cached second run performs no training at all (SC-004). The default
installation's time and size budgets are unchanged and still gated.

**Constraints**: the core loads no training framework — the layering tests of feature 001 must pass
unchanged, and a new one covers the builder half and the reader. No network. The author's manifest
is never modified. A dataset the author marked `benchmark-only` is never trained on. Every metric
carries the split and dataset version it was measured against.

**Scale/Scope**: one template's builder half (`mlp`), two commands, one extra, one cache, one
dataset format. Roughly 1,200 lines of implementation and a comparable amount of test code, plus a
160 KB committed fixture dataset.

## Constitution Check

*GATE: checked before Phase 0 research, and again after Phase 1 design.*

### Before research

| Principle | Gate | Verdict |
|---|---|---|
| I. Declarative Manifest | Every training setting from the manifest; no per-model script | PASS — `train` reads only manifest fields, and the stage cannot read what it did not declare (R7) |
| III. Reproducible by Construction | Provenance recorded; stage cache; seed | PASS — FR-008 and FR-016; the reproducibility claim is bounded in R9 rather than overstated |
| IV. Measured, Emulated or Estimated | No unlabeled number | PASS — this feature produces no hardware number; quality metrics carry their split and dataset version |
| V. Budgets Are Gates | No switch silences a gate | PASS — `--fresh` bypasses the cache, not a rule, and is recorded (FR-017) |
| VI. Compliance Enforced by the Schema | The author's own statements are kept | PASS — FR-009 refuses to train on `benchmark-only`, and claims nothing about a licence it did not verify |
| VII. Targets and Templates Are Data | Registry, not an enumeration | PASS — the builder half is discovered by name and by entry point, no central list (R3) |
| VIII. No Lock-In | Portable artifacts, no hosted service | PASS — everything runs offline; artifacts are the framework's own open formats |
| IX. Stable Manifest Contract | No schema churn | PASS — the schema gains no field; the dataset's format is a convention the data meets |
| X. Built for Real Models | A named model drives it | PASS — `picket-mlp`; `conv1d` and its builder wait for `pace-cnn` |
| XI. No Claude in Model Learning | No model data produced by Claude | PASS — the fixture is generated by a seeded standard-library script, committed with the script (R13) |
| XII. Small Core, Few Dependencies | Budget, layering, Python policy | **FAIL at first pass — see below** |

**The gate that failed, and how.** Principle XII as of v2.2.0 permitted "an extra to declare a
narrower Python window than the project". No such mechanism exists: `requires-python` is metadata of
the whole distribution, and an extra can carry only environment markers on its dependencies. With a
floor of `>=3.14` and a framework that ships only for 3.13, `pip install caravan-ml[train]` fails on
every interpreter — the permitted extra was not installable. Planning stopped here.

Resolved by amendment rather than by working around the principle: **constitution v2.3.0** states how
such a window is actually expressed and permits the published floor to be lowered to the extra's
floor under five conditions, the load-bearing one being that the lowered version must be *tested*,
or the support stated in the metadata is false. This plan meets all five: the floor moves to 3.13
(condition 2: recorded with framework, version and date, in R1 and the Technical Baseline); 3.13,
3.14 and 3.15 are all tested (condition 1, R12); the extra's dependencies carry markers (condition
3); running `build` or `train` outside the window gives a message naming the window and the reason
(condition 4, R2); and the return to 3.14 is recorded in R1, `docs/budgets.md` and the roadmap
(condition 5). **PASS after amendment**, and the amendment is reported as a change of governance,
not as a deviation.

### After design

Re-checked once the design existed. Four things it surfaced:

1. **The cache is a Principle III obligation that can silently lie.** A stage that reads a field it
   did not declare produces a result reused when it should not be, and no test written as a list of
   cases will catch the next such field. The projection in R7 makes the declaration the only access
   path, and the generic test walks every leaf of the pilot manifest. **PASS, and it is the single
   most important test in the feature.**
2. **Principle XII pulled against having a reader in the core.** The cache must detect a changed
   dataset without a framework installed, which looks like an argument for a core reader. Resolved by
   separating the two questions: the core hashes bytes (no parsing), the extra parses (R4). One
   implementation of the windowing rule, not two. **PASS.**
3. **The core's template discovery walk imports every module in `caravan.templates`.** Putting the
   builder half in `caravan/templates/builders/` therefore risked importing the framework from the
   core — the exact thing the layering test forbids. Resolved by skipping subpackages in the walk,
   with the layering test extended to cover it (R3). **PASS, and the test is what makes it safe
   rather than the comment.**
4. **Principle IV's habit applies to a training promise.** Enabling op determinism would buy a
   stronger reproducibility claim at the cost of refusing to run some models, and the claim would
   still be per-machine. Not enabled; the promise stays the one that holds (R9). **PASS.**
5. **One rule turned out to be unreachable, and was withdrawn before it was written.** DS-7 would
   have compared the data's feature width against "what the manifest's window implies" — and the
   manifest implies nothing about feature width, because the width comes from the data (FR-004).
   The same thing happened to CF-5 in feature 001, which is a sign the analysis pass earns its
   place: FR-011 now states what is checkable, DS-7 is marked entailed so the coverage test does
   not demand a fixture for it, and the case it reached for is covered by DS-3 and DS-6. **PASS.**

No deviation. Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-build-and-train/
├── spec.md                 # Feature specification
├── plan.md                 # This file
├── research.md             # Phase 0: R1–R13, decisions with evidence
├── data-model.md           # Phase 1: entities, validation rules, state
├── quickstart.md           # Phase 1: runnable validation scenarios
├── contracts/
│   ├── cli.md              # build and train: options, exit codes, output, exit code 4
│   ├── dataset.md          # the on-disk dataset contract, windowing, splitting
│   ├── stage-cache.md      # key, store, reuse, bypass
│   └── artifacts.md        # what each stage writes, and the report's new sections
├── checklists/
│   └── requirements.md     # Specification quality checklist
└── tasks.md                # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
pyproject.toml                       # floor 3.13; the train extra with its markers; pytest markers
src/caravan/
├── env.py                           # NEW: is the framework present; the two messages (R2)
├── cli/
│   ├── main.py                      #   gains the build and train verbs, and exit code 4
│   ├── build.py                     # NEW
│   └── train.py                     # NEW
├── stages/                          # NEW — the stage runner and the cache, all core
│   ├── base.py                      #   Stage protocol: name, READS, artifacts; the projection
│   ├── cache.py                     #   key computation, store, reuse, bypass record
│   ├── build.py                     #   the build stage; loads the builder half by name
│   └── train.py                     #   the train stage; loads the reader and the metrics
├── data/                            # NEW
│   ├── fingerprint.py               #   dataset version: hashlib over bytes (core)
│   ├── windows.py                   #   the windowing and splitting rule (core, no numpy)
│   └── reader.py                    #   records to arrays (extra only, imports numpy)
├── metrics/                         # NEW
│   └── classification.py            #   confusion matrix and what follows from it (extra only)
├── templates/
│   ├── registry.py                  #   one change: the discovery walk skips subpackages
│   └── builders/                    # NEW — the builder half
│       ├── __init__.py              #   lazy lookup by identifier and entry point; imports nothing
│       └── mlp.py                   #   imports keras; builds the model
└── run/
    └── report.py                    #   gains the stage, cache, dataset and metric sections

tests/
├── unit/                            # windowing, splitting, fingerprint, cache key, env messages
├── contract/                        # the two verbs, exit codes, artifact names, report shape
├── integration/                     # end to end *without* the framework: run dirs, input untouched
├── layering/                        # extended: builders, reader and metrics stay unimported
├── train/                           # NEW — every test that needs the framework, and only those
│   └── conftest.py                  #   importorskip, and the fixture dataset's path
└── fixtures/
    ├── datasets/synthetic/          # NEW — records.csv and the make.py that generated it
    └── manifests/valid/
        └── picket-mlp-fixture.yaml  # NEW — the pilot manifest, dataset.source at the fixture
```

**Structure Decision**: `data/` and `metrics/` are packages of their own rather than modules inside
`stages/`, because the layering rule is per module and a reader that imports `numpy` must be as
visibly separate from the core as the builder half is. `stages/` holds the runner and the cache but
no framework import anywhere — a stage *loads* its framework-bearing parts by name, which is what
keeps `import caravan.stages.train` safe in a default installation.

`windows.py` sits in the core although only the extra's reader calls it: the windowing and splitting
rule is arithmetic over indices with no array in sight, and keeping it in the core means its tests
run on every Python in the matrix rather than only on 3.13.

## Complexity Tracking

No deviation to justify. One governance amendment was required (v2.3.0) and is recorded as such: the
previous text permitted something packaging cannot express, and the plan would have had to either
ship an uninstallable extra or quietly ignore the principle. Amending it in the open was the only
honest third option.
